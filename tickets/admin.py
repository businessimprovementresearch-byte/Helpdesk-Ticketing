from django.contrib import admin

from .models import Attachment, Ticket, TicketReply


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("subject", "status", "priority", "source", "division", "assigned_to", "created_at")
    list_filter = ("status", "priority", "source", "division")
    search_fields = ("subject", "nama_perusahaan", "no_sj")
    inlines = [TicketReplyInline]


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "type", "created_at")
    list_filter = ("type",)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("file_name", "reply", "file_size", "uploaded_at")
