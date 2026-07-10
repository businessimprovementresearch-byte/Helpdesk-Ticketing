from django import forms
from django.contrib.auth.forms import AuthenticationForm

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Alamat Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True, "placeholder": "contoh@email.com"}),
    )