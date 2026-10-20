from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils import timezone
from core.forms import PhotoFormMixin
from .models import Excursion, Departure, Review, TourPhoto

class ExcursionForm(PhotoFormMixin, forms.ModelForm):
    class Meta:
        model = Excursion
        fields = ['title', 'destination', 'categories', 'description', 'meeting_point', 'duration', 'price', 'image']
        widgets = {'description': forms.Textarea(attrs={'rows': 7}), 'categories': forms.CheckboxSelectMultiple()}
    def clean_description(self):
        value = self.cleaned_data['description'].strip()
        if len(value) < 80: raise forms.ValidationError('Добавьте подробное описание: минимум 80 символов.')
        return value

class DepartureForm(forms.ModelForm):
    class Meta:
        model = Departure
        fields = ['date', 'capacity']
        widgets = {'date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}
    def clean_date(self):
        value = self.cleaned_data.get('date')
        if value and value < timezone.localdate() and not self.instance.pk:
            raise forms.ValidationError('Новая дата не может быть в прошлом.')
        return value
    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.reserved:
            if cleaned.get('DELETE') or cleaned.get('date') != self.instance.date:
                raise forms.ValidationError('Нельзя удалить или перенести дату с бронированиями.')
            if cleaned.get('capacity', 0) < self.instance.reserved:
                raise forms.ValidationError('Вместимость меньше числа забронированных мест.')
        return cleaned

class SafeDepartureFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if form.instance.pk and form.instance.bookings.exists():
                if form.cleaned_data.get('DELETE') or 'date' in form.changed_data:
                    raise forms.ValidationError('Дату с историей бронирований нельзя переносить или удалять.')

DepartureFormSet = inlineformset_factory(Excursion, Departure, form=DepartureForm, formset=SafeDepartureFormSet, extra=2, can_delete=True, min_num=1, validate_min=True)
class PhotoForm(PhotoFormMixin, forms.ModelForm):
    class Meta:
        model = TourPhoto
        fields = ['image']
PhotoFormSet = inlineformset_factory(Excursion, TourPhoto, form=PhotoForm, extra=2, max_num=8, validate_max=True, can_delete=True)

class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(label='Оценка', coerce=int, choices=[(5,'★★★★★ — Отлично'),(4,'★★★★ — Хорошо'),(3,'★★★ — Нормально'),(2,'★★ — Плохо'),(1,'★ — Очень плохо')])
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {'text': forms.Textarea(attrs={'rows': 4})}
    def clean_text(self):
        value = self.cleaned_data['text'].strip()
        if len(value) < 10: raise forms.ValidationError('Напишите минимум 10 символов.')
        return value
