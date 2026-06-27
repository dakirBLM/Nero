from django.test import TestCase
from django.urls import reverse
from django.db.models import Q

from accounts.models import User
from patients.models import Patient
from chat.models import ChatRoom, Message


def _patient(username):
    user = User.objects.create_user(username, f'{username}@example.com', 'pw-test-12345', user_type='patient')
    Patient.objects.create(user=user, full_name=username.title(), gender='M', phone='100')
    return user


class ChatRoomIDORTests(TestCase):
    """Regression tests for the chat-room IDOR fix in mark_messages_as_read."""

    def setUp(self):
        self.alice = _patient('alice')
        self.bob = _patient('bob')
        self.carol = _patient('carol')  # not a member of the room
        self.room = ChatRoom.objects.create(user1=self.alice, user2=self.bob)
        self.msg = Message.objects.create(chat_room=self.room, sender=self.alice, content='hello')
        self.url = reverse('mark_messages_as_read', args=[self.room.id])

    def test_non_member_gets_404_and_cannot_mutate(self):
        self.client.force_login(self.carol)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 404)
        self.msg.refresh_from_db()
        self.assertFalse(self.msg.is_read)  # state untouched by the outsider

    def test_member_can_mark_read(self):
        self.client.force_login(self.bob)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.msg.refresh_from_db()
        self.assertTrue(self.msg.is_read)

    def test_requires_login(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_non_member_cannot_open_routed_room_view(self):
        # The routed patient room view (name 'chat_room_view') must 404 a non-member.
        self.client.force_login(self.carol)
        resp = self.client.get(reverse('chat_room_view', args=[self.room.id]))
        self.assertEqual(resp.status_code, 404)

    def test_member_can_open_routed_room_view(self):
        self.client.force_login(self.bob)
        resp = self.client.get(reverse('chat_room_view', args=[self.room.id]))
        self.assertEqual(resp.status_code, 200)


class StartChatGuardTests(TestCase):
    """start_chat_with_user must not open rooms with non patient/clinic accounts."""

    def test_cannot_open_room_with_staff_account(self):
        alice = _patient('alice2')
        staff = User.objects.create_user('admin2', 'admin2@example.com', 'pw-test-12345',
                                         user_type='patient', is_staff=True)  # no Patient/Clinic row
        self.client.force_login(alice)
        self.client.get(reverse('start_chat_with_user'), {'user_id': staff.id})
        self.assertFalse(
            ChatRoom.objects.filter(
                Q(user1=alice, user2=staff) | Q(user1=staff, user2=alice)
            ).exists()
        )
