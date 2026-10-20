from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse

class Trip(models.Model):
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_trips', verbose_name='Организатор')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_trips', blank=True, verbose_name='Участники')
    destination = models.ForeignKey('tours.Destination', on_delete=models.PROTECT, related_name='trips', verbose_name='Направление')
    title = models.CharField('Название', max_length=180)
    description = models.TextField('План путешествия')
    start_date = models.DateField('Начало')
    end_date = models.DateField('Окончание')
    capacity = models.PositiveIntegerField('Максимум участников', default=6, validators=[MinValueValidator(2), MaxValueValidator(50)])
    image = models.ImageField('Фото', upload_to='trips/', blank=True)
    class Meta:
        ordering = ['start_date']
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')), name='trip_valid_dates')]
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('trips:detail', args=[self.pk])
    @property
    def count(self): return self.participants.count()
