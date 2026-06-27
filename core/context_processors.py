from django.db.models import Q

def total_unread(request):
    """Provide total unread chat messages for the current user.

    Returns {'total_unread': <int>} to be available in all templates.
    """
    if not request.user or not request.user.is_authenticated:
        return {'total_unread': 0}

    try:
        from chat.models import ChatRoom, Message
        chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
        count = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
        return {'total_unread': count}
    except Exception:
        return {'total_unread': 0}
