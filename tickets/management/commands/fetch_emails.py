import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from tickets.models import Attachment, Ticket, TicketReply

TICKET_TAG_RE = re.compile(r"\[Ticket #(\d+)\]", re.IGNORECASE)


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
                from_email = msg.from_ or "unknown@unknown.com"

                match = TICKET_TAG_RE.search(subject)
                ticket = None
                if match:
                    ticket = Ticket.objects.filter(pk=int(match.group(1))).first()

                if ticket is None:
                    ticket = Ticket.objects.create(
                        subject=subject,
                        source=Ticket.Source.EMAIL,
                        email_message_id=msg.uid or "",
                    )
                    created_count += 1
                    self.stdout.write(f"Tiket baru #{ticket.id} dari {from_email}: {subject}")
                else:
                    replied_count += 1
                    self.stdout.write(f"Balasan baru untuk tiket #{ticket.id} dari {from_email}")

                reply = TicketReply.objects.create(
                    ticket=ticket,
                    author=None,
                    type=TicketReply.Type.PUBLIC_REPLY,
                    message=f"(Email dari {from_email})\n\n{body}",
                )

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
