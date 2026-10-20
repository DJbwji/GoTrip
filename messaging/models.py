from django.conf import settings
from django.db import models

class Conversation(models.Model):
    tourist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tourist_chats', verbose_name='Турист')
    guide = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='guide_chats', verbose_name='Гид')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Диалог'
        verbose_name_plural = 'Диалоги'
        constraints = [models.UniqueConstraint(fields=['tourist', 'guide'], name='unique_conversation')]
    def __str__(self): return f'{self.tourist} — {self.guide}'

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name='Диалог')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    text = models.TextField('Сообщение', max_length=3000)
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
    def __str__(self): return self.text[:60]
