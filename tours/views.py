from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from core.forms import SearchForm
from core.services import notify, record, resize_image
from bookings.forms import BookingForm
from .models import Excursion, Destination, Category, Review
from .forms import ExcursionForm, DepartureFormSet, PhotoFormSet, ReviewForm

class Catalog(ListView):
    template_name = 'tours/catalog.html'
    context_object_name = 'excursions'
    paginate_by = 9
    def get_queryset(self):
        qs = Excursion.objects.filter(status='approved').select_related('destination','guide').prefetch_related('categories')
        self.form = SearchForm(self.request.GET)
        if not self.form.is_valid(): return qs.none()
        data = self.form.cleaned_data
        if data.get('q'):
            query = data['q'].lower()
            qs = qs.alias(title_lower=Lower('title'), description_lower=Lower('description'), destination_lower=Lower('destination__name'))
            qs = qs.filter(Q(title_lower__contains=query) | Q(description_lower__contains=query) | Q(destination_lower__contains=query))
        if data.get('destination'): qs = qs.filter(destination_id=data['destination'])
        if data.get('category'): qs = qs.filter(categories=data['category'])
        if data.get('budget'): qs = qs.filter(price__lte=data['budget'])
        departures = Q(departures__date__gte=timezone.localdate())
        if data.get('date'): departures &= Q(departures__date=data['date'])
        if data.get('people'): departures &= Q(departures__capacity__gte=F('departures__reserved') + data['people'])
        if data.get('date') or data.get('people'): qs = qs.filter(departures)
        return qs.distinct().order_by(data.get('sort') or '-created_at')
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(form=self.form, destinations=Destination.objects.all(), categories=Category.objects.all())
        return ctx

def detail(request, pk):
    tour = get_object_or_404(Excursion.objects.select_related('guide','destination'), pk=pk)
    if tour.status != 'approved' and not (request.user.is_authenticated and (request.user.pk == tour.guide_id or request.user.is_staff)):
        raise PermissionDenied
    can_review = request.user.is_authenticated and request.user.bookings.filter(departure__excursion=tour, departure__date__lt=timezone.localdate(), status='paid').exists()
    return render(request, 'tours/detail.html', {'tour':tour, 'booking_form':BookingForm(excursion=tour),
        'review_form':ReviewForm(), 'can_review':can_review,
        'is_favorite':request.user.is_authenticated and tour.favorites.filter(pk=request.user.pk).exists(),
        'departures':tour.departures.filter(date__gte=timezone.localdate())})

@login_required
def edit(request, pk=None):
    if not request.user.is_guide: raise PermissionDenied
    tour = get_object_or_404(Excursion, pk=pk, guide=request.user) if pk else Excursion(guide=request.user)
    if tour.pk and tour.status == 'pending':
        messages.info(request, 'Дождитесь решения модератора перед редактированием.')
        return redirect('users:dashboard')
    form = ExcursionForm(request.POST or None, request.FILES or None, instance=tour)
    dates = DepartureFormSet(request.POST or None, instance=tour, prefix='dates')
    photos = PhotoFormSet(request.POST or None, request.FILES or None, instance=tour, prefix='photos')
    if request.method == 'POST' and all([form.is_valid(), dates.is_valid(), photos.is_valid()]):
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.status = 'draft'
            obj.moderation_comment = ''
            if request.FILES.get('image'): obj.image = resize_image(form.cleaned_data['image'])
            obj.save()
            form.save_m2m()
            dates.instance = obj
            dates.save()
            photos.instance = obj
            photo_objects = photos.save(commit=False)
            for deleted in photos.deleted_objects: deleted.delete()
            for photo in photo_objects:
                if not photo.pk or 'image' in next((f.changed_data for f in photos.forms if f.instance is photo), []):
                    photo.image = resize_image(photo.image)
                photo.save()
        record(request.user, f'Сохранён черновик: {obj.title}')
        messages.success(request, 'Черновик сохранён. Отправьте его на модерацию из кабинета.')
        return redirect('users:dashboard')
    return render(request, 'tours/edit.html', {'form':form, 'dates':dates, 'photos':photos, 'tour':tour})

@login_required
@require_POST
def submit(request, pk):
    with transaction.atomic():
        tour = get_object_or_404(Excursion.objects.select_for_update(), pk=pk, guide=request.user)
        if not request.user.is_guide: raise PermissionDenied
        if tour.status not in ('draft','revision','rejected'):
            messages.error(request, 'Эта экскурсия уже отправлена или опубликована.')
        elif not (tour.image or tour.asset) or not tour.departures.filter(date__gte=timezone.localdate()).exists():
            messages.error(request, 'Для публикации добавьте фотографию и будущую дату.')
        else:
            tour.status = 'pending'
            tour.moderation_comment = ''
            tour.save(update_fields=['status','moderation_comment'])
            transaction.on_commit(lambda: notify('Новая экскурсия на модерации', f'{tour.title}. Гид: {tour.guide}. Откройте кабинет модератора.'))
            record(request.user, f'Отправлено на модерацию: {tour.title}')
            messages.success(request, 'Экскурсия отправлена на модерацию.')
    return redirect('users:dashboard')

@login_required
def delete(request, pk):
    tour = get_object_or_404(Excursion, pk=pk, guide=request.user)
    if request.method == 'POST':
        if tour.departures.filter(bookings__isnull=False).exists():
            messages.error(request, 'Экскурсию с историей бронирований нельзя удалить.')
        else:
            record(request.user, f'Удалена экскурсия: {tour.title}')
            tour.delete()
            messages.success(request, 'Экскурсия удалена.')
        return redirect('users:dashboard')
    return render(request, 'shared/confirm_delete.html', {'object':tour})

@login_required
@require_POST
def favorite(request, pk):
    tour = get_object_or_404(Excursion, pk=pk, status='approved')
    exists = tour.favorites.filter(pk=request.user.pk).exists()
    if exists: tour.favorites.remove(request.user)
    else: tour.favorites.add(request.user)
    record(request.user, f'{"Удалено из избранного" if exists else "Добавлено в избранное"}: {tour.title}')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'saved':not exists})
    return redirect(tour)

@login_required
@require_POST
def review(request, pk):
    tour = get_object_or_404(Excursion, pk=pk)
    if not request.user.bookings.filter(departure__excursion=tour, departure__date__lt=timezone.localdate(), status='paid').exists():
        raise PermissionDenied
    form = ReviewForm(request.POST)
    if form.is_valid():
        Review.objects.update_or_create(user=request.user, excursion=tour, defaults=form.cleaned_data)
        record(request.user, f'Оставлен отзыв: {tour.title}')
        messages.success(request, 'Спасибо за ваш отзыв!')
    else: messages.error(request, form.errors.as_text())
    return redirect(tour)
