from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Ticket

import logging

logger = logging.getLogger(__name__)


def ticket_email_subject(ticket: Ticket) -> str:
    """Subject dengan tag [Ticket #ID] supaya balasan email bisa dicocokkan
    kembali ke tiket yang sama oleh management command fetch_emails."""
    return f"[Ticket #{ticket.id}] {ticket.subject}"


def ticket_detail_url(ticket: Ticket) -> str:
    """URL absolut ke halaman detail tiket, dipakai di tombol CTA email."""
    return settings.SITE_URL.rstrip('/') + reverse('tickets:detail', args=[ticket.pk])


def _render_ticket_email_html(
    *,
    recipient_name: str,
    intro_text: str,
    badge_emoji: str,
    badge_title: str,
    rows: list[dict],
    note_text: str = "",
    button_text: str = "Lihat & Balas Tiket",
    button_url: str = "",
    footer_text: str = "Tim Helpdesk Selectro",
) -> str:
    return render_to_string(
        "emails/ticket_notification.html",
        {
            "recipient_name": recipient_name,
            "intro_text": intro_text,
            "badge_emoji": badge_emoji,
            "badge_title": badge_title,
            "rows": rows,
            "note_text": note_text,
            "button_text": button_text,
            "button_url": button_url,
            "footer_text": footer_text,
        },
    )


def _send(subject: str, message: str, to: list[str], cc: list[str] | None = None, html_message: str = ""):
    """Helper kirim email + auto-CC ke TICKET_NOTIFICATION_CC (kalau ada).

    `message` = versi plain-text (dipakai email client yang gak support
    HTML, dan jadi fallback). `html_message` opsional — kalau diisi, email
    dikirim sebagai multipart (HTML + plain text sekaligus).

    Kegagalan kirim email TIDAK boleh menggagalkan aksi utama (bikin tiket,
    ubah status, dll), makanya exception ditangkap manual di sini — tapi
    tetap dicatat ke console/log (bukan ditelan diam-diam kayak
    fail_silently=True) supaya kelihatan pas debugging.
    """
    to = [e for e in to if e]
    if not to:
        logger.warning("Email notifikasi tiket dilewati: penerima 'to' kosong (subject=%r)", subject)
        return
    cc = [e for e in (cc or []) if e and e not in to]
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        cc=cc or None,
    )
    if html_message:
        email.attach_alternative(html_message, "text/html")
    try:
        email.send(fail_silently=False)
    except Exception:
        logger.exception("Gagal mengirim email notifikasi tiket ke %s (cc=%s, subject=%r)", to, cc, subject)


def send_new_ticket_notification(ticket: Ticket):
    """Kirim email konfirmasi ke pembuat tiket saat tiket baru dibuat, dengan
    CC ke alamat pemantauan (TICKET_NOTIFICATION_CC, mis. surat.selectro@gmail.com)."""
    if not (ticket.created_by and ticket.created_by.email):
        return

    rows = [
        {"label": "No. Referensi", "value": ticket.ticket_code},
        {"label": "Subjek Tiket", "value": ticket.subject},
        {"label": "Customer", "value": f"{ticket.created_by} ({ticket.created_by.email})"},
    ]
    if ticket.nama_perusahaan:
        rows.append({"label": "Nama Perusahaan", "value": ticket.nama_perusahaan})
    if ticket.no_sj:
        rows.append({"label": "No. Surat Jalan", "value": ticket.no_sj})
    if ticket.salesman:
        rows.append({"label": "Salesman", "value": ticket.salesman})
    rows.append({"label": "Prioritas", "value": ticket.get_priority_display()})

    html_message = _render_ticket_email_html(
        recipient_name=str(ticket.created_by),
        intro_text="Tiket baru Anda telah berhasil dibuat. Berikut detailnya:",
        badge_emoji="🔔",
        badge_title="Tiket Baru Dibuat",
        rows=rows,
        note_text="Tiket Anda sedang diproses. Tim kami akan segera meninjau dan merespons dalam waktu 1x24 jam.",
        button_url=ticket_detail_url(ticket),
    )

    _send(
        subject=ticket_email_subject(ticket),
        message=(
            f"Halo {ticket.created_by},\n\n"
            f"Tiket Anda telah berhasil dibuat. Berikut detailnya:\n\n"
            f"No. Referensi: {ticket.ticket_code}\n"
            f"Subjek Tiket: {ticket.subject}\n"
            f"Prioritas: {ticket.get_priority_display()}\n\n"
            f"Tiket Anda sedang diproses. Tim kami akan segera meninjau dan "
            f"merespons tiket Anda dalam waktu 1x24 jam.\n\n"
            f"Lihat & balas tiket: {ticket_detail_url(ticket)}\n\n"
            f"Terima kasih,\nTim Helpdesk Selectro"
        ),
        to=[ticket.created_by.email],
        cc=settings.TICKET_NOTIFICATION_CC,
        html_message=html_message,
    )


def send_status_change_notification(ticket, old_status, changed_by=None):
    """Kirim email ke customer pembuat tiket saat status tiket berubah."""
    if ticket.status == old_status:
        return
    if not (ticket.created_by and ticket.created_by.email):
        return
    # Kalau yang mengubah status adalah si customer sendiri (mis. auto-reopen
    # karena dia reply), tidak perlu kirim email ke dirinya sendiri.
    if changed_by and changed_by.pk == getattr(ticket.created_by, "pk", None):
        return

    rows = [
        {"label": "No. Referensi", "value": ticket.ticket_code},
        {"label": "Subjek Tiket", "value": ticket.subject},
        {"label": "Status Baru", "value": ticket.get_status_display()},
    ]

    html_message = _render_ticket_email_html(
        recipient_name=str(ticket.created_by),
        intro_text=f"Status tiket kamu berubah dari '{old_status}' menjadi '{ticket.get_status_display()}'.",
        badge_emoji="🔄",
        badge_title="Status Tiket Diperbarui",
        rows=rows,
        button_url=ticket_detail_url(ticket),
    )

    _send(
        subject=ticket_email_subject(ticket),
        message=(
            f"Status tiket kamu berubah dari '{old_status}' menjadi "
            f"'{ticket.get_status_display()}'.\n\n"
            f"Lihat & balas tiket: {ticket_detail_url(ticket)}"
        ),
        to=[ticket.created_by.email],
        cc=settings.TICKET_NOTIFICATION_CC,
        html_message=html_message,
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

    rows = [
        {"label": "No. Referensi", "value": ticket.ticket_code},
        {"label": "Subjek Tiket", "value": ticket.subject},
        {"label": "Dari", "value": str(reply.author) if reply.author else "-"},
    ]

    html_message = _render_ticket_email_html(
        recipient_name=str(ticket.created_by) if ticket.created_by else "Admin",
        intro_text="Ada balasan baru pada tiket ini:",
        badge_emoji="💬",
        badge_title="Balasan Baru",
        rows=rows,
        note_text=reply.message,
        button_url=ticket_detail_url(ticket),
    )

    _send(
        subject=ticket_email_subject(ticket),
        message=reply.message + f"\n\nLihat & balas tiket: {ticket_detail_url(ticket)}",
        to=recipients,
        cc=settings.TICKET_NOTIFICATION_CC,
        html_message=html_message,
    )