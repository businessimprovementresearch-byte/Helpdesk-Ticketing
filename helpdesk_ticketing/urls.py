"""
URL configuration for helpdesk_ticketing project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from accounts.forms import EmailAuthenticationForm
from tickets.views import fetch_emails_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='tickets:dashboard', permanent=False)),
    path('tickets/', include('tickets.urls')),
    path('cron/fetch-emails/', fetch_emails_webhook, name='cron_fetch_emails'),
    # Login, logout, password reset (pakai template di templates/registration/)
    path('accounts/login/', auth_views.LoginView.as_view(authentication_form=EmailAuthenticationForm), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
]