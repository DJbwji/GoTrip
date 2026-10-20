import uuid
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Profile, GuideApplication
from core.forms import validate_photo

class SignupForm(UserCreationForm):
    first_name = forms.CharField(label='Ваше имя', max_length=150)
    email = forms.EmailField(label='Email')
    class Meta:
        model = User
        fields = ['first_name', 'email', 'password1', 'password2']
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Этот email уже зарегистрирован.')
        return email
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = uuid.uuid4().hex
        if commit: user.save()
        return user

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    def clean(self):
        email = self.cleaned_data.get('username', '')
        user = User.objects.filter(email__iexact=email).first()
        self.cleaned_data['username'] = user.username if user else email
        return super().clean()

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Имя', max_length=150)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'city', 'bio', 'interests', 'avatar']
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}
    def clean_avatar(self): return validate_photo(self.cleaned_data.get('avatar'))

class GuideForm(forms.ModelForm):
    class Meta:
        model = GuideApplication
        fields = ['experience', 'phone']
        widgets = {'experience': forms.Textarea(attrs={'rows': 6})}
    def clean_experience(self):
        value = self.cleaned_data['experience'].strip()
        if len(value) < 40: raise forms.ValidationError('Расскажите об опыте подробнее: минимум 40 символов.')
        return value
    def clean_phone(self):
        value = self.cleaned_data['phone']
        if sum(c.isdigit() for c in value) < 10: raise forms.ValidationError('Укажите корректный номер телефона.')
        return value
