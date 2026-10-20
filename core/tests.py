from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from PIL import Image
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from users.models import User, Profile, GuideApplication
from tours.models import Excursion, Destination, Category, Departure, Review
from trips.models import Trip
from bookings.models import Booking
from messaging.models import Conversation, Message
from moderation.models import Complaint

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PlatformTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tourist = User.objects.create_user(username='tourist',email='tourist@example.com',password='TestPassword2026!',first_name='Турист')
        cls.guide = User.objects.create_user(username='guide',email='guide@example.com',password='TestPassword2026!',first_name='Гид')
        cls.other = User.objects.create_user(username='other',email='other@example.com',password='TestPassword2026!')
        cls.staff = User.objects.create_user(username='staff',email='staff@example.com',password='TestPassword2026!',is_staff=True,is_superuser=True)
        for user in (cls.tourist,cls.guide,cls.other,cls.staff): Profile.objects.create(user=user)
        GuideApplication.objects.create(user=cls.guide,experience='Много лет провожу авторские экскурсии по городу.',phone='+79991234567',status='approved')
        cls.destination = Destination.objects.create(name='Италия')
        cls.category = Category.objects.create(name='Семейный')
        cls.tour = Excursion.objects.create(guide=cls.guide,destination=cls.destination,title='Прогулка по Риму',description='Подробная история прекрасного города. '*6,meeting_point='Площадь',price=2000,duration=3,status='approved',asset='italy.jpg')
        cls.tour.categories.add(cls.category)
        cls.departure = Departure.objects.create(excursion=cls.tour,date=timezone.localdate()+timedelta(days=10),capacity=3)
        cls.trip = Trip.objects.create(organizer=cls.other,destination=cls.destination,title='В Рим вместе',description='План поездки',start_date=timezone.localdate()+timedelta(days=15),end_date=timezone.localdate()+timedelta(days=18),capacity=2)
        cls.trip.participants.add(cls.other)
    def login(self,user=None): self.client.force_login(user or self.tourist)
    def completed(self):
        departure=Departure.objects.create(excursion=self.tour,date=timezone.localdate()-timedelta(days=2),capacity=5,reserved=1)
        return Booking.objects.create(user=self.tourist,departure=departure,people=1,total=2000,status='paid')
    def edit_data(self):
        return {'title':self.tour.title,'destination':self.destination.pk,'categories':[self.category.pk],
            'description':self.tour.description,'meeting_point':'Площадь','duration':3,'price':'2500',
            'dates-TOTAL_FORMS':1,'dates-INITIAL_FORMS':1,'dates-MIN_NUM_FORMS':1,'dates-MAX_NUM_FORMS':1000,
            'dates-0-id':self.departure.pk,'dates-0-excursion':self.tour.pk,'dates-0-date':str(self.departure.date),'dates-0-capacity':3,
            'photos-TOTAL_FORMS':0,'photos-INITIAL_FORMS':0,'photos-MIN_NUM_FORMS':0,'photos-MAX_NUM_FORMS':8}

    def test_public_pages_render(self):
        for name,args in [('core:home',[]),('core:about',[]),('tours:catalog',[]),('tours:detail',[self.tour.pk]),('trips:list',[]),('trips:detail',[self.trip.pk]),('users:login',[]),('users:signup',[]),('users:guides',[]),('users:guide',[self.guide.pk]),('users:password_reset',[])]:
            with self.subTest(page=name): self.assertEqual(self.client.get(reverse(name,args=args)).status_code,200)
    def test_private_pages_require_login(self):
        for name in ['users:dashboard','users:profile','users:guide_apply','tours:create','trips:create','messaging:inbox','moderation:queue']:
            with self.subTest(page=name): self.assertEqual(self.client.get(reverse(name)).status_code,302)
    def test_email_login_case_insensitive(self):
        response=self.client.post(reverse('users:login'),{'username':'TOURIST@example.com','password':'TestPassword2026!'})
        self.assertRedirects(response,reverse('users:dashboard'))
    def test_registration_and_duplicate_email(self):
        data={'first_name':'Новый','email':'New@example.com','password1':'TravelStrong2026!','password2':'TravelStrong2026!'}
        self.client.post(reverse('users:signup'),data)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
        self.assertEqual(len(mail.outbox),1)
        self.client.logout()
        data['email']='NEW@example.com'
        response=self.client.post(reverse('users:signup'),data)
        self.assertContains(response,'Этот email уже зарегистрирован.')
    def test_logout_only_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse('users:logout')).status_code,405)
        self.assertEqual(self.client.post(reverse('users:logout')).status_code,302)
    def test_password_reset_sends_namespaced_link(self):
        self.client.post(reverse('users:password_reset'),{'email':self.tourist.email})
        self.assertEqual(len(mail.outbox),1)
        self.assertIn('/account/password/',mail.outbox[0].body)
    def test_catalog_filters_and_invalid_data(self):
        self.assertContains(self.client.get(reverse('tours:catalog'),{'q':'рИМУ','budget':2000,'people':3,'date':str(self.departure.date)}),self.tour.title)
        self.assertNotContains(self.client.get(reverse('tours:catalog'),{'people':4}),self.tour.title)
        self.assertNotContains(self.client.get(reverse('tours:catalog'),{'budget':100}),self.tour.title)
        self.assertEqual(self.client.get(reverse('tours:catalog'),{'destination':'not-a-number','date':'invalid'}).status_code,200)
    def test_catalog_pagination_preserves_query(self):
        for i in range(11):
            Excursion.objects.create(guide=self.guide,destination=self.destination,title=f'Рим {i}',description='x',meeting_point='x',price=100,status='approved')
        response=self.client.get(reverse('tours:catalog'),{'destination':self.destination.pk})
        self.assertEqual(len(response.context['excursions']),9)
        self.assertContains(response,'destination=1&amp;page=2')
    def test_draft_invisible_to_guests_and_other_users(self):
        self.tour.status='draft'; self.tour.save()
        self.assertNotContains(self.client.get(reverse('tours:catalog')),self.tour.title)
        self.assertEqual(self.client.get(self.tour.get_absolute_url()).status_code,403)
        self.login(self.guide)
        self.assertEqual(self.client.get(self.tour.get_absolute_url()).status_code,200)
    def test_only_approved_guides_can_create(self):
        self.login()
        self.assertEqual(self.client.get(reverse('tours:create')).status_code,403)
        self.login(self.guide)
        self.assertEqual(self.client.get(reverse('tours:create')).status_code,200)
    def test_only_owner_can_edit_delete(self):
        self.login()
        for name in ['tours:edit','tours:delete']:
            self.assertIn(self.client.post(reverse(name,args=[self.tour.pk]),{}).status_code,[403,404])
        for name in ['trips:edit','trips:delete']:
            self.assertEqual(self.client.post(reverse(name,args=[self.trip.pk]),{}).status_code,404)
    def test_guide_application_and_approval(self):
        self.login()
        self.client.post(reverse('users:guide_apply'),{'experience':'Много лет изучаю историю города и провожу интересные экскурсии.','phone':'+79991234567'})
        app=GuideApplication.objects.get(user=self.tourist)
        self.assertEqual(app.status,'pending'); self.assertEqual(len(mail.outbox),1)
        self.login(self.staff)
        self.client.post(reverse('moderation:decision',args=['guide',app.pk]),{'status':'approved'})
        self.assertTrue(User.objects.get(pk=self.tourist.pk).is_guide)
    def test_submission_revision_resubmit_approval(self):
        self.tour.status='draft';self.tour.save()
        self.login(self.guide)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('tours:submit',args=[self.tour.pk]))
        self.tour.refresh_from_db();self.assertEqual(self.tour.status,'pending')
        self.assertEqual(len(mail.outbox),1)
        self.login(self.staff)
        url=reverse('moderation:decision',args=['excursion',self.tour.pk])
        self.assertEqual(self.client.post(url,{'status':'revision'}).status_code,200)
        self.tour.refresh_from_db();self.assertEqual(self.tour.status,'pending')
        self.client.post(url,{'status':'revision','comment':'Уточните место встречи'})
        self.tour.refresh_from_db();self.assertEqual(self.tour.status,'revision')
        self.login(self.guide)
        self.client.post(reverse('tours:submit',args=[self.tour.pk]))
        self.login(self.staff)
        self.client.post(url,{'status':'approved'})
        self.tour.refresh_from_db();self.assertEqual(self.tour.status,'approved')
        self.assertContains(self.client.get(reverse('tours:catalog')),self.tour.title)
    def test_non_staff_cannot_moderate(self):
        self.login()
        response=self.client.post(reverse('moderation:decision',args=['excursion',self.tour.pk]),{'status':'rejected','comment':'x'})
        self.assertEqual(response.status_code,302)
        self.tour.refresh_from_db();self.assertEqual(self.tour.status,'approved')
    def test_edit_published_tour_returns_to_draft(self):
        self.login(self.guide)
        self.assertEqual(self.client.post(reverse('tours:edit',args=[self.tour.pk]),self.edit_data()).status_code,302)
        self.tour.refresh_from_db();self.assertEqual(self.tour.status,'draft')
        self.assertNotContains(self.client.get(reverse('tours:catalog')),self.tour.title)
    def test_booked_departure_cannot_be_moved(self):
        self.departure.reserved=1;self.departure.save()
        self.login(self.guide)
        data=self.edit_data();data['dates-0-date']=str(self.departure.date+timedelta(days=1))
        response=self.client.post(reverse('tours:edit',args=[self.tour.pk]),data)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Нельзя удалить или перенести')
    def test_booking_reserves_and_cannot_overbook(self):
        self.login()
        url=reverse('bookings:create',args=[self.tour.pk])
        self.client.post(url,{'departure':self.departure.pk,'people':2,'total':'1'})
        booking=Booking.objects.get()
        self.assertEqual(booking.total,4000)
        self.departure.refresh_from_db();self.assertEqual(self.departure.available,1)
        self.client.post(url,{'departure':self.departure.pk,'people':2})
        self.assertEqual(Booking.objects.count(),1)
    def test_cancellation_is_idempotent_and_releases_seats(self):
        self.login()
        self.client.post(reverse('bookings:create',args=[self.tour.pk]),{'departure':self.departure.pk,'people':2})
        booking=Booking.objects.get()
        for _ in range(2): self.client.post(reverse('bookings:cancel',args=[booking.pk]))
        self.departure.refresh_from_db();self.assertEqual(self.departure.reserved,0)
        booking.refresh_from_db();self.assertEqual(booking.status,'cancelled')
    @override_settings(DEMO_PAYMENTS=True)
    def test_payment_is_owner_only_and_idempotent(self):
        self.login()
        self.client.post(reverse('bookings:create',args=[self.tour.pk]),{'departure':self.departure.pk,'people':1})
        booking=Booking.objects.get()
        self.login(self.other)
        url=reverse('bookings:payment',args=[booking.pk])
        self.assertEqual(self.client.post(url).status_code,404)
        self.login()
        self.client.post(url);self.client.post(url)
        booking.refresh_from_db();self.assertEqual(booking.status,'paid')
        self.departure.refresh_from_db();self.assertEqual(self.departure.reserved,1)
    @override_settings(DEMO_PAYMENTS=False)
    def test_payments_disabled_without_provider(self):
        self.login()
        self.client.post(reverse('bookings:create',args=[self.tour.pk]),{'departure':self.departure.pk,'people':1})
        booking=Booking.objects.get()
        self.client.post(reverse('bookings:payment',args=[booking.pk]))
        booking.refresh_from_db();self.assertEqual(booking.status,'pending')
    def test_review_only_after_completed_paid_booking(self):
        self.login()
        url=reverse('tours:review',args=[self.tour.pk])
        self.assertEqual(self.client.post(url,{'rating':5,'text':'Отличная прогулка!'}).status_code,403)
        self.completed()
        self.client.post(url,{'rating':5,'text':'Отличная прогулка!'})
        self.assertEqual(Review.objects.count(),1)
        self.client.post(url,{'rating':4,'text':'Дополненный отзыв о прогулке'})
        self.assertEqual(Review.objects.count(),1)
        self.assertEqual(Review.objects.get().rating,4)
    def test_complaint_requires_completed_booking_and_notifies(self):
        self.login()
        url=reverse('moderation:complain',args=[self.tour.pk])
        self.assertEqual(self.client.get(url).status_code,403)
        self.completed()
        self.client.post(url,{'text':'Непонятно указано место встречи, просим уточнить.'})
        self.assertEqual(Complaint.objects.count(),1)
        self.assertEqual(len(mail.outbox),1)
    def test_trip_membership_capacity_and_leave(self):
        self.login()
        url=reverse('trips:join',args=[self.trip.pk])
        self.client.post(url);self.assertEqual(self.trip.count,2)
        self.login(self.guide)
        self.client.post(url);self.assertEqual(self.trip.count,2)
        self.login()
        self.client.post(url);self.assertEqual(self.trip.count,1)
    def test_organizer_cannot_leave(self):
        self.login(self.other)
        self.client.post(reverse('trips:join',args=[self.trip.pk]))
        self.assertTrue(self.trip.participants.filter(pk=self.other.pk).exists())
    def test_trip_dates_validation(self):
        self.login()
        response=self.client.post(reverse('trips:create'),{'title':'Новая поездка','destination':self.destination.pk,'description':'Описание','start_date':'2020-01-02','end_date':'2020-01-01','capacity':4})
        self.assertEqual(response.status_code,200)
        self.assertEqual(Trip.objects.count(),1)
    def test_trip_create_update_delete(self):
        self.login()
        data={'title':'Новый маршрут','destination':self.destination.pk,'description':'Описание путешествия','start_date':str(timezone.localdate()+timedelta(days=30)),'end_date':str(timezone.localdate()+timedelta(days=31)),'capacity':4}
        self.client.post(reverse('trips:create'),data)
        trip=Trip.objects.get(title='Новый маршрут')
        self.assertTrue(trip.participants.filter(pk=self.tourist.pk).exists())
        data['title']='Обновлённый маршрут'
        self.client.post(reverse('trips:edit',args=[trip.pk]),data)
        trip.refresh_from_db();self.assertEqual(trip.title,data['title'])
        self.client.post(reverse('trips:delete',args=[trip.pk]))
        self.assertFalse(Trip.objects.filter(pk=trip.pk).exists())
    def test_chat_is_private(self):
        self.login()
        self.client.post(reverse('messaging:start',args=[self.guide.pk]))
        chat=Conversation.objects.get()
        url=reverse('messaging:chat',args=[chat.pk])
        self.client.post(url,{'text':'Здравствуйте, где встречаемся?'})
        self.assertEqual(Message.objects.count(),1)
        self.login(self.other)
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{'text':'Вторжение'}).status_code,403)
        self.assertEqual(Message.objects.count(),1)
    def test_favorite_ajax(self):
        self.login()
        url=reverse('tours:favorite',args=[self.tour.pk])
        self.assertTrue(self.client.post(url,HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()['saved'])
        self.assertFalse(self.client.post(url,HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()['saved'])
    def test_csrf_required(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.tourist)
        self.assertEqual(client.post(reverse('trips:join',args=[self.trip.pk])).status_code,403)
    def test_avatar_upload_resizes(self):
        self.login()
        output=BytesIO();Image.new('RGB',(2400,1800),'orange').save(output,'PNG')
        with TemporaryDirectory() as temp, override_settings(MEDIA_ROOT=temp):
            self.client.post(reverse('users:profile'),{'first_name':'Анна','avatar':SimpleUploadedFile('avatar.png',output.getvalue(),content_type='image/png')})
            self.tourist.profile.refresh_from_db()
            with Image.open(self.tourist.profile.avatar.path) as img:
                self.assertLessEqual(img.width,1600);self.assertLessEqual(img.height,1200)
    def test_authenticated_pages_render(self):
        self.login(self.guide)
        for name,args in [('users:dashboard',[]),('users:profile',[]),('tours:edit',[self.tour.pk]),('trips:create',[]),('messaging:inbox',[])]:
            with self.subTest(page=name): self.assertEqual(self.client.get(reverse(name,args=args)).status_code,200)
        self.login(self.staff)
        for name,args in [('moderation:queue',[]),('moderation:decision',['excursion',self.tour.pk]),('admin:index',[])]:
            with self.subTest(page=name): self.assertEqual(self.client.get(reverse(name,args=args)).status_code,200)

    def test_tour_create_with_image_and_dates(self):
        self.login(self.guide)
        output=BytesIO();Image.new('RGB',(400,300),'orange').save(output,'PNG')
        data=self.edit_data()
        data.update({'title':'Новая прогулка','dates-INITIAL_FORMS':0})
        data.pop('dates-0-id');data.pop('dates-0-excursion')
        data['image']=SimpleUploadedFile('tour.png',output.getvalue(),content_type='image/png')
        with TemporaryDirectory() as temp, override_settings(MEDIA_ROOT=temp):
            response=self.client.post(reverse('tours:create'),data)
            self.assertEqual(response.status_code,302)
            tour=Excursion.objects.get(title='Новая прогулка')
            self.assertEqual(tour.status,'draft')
            self.assertEqual(tour.departures.count(),1)
            self.assertTrue(tour.image)
            self.client.post(reverse('tours:submit',args=[tour.pk]))
            tour.refresh_from_db();self.assertEqual(tour.status,'pending')
    def test_booked_date_cannot_be_deleted_even_with_zero_reserved(self):
        Booking.objects.create(user=self.tourist,departure=self.departure,people=1,total=2000,status='cancelled')
        self.login(self.guide)
        data=self.edit_data()
        data.update({'dates-TOTAL_FORMS':2,'dates-0-DELETE':'on','dates-1-date':str(self.departure.date+timedelta(days=10)),'dates-1-capacity':4})
        response=self.client.post(reverse('tours:edit',args=[self.tour.pk]),data)
        self.assertEqual(response.status_code,200)
        self.assertTrue(Departure.objects.filter(pk=self.departure.pk).exists())
    def test_tour_delete_preserves_booking_history(self):
        self.completed();self.login(self.guide)
        self.client.post(reverse('tours:delete',args=[self.tour.pk]))
        self.assertTrue(Excursion.objects.filter(pk=self.tour.pk).exists())
    def test_tour_delete_without_bookings(self):
        self.login(self.guide)
        self.client.post(reverse('tours:delete',args=[self.tour.pk]))
        self.assertFalse(Excursion.objects.filter(pk=self.tour.pk).exists())
