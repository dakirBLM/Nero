
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from patients.models import Patient
from clinics.models import Clinic
from django.db.models import Q
from django.http import JsonResponse

@login_required
def start_chat_with_patient_clinic(request):
    """Start a chat between the current clinic and a patient (from clinic side)."""
    patient_id = request.GET.get('patient_id')
    if not patient_id or not hasattr(request.user, 'clinic'):
        return redirect('chat_room_list_clinic')
    try:
        patient = Patient.objects.get(id=patient_id)
        other_user = patient.user
    except (Patient.DoesNotExist, User.DoesNotExist, AttributeError):
        return redirect('chat_room_list_clinic')
    if other_user == request.user:
        return redirect('chat_room_list_clinic')
    chat_room = ChatRoom.objects.filter(
        Q(user1=request.user, user2=other_user) | Q(user1=other_user, user2=request.user)
    ).first()
    if not chat_room:
        chat_room = ChatRoom.objects.create(user1=request.user, user2=other_user)
    return redirect(reverse('chat_room_view_clinic', args=[chat_room.id]))

@login_required
def start_chat_with_clinic_as_clinic(request, clinic_id):
    """Start a chat between the current clinic and another clinic."""
    if not hasattr(request.user, 'clinic'):
        return redirect('chat_room_list_clinic')
    try:
        other_clinic = Clinic.objects.get(id=clinic_id)
        other_user = other_clinic.user
    except (Clinic.DoesNotExist, User.DoesNotExist, AttributeError):
        return redirect('chat_room_list_clinic')
    if other_user == request.user:
        return redirect('chat_room_list_clinic')
    chat_room = ChatRoom.objects.filter(
        Q(user1=request.user, user2=other_user) | Q(user1=other_user, user2=request.user)
    ).first()
    if not chat_room:
        chat_room = ChatRoom.objects.create(user1=request.user, user2=other_user)
    return redirect(reverse('chat_room_view_clinic', args=[chat_room.id]))

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from patients.models import Patient
from django.db.models import Q

@login_required
def chat_room_list_clinic(request):
    if not hasattr(request.user, 'clinic'):
        return redirect('login')
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    rooms = []
    for room in chat_rooms:
        other = room.user2 if room.user1 == request.user else room.user1
        # Show rooms where the other user is either a patient or a clinic
        if hasattr(other, 'patient') or hasattr(other, 'clinic'):
            unread_count = room.messages.filter(is_read=False).exclude(sender=request.user).count()
            # Calculate online status
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
    context = {
        'rooms': rooms,
        'clinic': request.user.clinic,
    }
    return render(request, 'chat/chat_room_list_clinic.html', context)

@login_required
def chat_room_view_clinic(request, room_id):
    if not hasattr(request.user, 'clinic'):
        return redirect('login')
    # Scope to the requester's own rooms: non-members get a 404 (no IDOR,
    # no room-existence leak) instead of access.
    chat_room = get_object_or_404(
        ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
        id=room_id,
    )
    other = chat_room.user2 if chat_room.user1 == request.user else chat_room.user1
    # Allow chat with both patients and clinics
    if not (hasattr(other, 'patient') or hasattr(other, 'clinic')):
        return redirect('chat_room_list_clinic')
    chat_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    messages = chat_room.messages.order_by('timestamp')
    # Calculate online status
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
    context = {'chat_room': chat_room, 'messages': messages, 'clinic': request.user.clinic, 'other': other}
    return render(request, 'chat/chat_room_clinic.html', context)


@login_required
def unread_count_clinic(request):
    """Return JSON with total unread messages for clinic user."""
    if not hasattr(request.user, 'clinic'):
        return JsonResponse({'unread': 0})
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
    return JsonResponse({'unread': total_unread})
