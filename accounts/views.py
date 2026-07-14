from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, StyledPasswordChangeForm


@login_required
def settings_profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("accounts:settings_profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/settings_profile.html", {"form": form, "active_tab": "profile"})


@login_required
def settings_password(request):
    if request.method == "POST":
        form = StyledPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # biar user gak ke-logout otomatis
            messages.success(request, "Password berhasil diubah.")
            return redirect("accounts:settings_password")
    else:
        form = StyledPasswordChangeForm(user=request.user)
    return render(request, "accounts/settings_password.html", {"form": form, "active_tab": "password"})