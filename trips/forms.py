from django import forms
from django.utils import timezone
from core.forms import PhotoFormMixin
from .models import Trip

class TripForm(PhotoFormMixin, forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['title', 'destination', 'description', 'start_date', 'end_date', 'capacity', 'image']
        widgets = {'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type':'date'}), 'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'type':'date'}), 'description': forms.Textarea(attrs={'rows':5})}
    def clean_start_date(self):
        value = self.cleaned_data['start_date']
        if value < timezone.localdate(): raise forms.ValidationError('Выберите будущую дату.')
        return value
    def clean(self):
        data = super().clean()
        if data.get('end_date') and data.get('start_date') and data['end_date'] < data['start_date']:
            self.add_error('end_date', 'Окончание должно быть не раньше начала.')
        if self.instance.pk and data.get('capacity', 0) < self.instance.count:
            self.add_error('capacity', 'Уже присоединилось больше участников.')
        return data
