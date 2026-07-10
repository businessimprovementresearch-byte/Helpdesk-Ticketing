from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.core.paginator import Paginator

@login_required
def dashboard(request):
    visible = _visible_tickets_for(request.user)

    closed_qs = visible.filter(status=Ticket.Status.CLOSED).annotate(
        resolution_time=ExpressionWrapper(F("updated_at") - F("created_at"), output_field=DurationField())
    )
    avg_duration = closed_qs.aggregate(avg=Avg("resolution_time"))["avg"]
    avg_hours = round(avg_duration.total_seconds() / 3600, 1) if avg_duration else 0

    return render(request, "tickets/dashboard.html", {
        "open_count": visible.filter(status=Ticket.Status.OPEN).count(),
        "pending_count": visible.filter(status=Ticket.Status.PENDING).count(),
        "closed_count": visible.filter(status=Ticket.Status.CLOSED).count(),
        "avg_hours": avg_hours,
        "recent_tickets": visible.select_related("created_by")[:5],
    })

from accounts.models import Division
from .emails import (
    send_new_ticket_notification,
    send_reply_notification,
    send_status_change_notification,
)
from .forms import (
    AttachmentUploadForm,
    DivisionForm,
    TicketForm,
    TicketReplyForm,
    TicketStatusForm,
    UserForm,
    validate_attachment_files,
)
from .models import Attachment, Ticket, TicketReply

User = get_user_model()


def _admin_required(user):
    if not user.is_admin:
        raise PermissionDenied("Halaman ini khusus admin.")


def _visible_tickets_for(user):
    """Customer cuma lihat tiket miliknya sendiri; agent/admin lihat semua."""
    if user.is_customer:
        return Ticket.objects.filter(created_by=user)
    return Ticket.objects.all()


@login_required
def index(request):
    tickets = _visible_tickets_for(request.user).select_related("division", "assigned_to")

    status = request.GET.get("status")
    priority = request.GET.get("priority")
    q = request.GET.get("q")

    if status:
        tickets = tickets.filter(status=status)
    if priority:
        tickets = tickets.filter(priority=priority)
    if q:
        tickets = tickets.filter(subject__icontains=q)

    paginator = Paginator(tickets, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "tickets/index.html", {
        "page_obj": page_obj,
        "status_options": [{"value": v, "label": l, "selected": v == (status or "")} for v, l in Ticket.Status.choices],
        "priority_options": [{"value": v, "label": l, "selected": v == (priority or "")} for v, l in Ticket.Priority.choices],
        "current_status": status or "",
        "current_priority": priority or "",
        "q": q or "",
    })


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketForm(request.POST, user=request.user)
        attachment_form = AttachmentUploadForm(request.POST, request.FILES)
        uploaded_files = request.FILES.getlist("files")

        attachment_error = None
        if attachment_form.is_valid():
            try:
                validate_attachment_files(uploaded_files)
            except ValidationError as exc:
                attachment_error = exc.message

        if form.is_valid() and attachment_form.is_valid() and not attachment_error:
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.source = Ticket.Source.WEB
            # Ticket code digenerate otomatis berdasarkan divisi yang dipilih
            ticket.ticket_code = Ticket.generate_ticket_code(division=ticket.division)
            ticket.save()

            reply = TicketReply.objects.create(
                ticket=ticket,
                author=request.user,
                type=TicketReply.Type.PUBLIC_REPLY,
                message=form.cleaned_data["message"],
            )

            for uploaded_file in uploaded_files:
                Attachment.objects.create(
                    reply=reply,
                    file=uploaded_file,
                    file_name=uploaded_file.name,
                    mime_type=getattr(uploaded_file, "content_type", "") or "",
                    file_size=uploaded_file.size,
                )

            send_new_ticket_notification(ticket)
            messages.success(request, f"Tiket {ticket.ticket_code} berhasil dibuat.")
            return redirect("tickets:detail", pk=ticket.pk)
        elif attachment_error:
            messages.error(request, attachment_error)
    else:
        form = TicketForm(user=request.user)
        attachment_form = AttachmentUploadForm()

    return render(request, "tickets/ticket_form.html", {
        "form": form,
        "attachment_form": attachment_form,
    })


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.user.is_customer and ticket.created_by_id != request.user.id:
        raise PermissionDenied("Kamu tidak punya akses ke tiket ini.")

    can_use_internal_note = not request.user.is_customer
    can_manage_status = not request.user.is_customer  # agent & admin

    status_form = TicketStatusForm(instance=ticket) if can_manage_status else None

    if request.method == "POST":
        action = request.POST.get("action", "reply")

        # --- Aksi 1: agent/admin mengubah status/priority/assignment tiket ---
        if action == "update_status" and can_manage_status:
            old_status = ticket.status
            status_form = TicketStatusForm(request.POST, instance=ticket)
            if status_form.is_valid():
                updated_ticket = status_form.save()
                send_status_change_notification(updated_ticket, old_status, changed_by=request.user)
                messages.success(request, "Status tiket diperbarui.")
                return redirect("tickets:detail", pk=ticket.pk)
            else:
                messages.error(request, "Gagal memperbarui status tiket.")

        # --- Aksi 2: kirim balasan (customer atau agent/admin) ---
        else:
            reply_form = TicketReplyForm(request.POST, can_use_internal_note=can_use_internal_note)
            attachment_form = AttachmentUploadForm(request.POST, request.FILES)
            uploaded_files = request.FILES.getlist("files")

            attachment_error = None
            try:
                validate_attachment_files(uploaded_files)
            except ValidationError as exc:
                attachment_error = exc.message

            if reply_form.is_valid() and attachment_form.is_valid() and not attachment_error:
                reply = reply_form.save(commit=False)
                reply.ticket = ticket
                reply.author = request.user
                if not can_use_internal_note:
                    reply.type = TicketReply.Type.PUBLIC_REPLY
                reply.save()

                for uploaded_file in uploaded_files:
                    Attachment.objects.create(
                        reply=reply,
                        file=uploaded_file,
                        file_name=uploaded_file.name,
                        mime_type=getattr(uploaded_file, "content_type", "") or "",
                        file_size=uploaded_file.size,
                    )

                # Auto-reopen: kalau tiket closed dan yang membalas adalah
                # customer pemilik tiket (bukan internal note), buka lagi otomatis.
                if (
                    ticket.status == Ticket.Status.CLOSED
                    and reply.type == TicketReply.Type.PUBLIC_REPLY
                    and request.user.id == ticket.created_by_id
                ):
                    old_status = ticket.status
                    ticket.status = Ticket.Status.OPEN
                    ticket.save(update_fields=["status", "updated_at"])
                    send_status_change_notification(ticket, old_status, changed_by=request.user)
                    messages.info(request, "Tiket dibuka kembali karena ada balasan baru.")

                send_reply_notification(reply)
                messages.success(request, "Balasan terkirim.")
                return redirect("tickets:detail", pk=ticket.pk)
            elif attachment_error:
                messages.error(request, attachment_error)
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
        "status_form": status_form,
        "can_manage_status": can_manage_status,
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


# ---------------------------------------------------------------------------
# Users (full CRUD + bulk delete) — khusus admin
# ---------------------------------------------------------------------------

@login_required
def users_index(request):
    _admin_required(request.user)

    if request.method == "POST" and request.POST.get("action") == "bulk_delete":
        ids = request.POST.getlist("selected_users")
        ids = [i for i in ids if str(i) != str(request.user.pk)]  # gak boleh hapus diri sendiri
        deleted_count, _ = User.objects.filter(pk__in=ids).delete()
        messages.success(request, f"{deleted_count} user berhasil dihapus.")
        return redirect("tickets:users")

    return render(request, "tickets/users_index.html", {
        "users": User.objects.all().select_related("division").order_by("username"),
    })


@login_required
def user_create(request):
    _admin_required(request.user)
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User baru berhasil dibuat.")
            return redirect("tickets:users")
    else:
        form = UserForm()
    return render(request, "tickets/user_form.html", {"form": form, "is_new": True})


@login_required
def user_edit(request, pk):
    _admin_required(request.user)
    target_user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, "User berhasil diperbarui.")
            return redirect("tickets:users")
    else:
        form = UserForm(instance=target_user)
    return render(request, "tickets/user_form.html", {"form": form, "is_new": False, "target_user": target_user})


@login_required
def user_delete(request, pk):
    _admin_required(request.user)
    target_user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if target_user.pk == request.user.pk:
            messages.error(request, "Kamu tidak bisa menghapus akunmu sendiri.")
        else:
            target_user.delete()
            messages.success(request, "User berhasil dihapus.")
    return redirect("tickets:users")


# ---------------------------------------------------------------------------
# Divisions (full CRUD)
# ---------------------------------------------------------------------------

@login_required
def divisions_index(request):
    return render(request, "tickets/divisions_index.html", {"divisions": Division.objects.all()})


@login_required
def division_create(request):
    _admin_required(request.user)
    if request.method == "POST":
        form = DivisionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Divisi baru berhasil dibuat.")
            return redirect("tickets:divisions")
    else:
        form = DivisionForm()
    return render(request, "tickets/division_form.html", {"form": form, "is_new": True})


@login_required
def division_edit(request, pk):
    _admin_required(request.user)
    division = get_object_or_404(Division, pk=pk)
    if request.method == "POST":
        form = DivisionForm(request.POST, instance=division)
        if form.is_valid():
            form.save()
            messages.success(request, "Divisi berhasil diperbarui.")
            return redirect("tickets:divisions")
    else:
        form = DivisionForm(instance=division)
    return render(request, "tickets/division_form.html", {"form": form, "is_new": False, "division": division})


@login_required
def division_toggle_active(request, pk):
    _admin_required(request.user)
    division = get_object_or_404(Division, pk=pk)
    if request.method == "POST":
        division.is_active = not division.is_active
        division.save(update_fields=["is_active"])
        messages.success(
            request,
            f"Divisi {division.name} sekarang {'aktif' if division.is_active else 'nonaktif'}.",
        )
    return redirect("tickets:divisions")


# ---------------------------------------------------------------------------
# Reports (+ export Excel)
# ---------------------------------------------------------------------------

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


@login_required
def reports_export_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    tickets = _visible_tickets_for(request.user).select_related(
        "division", "assigned_to", "created_by"
    ).order_by("-created_at")

    wb = Workbook()
    ws = wb.active
    ws.title = "Tickets"

    headers = [
        "Ticket Code", "Subject", "Status", "Priority", "Source", "Division",
        "Dibuat Oleh", "Ditugaskan Ke", "Nama Perusahaan", "No. SJ", "Salesman",
        "Invoice Status", "Dibuat Pada", "Diperbarui Pada",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for t in tickets:
        ws.append([
            t.ticket_code,
            t.subject,
            t.get_status_display(),
            t.get_priority_display(),
            t.get_source_display(),
            str(t.division) if t.division else "",
            str(t.created_by) if t.created_by else "",
            str(t.assigned_to) if t.assigned_to else "",
            t.nama_perusahaan,
            t.no_sj,
            t.salesman,
            t.invoice_status,
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
            t.updated_at.strftime("%Y-%m-%d %H:%M") if t.updated_at else "",
        ])

    for i, column_cells in enumerate(ws.columns, start=1):
        max_length = max((len(str(c.value)) for c in column_cells if c.value), default=10)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="tickets_export.xlsx"'
    wb.save(response)
    return response
