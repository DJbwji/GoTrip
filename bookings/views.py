from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from core.services import record, notify
from tours.models import Excursion, Departure
from .models import Booking
from .forms import BookingForm

@login_required
@require_POST
def create(request, pk):
    tour = get_object_or_404(Excursion, pk=pk, status='approved')
    form = BookingForm(request.POST, excursion=tour)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect(tour)
    people = form.cleaned_data['people']
    departure = form.cleaned_data['departure']
    with transaction.atomic():
        updated = Departure.objects.filter(pk=departure.pk, excursion__status='approved',
            capacity__gte=F('reserved') + people, date__gte=timezone.localdate()).update(reserved=F('reserved') + people)
        if not updated:
            messages.error(request, 'Места уже заняты. Выберите другую дату.')
            return redirect(tour)
        booking = Booking.objects.create(user=request.user, departure=departure, people=people, total=tour.price * people)
        record(request.user, f'Бронирование: {tour.title}')
        transaction.on_commit(lambda: notify('Бронирование создано', f'{tour.title}, {departure.date}. Сумма: {booking.total} ₽. Заказ {booking}.', [request.user.email]))
    return redirect('bookings:payment', pk=booking.pk)

@login_required
def payment(request, pk):
    booking = get_object_or_404(Booking.objects.select_related('departure__excursion'), pk=pk, user=request.user)
    if request.method == 'POST':
        if not settings.DEMO_PAYMENTS:
            messages.error(request, 'Платёжный провайдер пока не подключён.')
        elif booking.departure.date < timezone.localdate():
            messages.error(request, 'Дата экскурсии уже прошла.')
        else:
            with transaction.atomic():
                changed = Booking.objects.filter(pk=pk, status='pending').update(status='paid')
                if changed:
                    record(request.user, f'Тестовая оплата бронирования {booking}')
                    transaction.on_commit(lambda: notify('Бронирование подтверждено', f'Заказ {booking} подтверждён в демонстрационном режиме. Деньги не списывались.', [request.user.email]))
                    messages.success(request, 'Тестовая оплата прошла. Бронирование подтверждено.')
            return redirect('users:dashboard')
    return render(request, 'bookings/payment.html', {'booking':booking, 'demo_payments':settings.DEMO_PAYMENTS})

@login_required
@require_POST
def cancel(request, pk):
    with transaction.atomic():
        booking = get_object_or_404(Booking, pk=pk, user=request.user)
        if booking.status == 'paid':
            messages.error(request, 'Оплаченную бронь обрабатывает поддержка. Напишите гиду.')
        elif Booking.objects.filter(pk=pk, status='pending').update(status='cancelled'):
            Departure.objects.filter(pk=booking.departure_id).update(reserved=F('reserved') - booking.people)
            record(request.user, f'Отменено бронирование {booking}')
            messages.success(request, 'Бронирование отменено, места освобождены.')
    return redirect('users:dashboard')
