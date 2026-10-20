from django.conf import settings
from django.db import models

class Activity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities', verbose_name='Пользователь')
    text = models.CharField('Событие', max_length=255)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Событие'
        verbose_name_plural = 'История активности'

    def __str__(self):
        return self.text
