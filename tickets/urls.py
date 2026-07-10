from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.ticket_create, name="create"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("attachments/<int:pk>/download/", views.attachment_download, name="attachment_download"),

    # Users (admin only)
    path("users/", views.users_index, name="users"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),

    # Divisions
    path("divisions/", views.divisions_index, name="divisions"),
    path("divisions/create/", views.division_create, name="division_create"),
    path("divisions/<int:pk>/edit/", views.division_edit, name="division_edit"),
    path("divisions/<int:pk>/toggle/", views.division_toggle_active, name="division_toggle"),

    # Reports
    path("reports/", views.reports_index, name="reports"),
    path("reports/export/excel/", views.reports_export_excel, name="reports_export_excel"),
]
