import uuid
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

class Booking(models.Model):
    STATUS = [('pending', 'Ожидает оплаты'), ('paid', 'Оплачено'), ('cancelled', 'Отменено')]
    reference = models.UUIDField('Номер', default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bookings', verbose_name='Турист')
    departure = models.ForeignKey('tours.Departure', on_delete=models.PROTECT, related_name='bookings', verbose_name='Дата экскурсии')
    people = models.PositiveIntegerField('Количество гостей', validators=[MinValueValidator(1), MaxValueValidator(20)])
    total = models.DecimalField('Сумма, ₽', max_digits=12, decimal_places=2)
    status = models.CharField('Статус', max_length=15, choices=STATUS, default='pending')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
    def __str__(self): return str(self.reference)[:8]
