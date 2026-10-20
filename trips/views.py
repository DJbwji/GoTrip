from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Lower
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
from core.services import record, resize_image
from tours.models import Destination
from .models import Trip
from .forms import TripForm

class TripList(ListView):
    template_name = 'trips/list.html'
    context_object_name = 'trips'
    paginate_by = 12
    def get_queryset(self):
        qs = Trip.objects.filter(start_date__gte=timezone.localdate()).select_related('destination','organizer').prefetch_related('participants')
        q = self.request.GET.get('q','').strip()[:100]
        if q: qs = qs.alias(destination_lower=Lower('destination__name')).filter(destination_lower__contains=q.lower())
        return qs
class TripDetail(DetailView):
    model = Trip
    template_name = 'trips/detail.html'
    context_object_name = 'trip'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['joined'] = self.request.user.is_authenticated and self.object.participants.filter(pk=self.request.user.pk).exists()
        ctx['started'] = self.object.start_date < timezone.localdate()
        return ctx

@login_required
def edit(request, pk=None):
    obj = get_object_or_404(Trip, pk=pk, organizer=request.user) if pk else Trip(organizer=request.user)
    form = TripForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            if request.FILES.get('image'): obj.image = resize_image(form.cleaned_data['image'])
            obj.save()
            obj.participants.add(request.user)
        record(request.user, f'Сохранена поездка: {obj.title}')
        return redirect(obj)
    return render(request, 'shared/form.html', {'form':form, 'title':'Редактирование поездки' if pk else 'Найдите своих людей', 'eyebrow':'Совместное путешествие'})

@login_required
def delete(request, pk):
    obj = get_object_or_404(Trip, pk=pk, organizer=request.user)
    if request.method == 'POST':
        record(request.user, f'Удалена поездка: {obj.title}')
        obj.delete()
        return redirect('trips:list')
    return render(request, 'shared/confirm_delete.html', {'object':obj})

@login_required
@require_POST
def join(request, pk):
    with transaction.atomic():
        # Write lock first also serializes membership changes on SQLite.
        Trip.objects.filter(pk=pk).update(capacity=F('capacity'))
        trip = get_object_or_404(Trip.objects.select_for_update(), pk=pk)
        if trip.start_date < timezone.localdate():
            messages.error(request, 'Поездка уже началась.')
        elif request.user.pk == trip.organizer_id:
            messages.info(request, 'Вы организатор этой поездки.')
        elif trip.participants.filter(pk=request.user.pk).exists():
            trip.participants.remove(request.user)
            record(request.user, f'Вы вышли из поездки: {trip.title}')
        elif trip.count >= trip.capacity:
            messages.error(request, 'Все места уже заняты.')
        else:
            trip.participants.add(request.user)
            record(request.user, f'Вы присоединились к поездке: {trip.title}')
            messages.success(request, 'Вы в команде! Хорошего путешествия.')
    return redirect(trip)
