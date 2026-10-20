from django import forms
from .models import Complaint
class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows':6})}
    def clean_text(self):
        value = self.cleaned_data['text'].strip()
        if len(value) < 20: raise forms.ValidationError('Опишите проблему подробнее: минимум 20 символов.')
        return value

class DecisionForm(forms.Form):
    status = forms.ChoiceField(label='Решение', choices=[('approved','Одобрено'), ('rejected','Отклонено'), ('revision','На доработку')])
    comment = forms.CharField(label='Комментарий', required=False, max_length=5000, widget=forms.Textarea(attrs={'rows':4}))
    def __init__(self, *args, complaint=False, **kwargs):
        super().__init__(*args, **kwargs)
        if complaint: self.fields['status'].choices = [('resolved','Обработано'), ('rejected','Отклонено')]
    def clean(self):
        data = super().clean()
        if data.get('status') in ('rejected','revision') and not data.get('comment','').strip():
            self.add_error('comment', 'Укажите причину решения.')
        return data
