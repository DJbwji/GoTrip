import sqlite3
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from .pythonanywhere import PythonAnywhereAPI, DeploymentError, backup_database, production_environment

class InstallerTests(TestCase):
    def test_token_cannot_be_sent_to_an_unapproved_host(self):
        with self.assertRaises(DeploymentError):
            PythonAnywhereAPI('example', 'private-token', 'attacker.example')

    def test_failure_message_does_not_include_api_token(self):
        api = PythonAnywhereAPI('example', 'private-token')
        error = HTTPError(api.base + '/webapps/', 403, 'Denied', {}, BytesIO(b'{}'))
        with patch('deploy.pythonanywhere.urlopen', side_effect=error):
            with self.assertRaises(DeploymentError) as caught:
                api.request('/webapps/')
        self.assertNotIn('private-token', str(caught.exception))

    def test_installer_will_not_overwrite_another_website(self):
        api = PythonAnywhereAPI('example', 'token')
        api.request = Mock(side_effect=[
            [{'domain_name':'example.pythonanywhere.com'}],
            {'source_directory':'/home/example/another-project'},
        ])
        with self.assertRaises(DeploymentError):
            api.configure('example.pythonanywhere.com', Path('/home/example/gotrip'), Path('/home/example/env'), 'wsgi', 'python312', Path('/home/example/data'))
        self.assertEqual(api.request.call_count, 2)
        self.assertTrue(all(len(call.args) == 1 for call in api.request.call_args_list))

    def test_database_backup_preserves_original_data(self):
        with TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            connection = sqlite3.connect(root / 'db.sqlite3')
            connection.execute('CREATE TABLE test (value TEXT)')
            connection.execute("INSERT INTO test VALUES ('original')")
            connection.commit()
            connection.close()
            backup_database(root)
            copies = list((root / 'backups').glob('*.sqlite3'))
            self.assertEqual(len(copies), 1)
            connection = sqlite3.connect(copies[0])
            self.assertEqual(connection.execute('SELECT value FROM test').fetchone()[0], 'original')
            connection.close()

    def test_production_secret_is_new_for_each_installation(self):
        first = production_environment('example.pythonanywhere.com', Path('/home/example/data'))
        second = production_environment('example.pythonanywhere.com', Path('/home/example/data'))
        self.assertEqual(first['DJANGO_DEBUG'], '0')
        self.assertGreaterEqual(len(first['DJANGO_SECRET_KEY']), 50)
        self.assertNotEqual(first['DJANGO_SECRET_KEY'], second['DJANGO_SECRET_KEY'])

    def test_provider_validation_is_reported_without_secrets(self):
        api = PythonAnywhereAPI('example', 'private-token')
        body = b'{"python_version":["Invalid choice"],"detail":"private-token","password":"do-not-display"}'
        error = HTTPError(api.base + '/webapps/example/', 400, 'Bad request', {}, BytesIO(body))
        with patch('deploy.pythonanywhere.urlopen', side_effect=error):
            with self.assertRaises(DeploymentError) as caught:
                api.request('/webapps/example/', 'PATCH', {'python_version':'invalid'})
        message = str(caught.exception)
        self.assertIn('PATCH', message)
        self.assertIn('Invalid choice', message)
        self.assertNotIn('private-token', message)
        self.assertNotIn('do-not-display', message)

    def test_api_error_status_is_not_treated_as_success(self):
        api = PythonAnywhereAPI('example', 'token')
        with patch('deploy.pythonanywhere.urlopen', return_value=BytesIO(b'{"status":"ERROR","error":"Domain unavailable"}')):
            with self.assertRaises(DeploymentError):
                api.request('/webapps/', 'POST', {'domain_name':'example.pythonanywhere.com'})

    def test_resume_keeps_domain_spelling_and_does_not_patch_python_version(self):
        domain = 'DJbwji.pythonanywhere.com'
        project = Path('/home/DJbwji/gotrip')
        api = PythonAnywhereAPI('DJbwji', 'token')
        recorded = []
        def provider(path, method='GET', values=None):
            recorded.append((path, method, values))
            if path == '/webapps/':
                if method != 'GET':
                    self.fail('Must resume the existing app, not create a duplicate')
                return [{'domain_name':domain}]
            if path == f'/webapps/{domain}/' and method == 'GET':
                return {'source_directory':'/home/DJbwji', 'virtualenv_path':''}
            if path == f'/webapps/{domain}/' and method == 'PATCH':
                if 'python_version' in values:
                    raise DeploymentError('Invalid version format on PATCH')
                return {}
            if path.endswith('/static_files/') and method == 'GET':
                return []
            return {}
        api.request = provider
        with patch.object(Path, 'exists', return_value=False), patch.object(Path, 'write_text'):
            api.configure(domain.lower(), project, Path('/home/DJbwji/.virtualenvs/gotrip'),
                          'wsgi', 'python312', Path('/home/DJbwji/.gotrip-data'))
        self.assertTrue(any(method == 'PATCH' and path == f'/webapps/{domain}/' for path, method, _ in recorded))
        self.assertEqual(recorded[-1][0], f'/webapps/{domain}/reload/')
