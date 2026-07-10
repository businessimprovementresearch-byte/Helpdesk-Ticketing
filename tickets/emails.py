from django.conf import settings
from django.core.mail import send_mail

from .models import Ticket


def ticket_email_subject(ticket: Ticket) -> str:
    """Subject dengan tag [Ticket #ID] supaya balasan email bisa dicocokkan
    kembali ke tiket yang sama oleh management command fetch_emails."""
    return f"[Ticket #{ticket.id}] {ticket.subject}"


def send_new_ticket_notification(ticket: Ticket):
    recipients = [settings.EMAIL_HOST_USER] if settings.EMAIL_HOST_USER else []
    if not recipients:
        return
    send_mail(
        subject=ticket_email_subject(ticket),
        message=(
            f"Tiket baru dibuat oleh {ticket.created_by}.\n\n"
            f"Kategori: {ticket.category}\nPrioritas: {ticket.get_priority_display()}\n\n"
            f"Lihat tiket di dashboard untuk detail."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )


def send_reply_notification(reply):
    """Kirim notifikasi email saat ada balasan public (bukan internal note)."""
    if reply.type != reply.Type.PUBLIC_REPLY:
        return

    ticket = reply.ticket
    # Tentukan penerima: kalau yang balas agent/admin, notif ke customer pembuat
    # tiket; kalau yang balas customer, notif ke inbox support.
    if reply.author and reply.author.is_customer:
        recipients = [settings.EMAIL_HOST_USER] if settings.EMAIL_HOST_USER else []
    else:
        recipients = [ticket.created_by.email] if ticket.created_by and ticket.created_by.email else []

    if not recipients:
        return

    send_mail(
        subject=ticket_email_subject(ticket),
        message=reply.message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )
