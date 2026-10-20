from django.apps import AppConfig
from django.db.backends.signals import connection_created

def sqlite_unicode_lower(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        connection.connection.create_function('LOWER', 1, lambda value: value.lower() if isinstance(value, str) else value, deterministic=True)

class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'GoTrip: общие данные'
    def ready(self):
        # SQLite's built-in LOWER handles ASCII only. Match Cyrillic search too.
        connection_created.connect(sqlite_unicode_lower, dispatch_uid='gotrip_sqlite_lower')
