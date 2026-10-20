from django import forms

def validate_photo(upload):
    if upload and hasattr(upload, 'size') and upload.size > 8 * 1024 * 1024:
        raise forms.ValidationError('Изображение должно быть меньше 8 МБ.')
    return upload

class PhotoFormMixin:
    def clean_image(self):
        return validate_photo(self.cleaned_data.get('image'))

class SearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Поиск')
    destination = forms.IntegerField(required=False, min_value=1)
    category = forms.IntegerField(required=False, min_value=1)
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    budget = forms.DecimalField(required=False, min_value=1, max_digits=10, decimal_places=2)
    people = forms.IntegerField(required=False, min_value=1, max_value=20)
    sort = forms.ChoiceField(label="Сортировка", required=False, choices=[('', 'Рекомендуемые'), ('price', 'Сначала дешевле'), ('-price', 'Сначала дороже'), ('-created_at', 'Новинки')])
