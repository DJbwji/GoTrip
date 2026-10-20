from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

class User(AbstractUser):
    email = models.EmailField('Email', unique=True)
    class Meta:
        ordering = ['first_name', 'username']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = [models.UniqueConstraint(Lower('email'), name='user_email_ci_unique')]

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def is_guide(self):
        return GuideApplication.objects.filter(user=self, status='approved').exists()

    @property
    def rank(self):
        count = self.bookings.filter(status='paid', departure__date__lt=timezone.localdate()).count()
        return 'Легенда путешествий' if count >= 10 else 'Исследователь' if count >= 3 else 'Первооткрыватель'

    @property
    def guide_rank(self):
        count = self.excursions.filter(status='approved').count()
        return 'Мастер впечатлений' if count >= 10 else 'Опытный гид' if count >= 3 else 'Новый гид'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь')
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True)
    city = models.CharField('Город', max_length=100, blank=True)
    bio = models.TextField('О себе', max_length=2000, blank=True)
    interests = models.CharField('Интересы', max_length=255, blank=True)
    class Meta:
        ordering = ['user']
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
    def __str__(self):
        return str(self.user)

class GuideApplication(models.Model):
    STATUS = [('pending', 'На рассмотрении'), ('approved', 'Одобрено'), ('rejected', 'Отклонено'), ('revision', 'На доработку')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guide_application', verbose_name='Пользователь')
    experience = models.TextField('Опыт и квалификация')
    phone = models.CharField('Телефон', max_length=30)
    status = models.CharField('Статус', max_length=15, choices=STATUS, default='pending')
    comment = models.TextField('Комментарий модератора', blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Заявка гида'
        verbose_name_plural = 'Заявки гидов'
    def __str__(self):
        return f'{self.user}: {self.get_status_display()}'
