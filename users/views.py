from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from core.services import record, notify, resize_image
from .forms import SignupForm, ProfileForm, GuideForm
from .models import User, Profile, GuideApplication
from bookings.models import Booking

def signup(request):
    if request.user.is_authenticated: return redirect('users:dashboard')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        Profile.objects.create(user=user)
        login(request, user)
        record(user, 'Добро пожаловать в GoTrip!')
        notify('Добро пожаловать!', 'Ваш аккаунт создан. Открывайте мир вместе с GoTrip.', [user.email])
        return redirect('users:dashboard')
    return render(request, 'registration/signup.html', {'form':form})

@login_required
def dashboard(request):
    user = request.user
    return render(request, 'users/dashboard.html', {'bookings': user.bookings.select_related('departure__excursion'),
        'favorites': user.favorites.filter(status='approved'), 'trips':user.joined_trips.select_related('destination'),
        'excursions':user.excursions.all(),
        'guide_bookings':Booking.objects.filter(departure__excursion__guide=user).select_related('user','departure__excursion'), 'activities':user.activities.all()[:30],
        'application':GuideApplication.objects.filter(user=user).first(), 'complaints':user.complaints.select_related('excursion')})

@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile,
        initial={'first_name':request.user.first_name, 'last_name':request.user.last_name})
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if request.FILES.get('avatar'): obj.avatar = resize_image(form.cleaned_data['avatar'])
        obj.save()
        request.user.first_name = form.cleaned_data['first_name']
        request.user.last_name = form.cleaned_data['last_name']
        request.user.save(update_fields=['first_name','last_name'])
        record(request.user, 'Профиль обновлён')
        messages.success(request, 'Изменения сохранены.')
        return redirect('users:dashboard')
    return render(request, 'shared/form.html', {'form':form, 'title':'Мой профиль', 'eyebrow':'Личный кабинет'})

@login_required
def guide_apply(request):
    obj = GuideApplication.objects.filter(user=request.user).first()
    if obj and obj.status in ('approved','pending'):
        messages.info(request, 'Заявка уже одобрена или находится на рассмотрении.')
        return redirect('users:dashboard')
    form = GuideForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.status = 'pending'
        obj.comment = ''
        obj.save()
        record(request.user, 'Заявка на статус гида отправлена')
        notify('Новая заявка гида', f'{request.user} подал заявку. Проверьте кабинет модератора.')
        return redirect('users:dashboard')
    return render(request, 'shared/form.html', {'form':form, 'title':'Делитесь любимыми местами', 'eyebrow':'Стать гидом', 'button':'Отправить заявку'})

class GuideList(ListView):
    template_name = 'users/guides.html'
    context_object_name = 'guides'
    paginate_by = 12
    def get_queryset(self):
        return User.objects.filter(guide_application__status='approved').select_related('profile')

class GuideDetail(DetailView):
    template_name = 'users/guide.html'
    context_object_name = 'guide'
    def get_queryset(self):
        return User.objects.filter(guide_application__status='approved').select_related('profile')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['excursions'] = self.object.excursions.filter(status='approved')
        return context
