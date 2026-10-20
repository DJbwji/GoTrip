from django.conf import settings
from django.db import models

class Complaint(models.Model):
    STATUS = [('pending', 'На рассмотрении'), ('resolved', 'Обработано'), ('rejected', 'Отклонено')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints', verbose_name='Автор')
    excursion = models.ForeignKey('tours.Excursion', on_delete=models.CASCADE, related_name='complaints', verbose_name='Экскурсия')
    text = models.TextField('Описание жалобы', max_length=5000)
    status = models.CharField('Статус', max_length=15, choices=STATUS, default='pending')
    comment = models.TextField('Ответ модератора', blank=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
    def __str__(self): return f'Жалоба №{self.pk}: {self.excursion}'
