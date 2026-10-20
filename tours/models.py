from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Avg
from django.urls import reverse

class Destination(models.Model):
    name = models.CharField('Направление', max_length=100, unique=True)
    subtitle = models.CharField('Подпись', max_length=150, blank=True)
    image = models.ImageField('Фото', upload_to='destinations/', blank=True)
    asset = models.CharField('Локальное фото', max_length=100, default='italy.jpg')
    class Meta:
        ordering = ['pk']
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'
    def __str__(self): return self.name

class Category(models.Model):
    name = models.CharField('Тип отдыха', max_length=80, unique=True)
    class Meta:
        ordering = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
    def __str__(self): return self.name

class Excursion(models.Model):
    STATUS = [('draft', 'Черновик'), ('pending', 'На рассмотрении'), ('approved', 'Одобрено'), ('rejected', 'Отклонено'), ('revision', 'На доработку')]
    guide = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='excursions', verbose_name='Гид')
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT, related_name='excursions', verbose_name='Направление')
    categories = models.ManyToManyField(Category, related_name='excursions', verbose_name='Тип отдыха')
    title = models.CharField('Название', max_length=180)
    description = models.TextField('Описание')
    meeting_point = models.CharField('Место встречи', max_length=255)
    duration = models.PositiveIntegerField('Длительность, часов', default=3, validators=[MinValueValidator(1), MaxValueValidator(720)])
    price = models.DecimalField('Стоимость, ₽', max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    image = models.ImageField('Главная фотография', upload_to='excursions/', blank=True)
    asset = models.CharField('Демонстрационное фото', max_length=100, blank=True)
    status = models.CharField('Статус', max_length=15, choices=STATUS, default='draft')
    moderation_comment = models.TextField('Комментарий модератора', blank=True)
    favorites = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorites', blank=True, verbose_name='В избранном')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Экскурсия'
        verbose_name_plural = 'Экскурсии'
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('tours:detail', args=[self.pk])
    @property
    def rating(self): return self.reviews.aggregate(value=Avg('rating'))['value']

class TourPhoto(models.Model):
    excursion = models.ForeignKey(Excursion, on_delete=models.CASCADE, related_name='photos', verbose_name='Экскурсия')
    image = models.ImageField('Фото', upload_to='gallery/')
    class Meta:
        ordering = ['pk']
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
    def __str__(self): return f'Фото {self.excursion}'

class Departure(models.Model):
    excursion = models.ForeignKey(Excursion, on_delete=models.CASCADE, related_name='departures', verbose_name='Экскурсия')
    date = models.DateField('Дата')
    capacity = models.PositiveIntegerField('Всего мест', validators=[MinValueValidator(1), MaxValueValidator(100)])
    reserved = models.PositiveIntegerField('Занято мест', default=0)
    class Meta:
        ordering = ['date']
        verbose_name = 'Дата экскурсии'
        verbose_name_plural = 'Даты экскурсий'
        constraints = [models.UniqueConstraint(fields=['excursion', 'date'], name='unique_tour_date'),
            models.CheckConstraint(condition=models.Q(reserved__lte=models.F('capacity')), name='departure_not_overbooked')]
    def __str__(self): return f'{self.date:%d.%m.%Y} · {self.available} мест'
    @property
    def available(self): return self.capacity - self.reserved

class Review(models.Model):
    excursion = models.ForeignKey(Excursion, on_delete=models.CASCADE, related_name='reviews', verbose_name='Экскурсия')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews', verbose_name='Автор')
    rating = models.PositiveSmallIntegerField('Оценка', validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField('Отзыв', max_length=3000)
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        constraints = [models.UniqueConstraint(fields=['user', 'excursion'], name='unique_user_review')]
    def __str__(self): return f'{self.user}: {self.rating}/5'
