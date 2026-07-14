from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Alamat Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True, "placeholder": "contoh@email.com"}),
    )

class ProfileForm(forms.ModelForm):
    """Form untuk user mengubah nama & email sendiri di halaman Pengaturan."""

    name = forms.CharField(label="Nama", widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = get_user_model()
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].initial = self.instance.get_full_name() or self.instance.username
        self.order_fields(["name", "email"])

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        user.first_name = first_name
        user.last_name = last_name
        if commit:
            user.save()
        return user


class StyledPasswordChangeForm(PasswordChangeForm):
    """PasswordChangeForm bawaan Django, cuma diganti label & styling-nya
    biar sesuai desain (Password Saat Ini / Password Baru / Konfirmasi Password)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Password Saat Ini"
        self.fields["old_password"].widget.attrs.update({"class": "form-control"})
        self.fields["new_password1"].label = "Password Baru"
        self.fields["new_password1"].widget.attrs.update({"class": "form-control"})
        self.fields["new_password1"].help_text = None
        self.fields["new_password2"].label = "Konfirmasi Password"
        self.fields["new_password2"].widget.attrs.update({"class": "form-control"})