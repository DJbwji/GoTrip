from django import forms
from .models import Message
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows':3, 'placeholder':'Напишите сообщение…', 'maxlength':3000})}
    def clean_text(self):
        value = self.cleaned_data['text'].strip()
        if not value: raise forms.ValidationError('Введите сообщение.')
        return value
