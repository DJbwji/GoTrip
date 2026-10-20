from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from users.models import User
from .models import Conversation
from .forms import MessageForm

@login_required
def inbox(request):
    chats = Conversation.objects.filter(Q(tourist=request.user)|Q(guide=request.user)).select_related('tourist','guide')
    return render(request, 'messaging/inbox.html', {'chats':chats})

@login_required
@require_POST
def start(request, pk):
    guide = get_object_or_404(User, pk=pk, guide_application__status='approved')
    if guide == request.user: return redirect('messaging:inbox')
    chat, _ = Conversation.objects.get_or_create(tourist=request.user, guide=guide)
    return redirect('messaging:chat', pk=chat.pk)

@login_required
def chat(request, pk):
    obj = get_object_or_404(Conversation.objects.select_related('tourist','guide'), pk=pk)
    if request.user.pk not in (obj.tourist_id, obj.guide_id): raise PermissionDenied
    form = MessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        message = form.save(commit=False)
        message.sender = request.user
        message.conversation = obj
        message.save()
        return redirect('messaging:chat', pk=pk)
    return render(request, 'messaging/chat.html', {'chat':obj, 'chat_messages':obj.messages.select_related('sender'), 'form':form})
