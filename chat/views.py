
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from patients.models import Patient
from clinics.models import Clinic
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST

# AJAX endpoint to mark all unread messages in a chat room as read for the current user
@login_required
@require_POST
def mark_messages_as_read(request, room_id):
    # Scope to rooms the requester is a member of: prevents IDOR / room-existence
    # enumeration (a non-member gets a 404, not access to another room's state).
    chat_room = get_object_or_404(
        ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
        id=room_id,
    )
    # Only mark messages not sent by the current user
    updated = chat_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return JsonResponse({'status': 'ok', 'marked_count': updated})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from patients.models import Patient
from clinics.models import Clinic
from django.http import JsonResponse
from django.db.models import Q


@login_required
def start_chat_with_clinic(request):
    clinic_id = request.GET.get('clinic_id')
    if not clinic_id or not hasattr(request.user, 'patient'):
        return redirect('chat_room_list')
    clinic = get_object_or_404(Clinic, id=clinic_id)
    patient_user = request.user
    clinic_user = clinic.user
   
    chat_room = ChatRoom.objects.filter(
        Q(user1=patient_user, user2=clinic_user) | Q(user1=clinic_user, user2=patient_user)
    ).first()
    if not chat_room:
        # ensure consistent ordering when creating (optional)
        chat_room = ChatRoom.objects.create(user1=patient_user, user2=clinic_user)
    return redirect(reverse('chat_room_view', args=[chat_room.id]))


@login_required
def start_chat_with_user(request):
    """Start a chat between the current user and another user identified by query param `user_id`.
    This is used by clinics to start chats with patients (and can be reused elsewhere).
    """
    user_id = request.GET.get('user_id')
    if not user_id:
        return redirect('chat_room_list')
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('chat_room_list')

    if other_user == request.user:
        return redirect('chat_room_list')

    # Only allow opening rooms with patient/clinic accounts — never with staff,
    # superusers, or role-less accounts.
    if not (hasattr(other_user, 'patient') or hasattr(other_user, 'clinic')):
        return redirect('chat_room_list')

    chat_room = ChatRoom.objects.filter(
        Q(user1=request.user, user2=other_user) | Q(user1=other_user, user2=request.user)
    ).first()
    if not chat_room:
        # Keep patient-patient rooms open by default; patient-clinic stays blocked by default.
        is_patient_to_patient = hasattr(request.user, 'patient') and hasattr(other_user, 'patient')
        chat_room = ChatRoom.objects.create(
            user1=request.user,
            user2=other_user,
            is_messaging_blocked=not is_patient_to_patient,
        )
    return redirect(reverse('chat_room_view', args=[chat_room.id]))

@login_required
def chat_room_list(request):
    from django.db.models import Q
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    rooms = []
    for room in chat_rooms:
        # compute unread messages for this user (messages sent by other user and not yet read)
        unread_count = room.messages.filter(is_read=False).exclude(sender=request.user).count()
        other = room.user2 if room.user1 == request.user else room.user1
        # Presence: mark patient users as online if last_seen within 5 minutes
        try:
            is_online = False
            from django.utils import timezone
            from datetime import timedelta
            if hasattr(other, 'patient') and getattr(other, 'patient') and other.patient.last_seen:
                is_online = (timezone.now() - other.patient.last_seen) <= timedelta(minutes=5)
            elif hasattr(other, 'clinic') and getattr(other, 'clinic') and other.clinic.last_seen:
                is_online = (timezone.now() - other.clinic.last_seen) <= timedelta(minutes=5)
            other.is_online = is_online
        except Exception:
            other.is_online = False
        rooms.append({'room': room, 'other': other, 'unread_count': unread_count})
    context = {'rooms': rooms}
    # Add patient or clinic context for sidebar/header
    if hasattr(request.user, 'patient'):
        context['patient'] = request.user.patient
    if hasattr(request.user, 'clinic'):
        context['clinic'] = request.user.clinic
    return render(request, 'chat/chat_room_list.html', context)

@login_required
def chat_room_view(request, room_id):
    # Scope to the requester's own rooms (defense-in-depth against IDOR).
    chat_room = get_object_or_404(
        ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
        id=room_id,
    )
    # mark unread messages (sent by other user) as read when opening the room
    chat_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    messages = chat_room.messages.order_by('timestamp')

    other = chat_room.user2 if chat_room.user1 == request.user else chat_room.user1
    try:
        is_online = False
        from django.utils import timezone
        from datetime import timedelta
        if hasattr(other, 'patient') and getattr(other, 'patient') and other.patient.last_seen:
            is_online = (timezone.now() - other.patient.last_seen) <= timedelta(minutes=5)
        elif hasattr(other, 'clinic') and getattr(other, 'clinic') and other.clinic.last_seen:
            is_online = (timezone.now() - other.clinic.last_seen) <= timedelta(minutes=5)
        other.is_online = is_online
    except Exception:
        other.is_online = False
    context = {'chat_room': chat_room, 'messages': messages, 'other': other}
    # Add patient or clinic context for sidebar/header
    if hasattr(request.user, 'patient'):
        context['patient'] = request.user.patient
    if hasattr(request.user, 'clinic'):
        context['clinic'] = request.user.clinic
    return render(request, 'chat/chat_room.html', context)

@login_required
def send_message(request, room_id):
    if request.method == 'POST':
        chat_room = get_object_or_404(ChatRoom, id=room_id)
        if request.user not in (chat_room.user1, chat_room.user2):
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        if chat_room.is_messaging_blocked_effective:
            return JsonResponse(
                {
                    'status': 'blocked',
                    'message': 'Messaging is available only when there is a payed appointment between patient and clinic. If you want to ask questions, please contact info@nero.com.'
                },
                status=403
            )
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                chat_room=chat_room,
                sender=request.user,
                content=content
            )
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'})
