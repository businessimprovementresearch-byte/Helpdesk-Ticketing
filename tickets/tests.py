from django.core import mail
from django.test import TestCase, override_settings

from accounts.models import User
from tickets.emails import send_reply_notification
from tickets.management.commands.fetch_emails import _get_or_create_sender_user
from tickets.models import Ticket, TicketReply


class EmailNotificationTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="support@resend.dev",
        EMAIL_HOST_USER="",
    )
    def test_customer_reply_notification_uses_default_from_email_as_support_recipient(self):
        customer = User.objects.create_user(
            username="customer-user",
            email="customer@example.com",
            password="StrongPass123!",
        )
        ticket = Ticket.objects.create(
            subject="Test ticket",
            ticket_code="GN-001",
            created_by=customer,
            source=Ticket.Source.WEB,
        )
        reply = TicketReply.objects.create(
            ticket=ticket,
            author=customer,
            type=TicketReply.Type.PUBLIC_REPLY,
            message="Customer reply",
        )

        mail.outbox.clear()
        send_reply_notification(reply)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("support@resend.dev", mail.outbox[0].to)

    def test_fetch_emails_assigns_created_by_using_sender_email(self):
        customer_email = "customer@example.com"

        sender = _get_or_create_sender_user(f"Customer Name <{customer_email}>")

        self.assertIsNotNone(sender)
        self.assertEqual(sender.email, customer_email)
        self.assertTrue(User.objects.filter(email__iexact=customer_email).exists())
