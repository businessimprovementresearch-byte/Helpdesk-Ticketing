from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Division
from .emails import send_new_ticket_notification, send_reply_notification
from .forms import AttachmentUploadForm, TicketForm, TicketReplyForm
from .models import Attachment, Ticket, TicketReply

User = get_user_model()


def _visible_tickets_for(user):
    """Customer cuma lihat tiket miliknya sendiri; agent/admin lihat semua."""
    if user.is_customer:
        return Ticket.objects.filter(created_by=user)
    return Ticket.objects.all()


@login_required
def index(request):
    tickets = _visible_tickets_for(request.user)

    status = request.GET.get("status")
    if status:
        tickets = tickets.filter(status=status)

    q = request.GET.get("q")
    if q:
        tickets = tickets.filter(subject__icontains=q)

    return render(request, "tickets/index.html", {
        "tickets": tickets.select_related("division", "assigned_to")[:200],
        "status_choices": Ticket.Status.choices,
        "current_status": status or "",
        "q": q or "",
    })


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.source = Ticket.Source.WEB
            ticket.save()

            TicketReply.objects.create(
                ticket=ticket,
                author=request.user,
                type=TicketReply.Type.PUBLIC_REPLY,
                message=form.cleaned_data["message"],
            )
            send_new_ticket_notification(ticket)
            messages.success(request, "Tiket berhasil dibuat.")
            return redirect("tickets:detail", pk=ticket.pk)
    else:
        form = TicketForm()

    return render(request, "tickets/ticket_form.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.user.is_customer and ticket.created_by_id != request.user.id:
        raise PermissionDenied("Kamu tidak punya akses ke tiket ini.")

    can_use_internal_note = not request.user.is_customer

    if request.method == "POST":
        reply_form = TicketReplyForm(request.POST, can_use_internal_note=can_use_internal_note)
        attachment_form = AttachmentUploadForm(request.POST, request.FILES)
        if reply_form.is_valid() and attachment_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.ticket = ticket
            reply.author = request.user
            if not can_use_internal_note:
                reply.type = TicketReply.Type.PUBLIC_REPLY
            reply.save()

            uploaded_file = attachment_form.cleaned_data.get("file")
            if uploaded_file:
                Attachment.objects.create(
                    reply=reply,
                    file=uploaded_file,
                    file_name=uploaded_file.name,
                    mime_type=getattr(uploaded_file, "content_type", "") or "",
                    file_size=uploaded_file.size,
                )

            send_reply_notification(reply)
            messages.success(request, "Balasan terkirim.")
            return redirect("tickets:detail", pk=ticket.pk)
    else:
        reply_form = TicketReplyForm(can_use_internal_note=can_use_internal_note)
        attachment_form = AttachmentUploadForm()

    replies = ticket.replies.select_related("author").prefetch_related("attachments")
    if request.user.is_customer:
        replies = replies.exclude(type=TicketReply.Type.INTERNAL_NOTE)

    return render(request, "tickets/ticket_detail.html", {
        "ticket": ticket,
        "replies": replies,
        "reply_form": reply_form,
        "attachment_form": attachment_form,
    })


@login_required
def attachment_download(request, pk):
    attachment = get_object_or_404(Attachment, pk=pk)
    ticket = attachment.reply.ticket

    if request.user.is_customer and ticket.created_by_id != request.user.id:
        raise PermissionDenied("Kamu tidak punya akses ke file ini.")
    if request.user.is_customer and attachment.reply.type == TicketReply.Type.INTERNAL_NOTE:
        raise Http404("File tidak ditemukan.")

    # Kalau pakai remote storage (Supabase S3), redirect ke signed URL-nya.
    # Kalau local storage, stream langsung filenya.
    if hasattr(attachment.file, "url") and attachment.file.storage.__class__.__name__ != "FileSystemStorage":
        return redirect(attachment.file.url)

    return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.file_name)


@login_required
def users_index(request):
    if not request.user.is_admin:
        raise PermissionDenied
    return render(request, "tickets/users_index.html", {"users": User.objects.all().order_by("username")})


@login_required
def divisions_index(request):
    return render(request, "tickets/divisions_index.html", {"divisions": Division.objects.all()})


@login_required
def reports_index(request):
    tickets = _visible_tickets_for(request.user)
    summary = {
        "total": tickets.count(),
        "open": tickets.filter(status=Ticket.Status.OPEN).count(),
        "pending": tickets.filter(status=Ticket.Status.PENDING).count(),
        "closed": tickets.filter(status=Ticket.Status.CLOSED).count(),
    }
    return render(request, "tickets/reports_index.html", {"summary": summary})
