from django import forms
from django.utils import timezone
from tours.models import Departure

class BookingForm(forms.Form):
    departure = forms.ModelChoiceField(label='Дата экскурсии', queryset=Departure.objects.none())
    people = forms.IntegerField(label='Количество гостей', min_value=1, max_value=20, initial=1)
    def __init__(self, *args, excursion, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departure'].queryset = excursion.departures.filter(date__gte=timezone.localdate())
    def clean(self):
        data = super().clean()
        if data.get('departure') and data.get('people') and data['people'] > data['departure'].available:
            raise forms.ValidationError('На эту дату недостаточно свободных мест.')
        return data
