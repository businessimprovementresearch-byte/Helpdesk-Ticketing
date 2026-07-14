from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("settings/profile/", views.settings_profile, name="settings_profile"),
    path("settings/password/", views.settings_password, name="settings_password"),
]