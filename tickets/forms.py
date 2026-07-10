from django import forms

from .models import Attachment, Ticket, TicketReply


class TicketForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), label="Deskripsi Awal")

    class Meta:
        model = Ticket
        fields = [
            "subject", "category", "priority", "division",
            "nama_perusahaan", "no_sj", "salesman", "invoice_status",
        ]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
        }


class TicketReplyForm(forms.ModelForm):
    class Meta:
        model = TicketReply
        fields = ["message", "type"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }

    def __init__(self, *args, can_use_internal_note=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_use_internal_note:
            # Customer tidak boleh membuat internal note, jadi field-nya disembunyikan
            self.fields["type"].widget = forms.HiddenInput()
            self.initial["type"] = TicketReply.Type.PUBLIC_REPLY


class AttachmentUploadForm(forms.Form):
    file = forms.FileField(required=False)
