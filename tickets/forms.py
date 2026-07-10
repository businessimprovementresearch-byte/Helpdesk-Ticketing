from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Division
from .models import Attachment, Ticket, TicketReply

# Aturan validasi lampiran: maksimal 5 file per balasan, masing-masing maks 10MB
MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_SIZE_MB = 10
MAX_ATTACHMENT_SIZE_BYTES = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024


def validate_attachment_files(files):
    """Validasi list UploadedFile. Raise ValidationError kalau melanggar aturan.
    Dipakai baik di form create tiket maupun di halaman detail tiket."""
    if not files:
        return
    if len(files) > MAX_ATTACHMENTS:
        raise ValidationError(f"Maksimal {MAX_ATTACHMENTS} file lampiran per balasan.")
    for f in files:
        if f.size > MAX_ATTACHMENT_SIZE_BYTES:
            raise ValidationError(
                f"File '{f.name}' terlalu besar ({f.size / 1024 / 1024:.1f}MB). "
                f"Maksimal {MAX_ATTACHMENT_SIZE_MB}MB per file."
            )


class TicketForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"}), label="Deskripsi Awal")

    class Meta:
        model = Ticket
        fields = [
            "subject", "category", "priority", "division",
            "nama_perusahaan", "no_sj", "salesman", "invoice_status",
        ]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "nama_perusahaan": forms.TextInput(attrs={"class": "form-control"}),
            "no_sj": forms.TextInput(attrs={"class": "form-control"}),
            "salesman": forms.TextInput(attrs={"class": "form-control"}),
            "invoice_status": forms.TextInput(attrs={"class": "form-control"}),
            "division": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Divisi wajib dipilih, dan hanya divisi aktif yang muncul di pilihan
        self.fields["division"].queryset = Division.objects.filter(is_active=True)
        self.fields["division"].required = True
        self.fields["division"].empty_label = "-- Pilih Divisi --"

        # Priority cuma boleh diedit admin. Non-admin: field disembunyikan,
        # nilainya dipaksa default Medium lewat clean_priority().
        if not (self.user and getattr(self.user, "is_admin", False)):
            self.fields["priority"].widget = forms.HiddenInput()
            self.fields["priority"].required = False
            self.initial["priority"] = Ticket.Priority.MEDIUM

    def clean_priority(self):
        if not (self.user and getattr(self.user, "is_admin", False)):
            return Ticket.Priority.MEDIUM
        return self.cleaned_data["priority"]


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


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """FileField yang bisa menerima banyak file sekaligus (input `multiple`).
    Berdasarkan resep resmi Django untuk multi-file upload."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput(attrs={"class": "form-control"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)


class AttachmentUploadForm(forms.Form):
    """Menerima banyak file lewat input `files` (attribute multiple di HTML).
    Validasi jumlah & ukuran dilakukan manual di view lewat validate_attachment_files()."""
    files = MultiFileField(required=False)


class TicketStatusForm(forms.ModelForm):
    """Form untuk agent/admin mengubah status, priority, assignment, dan divisi tiket."""

    class Meta:
        model = Ticket
        fields = ["status", "priority", "division", "assigned_to"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "priority": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "division": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "assigned_to": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["division"].queryset = Division.objects.filter(is_active=True)
        self.fields["division"].required = False
        self.fields["assigned_to"].queryset = User.objects.filter(role__in=[User.Role.AGENT, User.Role.ADMIN])
        self.fields["assigned_to"].required = False


class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ["name", "code", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control text-uppercase", "maxlength": 10}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if not code:
            raise ValidationError("Kode divisi wajib diisi (dipakai untuk prefix nomor tiket, mis. OK-001).")
        return code


class UserForm(forms.ModelForm):
    """Dipakai admin untuk membuat/mengedit user. Password diisi terpisah (opsional saat edit)."""

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        help_text="Kosongkan kalau tidak ingin mengubah password.",
    )

    class Meta:
        from accounts.models import User as UserModel
        model = UserModel
        fields = [
            "username", "email", "first_name", "last_name",
            "role", "division", "phone_number", "company", "address", "position", "is_active",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "division": forms.Select(attrs={"class": "form-select"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "company": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "position": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["division"].required = False
        if self.instance and self.instance.pk:
            # Saat edit, password tidak wajib
            self.fields["password"].required = False
        else:
            self.fields["password"].required = True
            self.fields["password"].help_text = "Password awal untuk user ini."

    def save(self, commit=True):
        user = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            user.set_password(raw_password)
        if commit:
            user.save()
        return user
