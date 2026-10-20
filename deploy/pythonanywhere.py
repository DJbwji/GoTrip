"""Install or update GoTrip from a PythonAnywhere Bash console.

Run on PythonAnywhere only; secrets stay in that account.
"""
import argparse
from contextlib import closing
import getpass
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPOSITORY = 'https://github.com/DJbwji/GoTrip.git'
HOSTS = ('www.pythonanywhere.com', 'eu.pythonanywhere.com')
MARKER = '# Managed by GoTrip PythonAnywhere installer'


class DeploymentError(RuntimeError):
    pass


def api_error_detail(body, token):
    try:
        decoded = json.loads(body)
    except (ValueError, TypeError):
        return ''
    if not isinstance(decoded, dict):
        return ''
    allowed = ('python_version', 'domain_name', 'source_directory', 'virtualenv_path',
               'force_https', 'non_field_errors', 'error', 'detail')
    parts = []
    for key in allowed:
        if key in decoded:
            message = str(decoded[key]).replace(token, '[redacted]') if token else str(decoded[key])
            parts.append(f'{key}: {message[:300]}')
    return '; '.join(parts)[:1500]


def is_unconfigured(configuration, project):
    source = configuration.get('source_directory')
    return not configuration.get('virtualenv_path') and (
        not source or Path(source).resolve() == project.parent.resolve()
    )


class PythonAnywhereAPI:
    def __init__(self, username, token, host='www.pythonanywhere.com'):
        if host not in HOSTS or not re.fullmatch(r'[a-zA-Z0-9_-]+', username):
            raise DeploymentError('Invalid PythonAnywhere account or API host.')
        self.base = f'https://{host}/api/v0/user/{username}'
        self.token = token

    def request(self, path, method='GET', values=None):
        payload = urlencode(values).encode() if values is not None else None
        headers = {'Authorization': 'Token ' + self.token, 'User-Agent': 'GoTrip-deployer'}
        if payload is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = Request(self.base + path, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=90) as response:
                body = response.read()
            result = json.loads(body) if body.strip() else None
            if isinstance(result, dict) and result.get('status') == 'ERROR':
                detail = api_error_detail(body, self.token)
                raise DeploymentError(f'PythonAnywhere rejected {method} {path}. {detail}')
            return result
        except HTTPError as error:
            # Only selected validation fields may be shown; credentials are redacted.
            detail = api_error_detail(error.read(8192), self.token)
            raise DeploymentError(f'PythonAnywhere API returned HTTP {error.code} for {method} {path}. {detail}') from None
        except URLError:
            raise DeploymentError('PythonAnywhere API is temporarily unavailable. Retry this command later.') from None

    def configure(self, domain, project, environment, wsgi_source, python_version, data_dir):
        apps = self.request('/webapps/')
        existing = next((app for app in apps if app['domain_name'].casefold() == domain.casefold()), None)
        if existing:
            domain = existing['domain_name']
        app_path = f'/webapps/{domain}/'
        if existing:
            configuration = self.request(app_path)
            source = configuration.get('source_directory')
            if source and Path(source).resolve() != project.resolve() and not is_unconfigured(configuration, project):
                raise DeploymentError('This domain already hosts another project. Existing configuration was preserved.')
        else:
            if apps:
                raise DeploymentError('This account already has a website. The installer will not replace it.')
            self.request('/webapps/', 'POST', {'domain_name': domain, 'python_version': python_version})
            configuration = self.request(app_path)
        wsgi_path = Path(configuration.get('wsgi_configuration_file') or
                         '/var/www/' + domain.replace('.', '_') + '_wsgi.py')
        expected_wsgi = Path('/var/www') / (domain.replace('.', '_') + '_wsgi.py')
        if wsgi_path.resolve() != expected_wsgi.resolve():
            raise DeploymentError('Unexpected WSGI configuration location; no WSGI file was overwritten.')
        current = wsgi_path.read_text() if wsgi_path.exists() else ''
        if current and MARKER not in current and existing and not is_unconfigured(configuration, project):
            raise DeploymentError('Existing WSGI is not managed by GoTrip. It was preserved.')
        self.request(app_path, 'PATCH', {
            'source_directory': str(project),
            'virtualenv_path': str(environment), 'force_https': 'true',
        })
        if current and MARKER not in current:
            backup = wsgi_path.with_name(wsgi_path.name + '.before-gotrip')
            if not backup.exists():
                backup.write_text(current)
        wsgi_path.write_text(wsgi_source, encoding='utf-8')
        mappings = self.request(app_path + 'static_files/')
        for url, directory in [('/static/', project / 'staticfiles'), ('/media/', data_dir / 'media')]:
            mapping = next((item for item in mappings if item['url'] == url), None)
            if mapping:
                self.request(app_path + f"static_files/{mapping['id']}/", 'PATCH', {'path': str(directory)})
            else:
                self.request(app_path + 'static_files/', 'POST', {'url': url, 'path': str(directory)})
        self.request(app_path + 'reload/', 'POST', {})


def production_environment(domain, data_dir):
    return {
        'DJANGO_DEBUG': '0',
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
        'DJANGO_ALLOWED_HOSTS': domain.lower(),
        'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://' + domain.lower(),
        'DJANGO_TRUST_PROXY': '1',
        'GOTRIP_DATA_DIR': str(data_dir),
        'DEMO_PAYMENTS': '1',
        'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend',
    }


def read_environment(path):
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def wsgi_configuration(project):
    return (
        MARKER + '\nimport os\nimport sys\n'
        + f'project = {str(project)!r}\n'
        + 'if project not in sys.path:\n    sys.path.insert(0, project)\n'
        + "os.environ['DJANGO_SETTINGS_MODULE'] = 'gotrip.settings'\n"
        + 'from django.core.wsgi import get_wsgi_application\n'
        + 'application = get_wsgi_application()\n'
    )


def backup_database(data_dir):
    database = data_dir / 'db.sqlite3'
    if not database.exists():
        return
    backup_dir = data_dir / 'backups'
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    target = backup_dir / f'gotrip-{timestamp}.sqlite3'
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
    target.chmod(0o600)
    print('Database backup saved inside the private data directory.')


def run(arguments, cwd=None, env=None):
    subprocess.run([str(value) for value in arguments], cwd=cwd, env=env, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=HOSTS, default='www.pythonanywhere.com')
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--no-admin', action='store_true', help='Skip interactive administrator creation.')
    options = parser.parse_args(argv)
    username = getpass.getuser()
    home = Path.home().resolve()
    if os.name != 'posix' or home != Path('/home') / username or not Path('/var/www').is_dir():
        raise DeploymentError('Run this installer inside your PythonAnywhere Bash console, not on your computer.')
    if sys.version_info < (3, 10):
        raise DeploymentError('Use Python 3.10 or newer, for example python3.12.')
    token = os.environ.get('API_TOKEN', '').strip()
    token_path = home / '.pythonanywhere_api_token'
    if not token and token_path.is_file():
        token = token_path.read_text().strip()
    if not token:
        raise DeploymentError(
            f'Open https://{options.host}/account/ and generate an API token on the API Token tab. '
            'Then start a NEW Bash console and run the installer again. Do not send the token to anyone.'
        )
    project = home / 'gotrip'
    data_dir = home / '.gotrip-data'
    environment = home / '.virtualenvs' / 'gotrip'
    domain_suffix = 'eu.pythonanywhere.com' if options.host.startswith('eu.') else 'pythonanywhere.com'
    domain = username + '.' + domain_suffix
    api = PythonAnywhereAPI(username, token, options.host)
    apps = api.request('/webapps/')
    own_app = next((app for app in apps if app['domain_name'].casefold() == domain.casefold()), None)
    if apps and not own_app:
        raise DeploymentError('Another website already uses this account. Nothing was replaced.')
    if own_app:
        domain = own_app['domain_name']
        configuration = api.request(f'/webapps/{domain}/')
        source = configuration.get('source_directory')
        if source and Path(source).resolve() != project and not is_unconfigured(configuration, project):
            raise DeploymentError('The existing website belongs to another project. Nothing was replaced.')
    if project.exists():
        if not (project / '.git').is_dir() or project.is_symlink():
            raise DeploymentError('The gotrip folder already contains unrelated files. Nothing was replaced.')
        origin = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=project, text=True).strip()
        if origin.lower() != REPOSITORY.lower():
            raise DeploymentError('Unexpected Git repository in the gotrip folder.')
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=project, text=True)
        if dirty.strip():
            raise DeploymentError('There are local code changes on the server. Commit them before updating.')
        backup_database(data_dir)
        run(['git', 'pull', '--ff-only', 'origin', 'main'], cwd=project)
    else:
        if options.update:
            raise DeploymentError('There is no installed GoTrip to update.')
        run(['git', 'clone', '--branch', 'main', REPOSITORY, project])
    data_dir.mkdir(mode=0o700, exist_ok=True)
    (data_dir / 'media').mkdir(exist_ok=True)
    env_path = project / '.env'
    if not env_path.exists():
        values = production_environment(domain, data_dir)
        with env_path.open('x', encoding='utf-8') as handle:
            handle.write('\n'.join(f'{key}={value}' for key, value in values.items()) + '\n')
        env_path.chmod(0o600)
    values = read_environment(env_path)
    if (values.get('DJANGO_DEBUG') != '0' or values.get('DJANGO_ALLOWED_HOSTS', '').lower() != domain.lower()
            or values.get('GOTRIP_DATA_DIR') != str(data_dir)
            or len(values.get('DJANGO_SECRET_KEY', '')) < 50):
        raise DeploymentError('Existing .env does not match safe hosting settings. It was not overwritten.')
    command_env = dict(os.environ, **values)
    command_env['PYTHONDONTWRITEBYTECODE'] = '1'
    if not environment.exists():
        environment.parent.mkdir(exist_ok=True)
        run([sys.executable, '-m', 'venv', environment])
    python = environment / 'bin/python'
    run([python, '-m', 'pip', 'install', '--no-cache-dir', '-r', project / 'requirements.txt'])
    manage = [python, project / 'manage.py']
    run([*manage, 'migrate', '--noinput'], cwd=project, env=command_env)
    marker = data_dir / '.catalog-initialized'
    if not marker.exists():
        run([*manage, 'seed_demo', '--public-catalog'], cwd=project, env=command_env)
        marker.touch()
    run([*manage, 'collectstatic', '--noinput'], cwd=project, env=command_env)
    has_admin = subprocess.check_output([
        *map(str, manage), 'shell', '--verbosity', '0', '-c',
        "from users.models import User; print('yes' if User.objects.filter(is_staff=True, is_active=True).exists() else 'no')"
    ], cwd=project, env=command_env, text=True).strip().splitlines()[-1]
    if has_admin != 'yes' and not options.no_admin:
        print('\nCreate your own GoTrip administrator. Choose a separate password for the WEBSITE.')
        print('The public demonstration password must not be used for this account.\n')
        run([*manage, 'createsuperuser'], cwd=project, env=command_env)
    python_version = f'python{sys.version_info.major}{sys.version_info.minor}'
    api.configure(domain, project, environment, wsgi_configuration(project), python_version, data_dir)
    print('\nPythonAnywhere accepted the deployment and reload request.')
    print(f'Website address: https://{domain}/')
    print('Open the address to verify the live site. Free web apps require monthly extension in the Web tab.')
    print('Email is in console mode. Test payments do not charge money.')
    print('Update later: ' + str(python) + ' ' + str(project / 'deploy/pythonanywhere.py') + ' --update --host ' + options.host)


if __name__ == '__main__':
    try:
        main()
    except (DeploymentError, subprocess.CalledProcessError) as error:
        print('Installation stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
