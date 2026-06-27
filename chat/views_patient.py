from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from clinics.models import Clinic
from django.db.models import Q

@login_required
def chat_room_list_patient(request):
    if not hasattr(request.user, 'patient'):
        return redirect('login')
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    rooms = []
    for room in chat_rooms:
        other = room.user2 if room.user1 == request.user else room.user1
        unread_count = room.messages.filter(is_read=False).exclude(sender=request.user).count()
        # Presence: consider patient.last_seen within 5 minutes as online
        try:
            is_online = False
            if hasattr(other, 'patient') and other.patient.last_seen:
                from django.utils import timezone
                from datetime import timedelta
                is_online = (timezone.now() - other.patient.last_seen) <= timedelta(minutes=5)
            # attach attribute for template rendering
            other.is_online = is_online
        except Exception:
            other.is_online = False
        rooms.append({'room': room, 'other': other, 'unread_count': unread_count})
    context = {'rooms': rooms, 'patient': request.user.patient}
    return render(request, 'chat/chat_room_list_patient.html', context)

@login_required
def chat_room_view_patient(request, room_id):
    if not hasattr(request.user, 'patient'):
        return redirect('login')
    # Scope to the requester's own rooms: non-members get a 404 (no IDOR,
    # no room-existence leak) instead of access.
    chat_room = get_object_or_404(
        ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
        id=room_id,
    )
    other = chat_room.user2 if chat_room.user1 == request.user else chat_room.user1
    chat_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    messages = chat_room.messages.order_by('timestamp')

    # Presence: consider patient/clinic last_seen within 5 minutes as online
    try:
        is_online = False
        if hasattr(other, 'patient') and other.patient and other.patient.last_seen:
            from django.utils import timezone
            from datetime import timedelta
            is_online = (timezone.now() - other.patient.last_seen) <= timedelta(minutes=5)
        elif hasattr(other, 'clinic') and other.clinic and other.clinic.last_seen:
            from django.utils import timezone
            from datetime import timedelta
            is_online = (timezone.now() - other.clinic.last_seen) <= timedelta(minutes=5)
        other.is_online = is_online
    except Exception:
        other.is_online = False

    context = {'chat_room': chat_room, 'messages': messages, 'patient': request.user.patient, 'other': other}
    return render(request, 'chat/chat_room_patient.html', context)
