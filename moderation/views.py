from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from core.services import record, notify
from tours.models import Excursion
from users.models import GuideApplication
from .models import Complaint
from .forms import ComplaintForm, DecisionForm

staff_required = user_passes_test(lambda u: u.is_active and u.is_staff)

@staff_required
def queue(request):
    return render(request, 'moderation/queue.html', {'excursions':Excursion.objects.filter(status='pending').select_related('guide','destination'),
        'applications':GuideApplication.objects.filter(status='pending').select_related('user'),
        'complaints':Complaint.objects.filter(status='pending').select_related('user','excursion')})

@staff_required
def decision(request, kind, pk):
    model = {'excursion':Excursion, 'guide':GuideApplication, 'complaint':Complaint}.get(kind)
    if not model: return redirect('moderation:queue')
    obj = get_object_or_404(model, pk=pk)
    form = DecisionForm(request.POST or None, complaint=kind == 'complaint')
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            obj = model.objects.select_for_update().get(pk=pk)
            if obj.status != 'pending':
                messages.error(request, 'Заявка уже обработана.')
                return redirect('moderation:queue')
            obj.status = form.cleaned_data['status']
            field = 'moderation_comment' if kind == 'excursion' else 'comment'
            setattr(obj, field, form.cleaned_data['comment'])
            obj.save()
            owner = obj.guide if kind == 'excursion' else obj.user
            record(owner, f'Решение модератора: {obj.get_status_display()} — {obj}')
            record(request.user, f'Обработана заявка: {obj}')
            transaction.on_commit(lambda: notify('Решение по заявке', f'{obj.get_status_display()}. {getattr(obj, field)}', [owner.email]))
        messages.success(request, 'Решение сохранено.')
        return redirect('moderation:queue')
    return render(request, 'moderation/decision.html', {'object':obj, 'kind':kind, 'form':form})

@login_required
def complain(request, pk):
    tour = get_object_or_404(Excursion, pk=pk)
    if not request.user.bookings.filter(departure__excursion=tour, status='paid', departure__date__lt=timezone.localdate()).exists():
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    form = ComplaintForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.excursion = tour
        obj.save()
        record(request.user, f'Отправлена жалоба: {tour.title}')
        notify('Новая жалоба', f'Жалоба №{obj.pk} на экскурсию «{tour.title}». Откройте кабинет модератора.')
        messages.success(request, 'Жалоба отправлена. Ответ появится в личном кабинете.')
        return redirect('users:dashboard')
    return render(request, 'shared/form.html', {'form':form, 'title':'Сообщить о проблеме', 'eyebrow':tour.title, 'button':'Отправить жалобу'})
