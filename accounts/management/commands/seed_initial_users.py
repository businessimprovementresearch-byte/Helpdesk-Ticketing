from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User


ACCOUNTS = [
    {
        "username": "indra",
        "email": "indra@selectro.co.id",
        "first_name": "Indra",
        "password": "Selectro123",
        "role": User.Role.ADMIN,
        "company": "Selectro",
    },
    {
        "username": "levin",
        "email": "marketing3@selectro.co.id",
        "first_name": "Levin",
        "password": "Marketing3",
        "role": User.Role.CUSTOMER,
        "company": "Selectro",
    },
    {
        "username": "tara",
        "email": "marketing2@orientraco.com",
        "first_name": "Tara",
        "password": "Marketing2",
        "role": User.Role.CUSTOMER,
        "company": "Orientraco",
    },
]


class Command(BaseCommand):
    help = "Bikin/update 3 akun awal (Pak Indra - admin, Levin & Tara - customer). Aman dijalankan berkali-kali."

    @transaction.atomic
    def handle(self, *args, **options):
        for data in ACCOUNTS:
            user, created = User.objects.get_or_create(
                email__iexact=data["email"],
                defaults={
                    "username": data["username"],
                    "email": data["email"],
                    "first_name": data["first_name"],
                    "role": data["role"],
                    "company": data["company"],
                    "is_active": True,
                    "is_staff": data["role"] == User.Role.ADMIN,
                    "is_superuser": data["role"] == User.Role.ADMIN,
                },
            )
            user.set_password(data["password"])
            if not created:
                user.username = data["username"]
                user.first_name = data["first_name"]
                user.role = data["role"]
                user.company = data["company"]
                user.is_active = True
                user.is_staff = data["role"] == User.Role.ADMIN
                user.is_superuser = data["role"] == User.Role.ADMIN
            user.save()

            status = "dibuat" if created else "diupdate"
            self.stdout.write(self.style.SUCCESS(f"{data['email']} ({data['role']}) — {status}"))