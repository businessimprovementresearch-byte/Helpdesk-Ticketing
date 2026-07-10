from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.ticket_create, name="create"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("attachments/<int:pk>/download/", views.attachment_download, name="attachment_download"),
    path("users/", views.users_index, name="users"),
    path("divisions/", views.divisions_index, name="divisions"),
    path("reports/", views.reports_index, name="reports"),
]
