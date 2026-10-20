from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from users.models import User, Profile, GuideApplication
from tours.models import Destination, Category, Excursion, Departure, Review
from trips.models import Trip
from bookings.models import Booking
from messaging.models import Conversation, Message
from moderation.models import Complaint
from core.models import Activity

class Command(BaseCommand):
    help = 'Create repeatable demonstration data. Does not reset existing accounts.'
    def add_arguments(self, parser):
        parser.add_argument('--public-catalog', action='store_true', help='Seed a public catalog with login-disabled sample accounts and no demo administrator.')

    def handle(self, *args, **options):
        public = options.get('public_catalog', False)
        if not settings.DEBUG and not public:
            raise CommandError('Demo accounts may only be created with DEBUG=True. Use --public-catalog for hosted sample content.')
        if public:
            sample_emails = ['tourist@gotrip.local', 'guide@gotrip.local', 'ivan@gotrip.local', 'marina@gotrip.local', 'newguide@gotrip.local', 'admin@gotrip.local']
            existing = User.objects.filter(email__in=sample_emails)
            if any(account.has_usable_password() or account.is_staff or account.is_superuser for account in existing):
                raise CommandError('Existing sample accounts have login access. Use a fresh hosting database; do not publish the local demonstration database.')
        def user(email, name, **flags):
            obj, created = User.objects.get_or_create(email=email, defaults={'username':email,'first_name':name, **flags})
            if created:
                if public:
                    obj.set_unusable_password()
                else:
                    obj.set_password('GoTrip2026!')
                obj.save()
                Activity.objects.create(user=obj, text='Добро пожаловать в GoTrip!')
            Profile.objects.get_or_create(user=obj)
            return obj
        traveler = user('tourist@gotrip.local','Александра')
        guide = user('guide@gotrip.local','Анна')
        admin = None if public else user('admin@gotrip.local','Модератор',is_staff=True,is_superuser=True)
        other = user('ivan@gotrip.local','Иван')
        marina = user('marina@gotrip.local','Марина')
        applicant = user('newguide@gotrip.local','Михаил')
        profile = guide.profile
        profile.city = 'Рим · Тбилиси'
        profile.bio = 'Влюбляю в города через их истории, людей и маленькие детали. Уже 7 лет создаю авторские маршруты: от уютных итальянских двориков до горных троп Кавказа. Покажу места, которые сложно найти в путеводителях.'
        profile.interests = 'История, гастрономия, пешие маршруты'
        profile.save()
        GuideApplication.objects.get_or_create(user=guide, defaults={'experience':profile.bio,'phone':'+7 999 123-45-67','status':'approved'})
        GuideApplication.objects.get_or_create(user=applicant, defaults={'experience':'Провожу прогулки по историческим районам города. Пять лет изучаю архитектуру, историю и местную кухню. Хочу поделиться любимыми местами с путешественниками.','phone':'+7 999 555-12-34'})
        names = [('Италия','dolce vita','italy.jpg'),('Франция','искусство жить','france.jpg'),('Грузия','ближе к горам','georgia.jpg'),('Турция','другой мир','turkey.jpg'),('Япония','своя гармония','japan.jpg')]
        destinations = [Destination.objects.get_or_create(name=n,defaults={'subtitle':s,'asset':a})[0] for n,s,a in names]
        cats = [Category.objects.get_or_create(name=n)[0] for n in ['Активный отдых','Семейный','Романтический','Гастрономический','Культурный']]
        titles = [
            ('Побережье Амальфи: навстречу морю',0,4900,2),
            ('Париж, который знают только местные',1,3500,4),
            ('Казбеги: наедине с большими горами',2,6800,0),
            ('Каппадокия на рассвете',3,7500,2),
            ('Киото: сады, храмы и чайные истории',4,5200,4),
            ('Вкус Рима: от рынка до траттории',0,4200,3),
            ('Монмартр: прогулка для всей семьи',1,2900,1),
            ('Тбилиси: вино, дворики и разговоры',2,2800,3),
            ('Стамбул между двух континентов',3,3900,4),
            ('Токио: маленькие открытия большого города',4,5900,1),
            ('Закат над Флоренцией',0,3200,2),
            ('Грузия: тропами к водопадам',2,4500,0)]
        today = timezone.localdate()
        tours = []
        for i,(title,dest,price,cat) in enumerate(titles):
            d = destinations[dest]
            tour,created = Excursion.objects.get_or_create(title=title, guide=guide, defaults={
                'destination':d,'description':f'{title} — путешествие без спешки и шумных туристических групп. Вместе мы откроем характер этого места, познакомимся с местными традициями и найдём лучшие точки для фотографий.\n\nНачнём со встречи в центре, пройдём по живописным улочкам и остановимся в любимом кафе местных жителей. Я расскажу истории, которые стоят за фасадами, подскажу, что попробовать и куда заглянуть самостоятельно.\n\nМаршрут подойдёт всем, кто любит живые впечатления. Возьмите удобную обувь, воду и хорошее настроение. В стоимость входит сопровождение гида; еда и транспорт оплачиваются отдельно.',
                'meeting_point':'У центрального туристического информационного центра. Точное место уточним в чате.',
                'duration':3 + i % 3,'price':price,'asset':d.asset,'status':'approved'})
            if created: tour.categories.add(cats[cat])
            for offset in (10,24,45):
                Departure.objects.get_or_create(excursion=tour,date=today+timedelta(days=offset+i),defaults={'capacity':8})
            tours.append(tour)
        for i,tour in enumerate(tours[:5]):
            past,_ = Departure.objects.get_or_create(excursion=tour,date=today-timedelta(days=10+i),defaults={'capacity':8,'reserved':1})
            Booking.objects.get_or_create(user=traveler,departure=past,defaults={'people':1,'total':tour.price,'status':'paid'})
            Review.objects.get_or_create(user=traveler,excursion=tour,defaults={'rating':5,'text':'Очень душевная прогулка! Анна показала удивительные места, о которых мы не прочитали бы в путеводителе. Понравился неспешный темп и внимание к каждому участнику.'})
        traveler.favorites.add(tours[0],tours[2])
        trip_titles = [('Рим на выходные',0,6),('Грузия: горы и вино',2,8),('Япония: Токио и окрестности',4,6),('Турция: навстречу рассвету',3,6)]
        for i,(title,dest,capacity) in enumerate(trip_titles):
            trip,created = Trip.objects.get_or_create(title=title,organizer=other,defaults={'destination':destinations[dest],'start_date':today+timedelta(days=15+i*9),'end_date':today+timedelta(days=19+i*9),'capacity':capacity,'description':'Собираем небольшую компанию для путешествия без суеты. Будем гулять, пробовать местную еду, встречать рассветы и делиться историями.\n\nВ первый день познакомимся за ужином, затем отправимся исследовать город и окрестности. План обсуждаем вместе — важно, чтобы каждому было интересно. Билеты и проживание бронируем самостоятельно.'})
            if created: trip.participants.add(other,marina,traveler)
        pending,_ = Excursion.objects.get_or_create(title='Тайные дворики Рима',guide=guide,defaults={'destination':destinations[0],'description':'Новый маршрут по тихим дворикам, семейным кафе и старинным площадям Рима. Поговорим о жизни местных жителей, попробуем настоящий эспрессо и увидим город с необычной стороны.','meeting_point':'Пьяцца Навона','duration':3,'price':3100,'asset':'italy.jpg','status':'pending'})
        pending.categories.add(cats[4])
        Departure.objects.get_or_create(excursion=pending,date=today+timedelta(days=30),defaults={'capacity':6})
        Complaint.objects.get_or_create(user=traveler,excursion=tours[1],defaults={'text':'Демонстрационное обращение: точка встречи была указана недостаточно точно. Просим дополнить описание понятными ориентирами.'})
        chat,_ = Conversation.objects.get_or_create(tourist=traveler,guide=guide)
        if not chat.messages.exists():
            Message.objects.create(conversation=chat,sender=traveler,text='Здравствуйте! Подскажите, подойдёт ли прогулка для первого знакомства с городом?')
            Message.objects.create(conversation=chat,sender=guide,text='Здравствуйте, Александра! Конечно. Покажу и главные места, и мои любимые тихие уголки. Буду рада знакомству!')
        if public:
            self.stdout.write(self.style.SUCCESS('Public catalog is ready. Sample accounts cannot sign in; no sample administrator was created.'))
        else:
            self.stdout.write(self.style.SUCCESS('Demo ready. tourist@gotrip.local / guide@gotrip.local / admin@gotrip.local | password: GoTrip2026!'))
