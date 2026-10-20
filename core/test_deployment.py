from io import StringIO
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from users.models import User
from tours.models import Excursion, Destination

@override_settings(DEBUG=False)
class PublicCatalogTests(TestCase):
    def test_normal_demo_is_refused_in_production(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_public_catalog_has_no_shared_login_or_administrator(self):
        call_command('seed_demo', public_catalog=True, stdout=StringIO())
        self.assertEqual(Excursion.objects.filter(status='approved').count(), 12)
        self.assertFalse(User.objects.filter(is_staff=True).exists())
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
        self.assertTrue(User.objects.exists())
        for user in User.objects.all():
            self.assertFalse(user.has_usable_password())
            self.assertFalse(user.check_password('GoTrip2026!'))
        response = self.client.get('/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Популярные направления')

    def test_public_seed_refuses_existing_demo_credentials_before_any_changes(self):
        original = User.objects.create_user(username='original', email='tourist@gotrip.local', password='SharedPassword!')
        with self.assertRaises(CommandError):
            call_command('seed_demo', public_catalog=True, stdout=StringIO())
        self.assertFalse(Destination.objects.exists())
        original.refresh_from_db()
        self.assertTrue(original.check_password('SharedPassword!'))

    def test_public_catalog_can_be_repeated_without_duplicate_tours(self):
        for _ in range(2):
            call_command('seed_demo', public_catalog=True, stdout=StringIO())
        self.assertEqual(Excursion.objects.count(), 13)
        self.assertEqual(User.objects.count(), 5)
