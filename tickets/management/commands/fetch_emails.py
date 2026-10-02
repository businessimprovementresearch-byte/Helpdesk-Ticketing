import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from accounts.models import User
from tickets.emails import send_reply_notification
from tickets.models import Attachment, Ticket, TicketReply

TICKET_TAG_RE = re.compile(r"\[Ticket #(\d+)\]", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _extract_sender_email(raw_value):
    if not raw_value:
        return ""
    match = EMAIL_RE.search(raw_value)
    if match:
        return match.group(0).strip()
    return str(raw_value).strip()


def _get_or_create_sender_user(raw_from):
    sender_email = _extract_sender_email(raw_from)
    if not sender_email or sender_email == "unknown@unknown.com":
        return None

    sender = User.objects.filter(email__iexact=sender_email).first()
    if sender is not None:
        return sender

    username = sender_email.split("@", 1)[0][:30] or "customer"
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return User.objects.create_user(
        username=username,
        email=sender_email,
        password=get_random_string(24),
    )


class Command(BaseCommand):
    help = "Cek inbox IMAP, ubah email baru jadi tiket (atau balasan tiket yang sudah ada)."

    def handle(self, *args, **options):
        if not settings.IMAP_USERNAME or not settings.IMAP_PASSWORD:
            self.stdout.write(self.style.WARNING(
                "IMAP_USERNAME/IMAP_PASSWORD belum diisi di env, skip fetch_emails."
            ))
            return

        try:
            from imap_tools import AND, MailBox
        except ImportError:
            self.stderr.write(self.style.ERROR("Package imap-tools belum terinstall."))
            return

        created_count = 0
        replied_count = 0

        with MailBox(settings.IMAP_HOST, port=settings.IMAP_PORT).login(
            settings.IMAP_USERNAME, settings.IMAP_PASSWORD, initial_folder=settings.IMAP_FOLDER
        ) as mailbox:
            for msg in mailbox.fetch(AND(seen=False), mark_seen=True):
                subject = msg.subject or "(Tanpa Subject)"
                body = msg.text or msg.html or "(email tanpa isi teks)"
                from_email = _extract_sender_email(msg.from_ or "unknown@unknown.com")
                sender = _get_or_create_sender_user(from_email)

                match = TICKET_TAG_RE.search(subject)
                ticket = None
                if match:
                    ticket = Ticket.objects.filter(pk=int(match.group(1))).first()

                if ticket is None:
                    ticket = Ticket.objects.create(
                        subject=subject,
                        source=Ticket.Source.EMAIL,
                        created_by=sender,
                        email_message_id=msg.uid or "",
                    )
                    created_count += 1
                    self.stdout.write(f"Tiket baru #{ticket.id} dari {from_email}: {subject}")
                else:
                    if ticket.created_by is None and sender is not None:
                        ticket.created_by = sender
                        ticket.save(update_fields=["created_by"])
                    replied_count += 1
                    self.stdout.write(f"Balasan baru untuk tiket #{ticket.id} dari {from_email}")

                reply = TicketReply.objects.create(
                    ticket=ticket,
                    author=sender,
                    type=TicketReply.Type.PUBLIC_REPLY,
                    message=f"(Email dari {from_email})\n\n{body}",
                )

                if reply.type == TicketReply.Type.PUBLIC_REPLY:
                    send_reply_notification(reply)

                for att in msg.attachments:
                    Attachment.objects.create(
                        reply=reply,
                        file=ContentFile(att.payload, name=att.filename),
                        file_name=att.filename,
                        mime_type=att.content_type or "",
                        file_size=len(att.payload),
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Selesai. Tiket baru: {created_count}, balasan masuk: {replied_count}."
        ))
