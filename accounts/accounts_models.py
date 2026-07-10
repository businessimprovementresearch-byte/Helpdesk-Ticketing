from django.contrib.auth.models import AbstractUser
from django.db import models, transaction


class Division(models.Model):
    """Divisi/departemen di perusahaan (mis. Finance, Operations, IT)."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def generate_next_ticket_code(self):
        """Format: {CODE}-{urut} contoh OK-001, OK-002. Thread-safe pakai row lock."""
        from tickets.models import Ticket

        with transaction.atomic():
            division = Division.objects.select_for_update().get(pk=self.pk)
            last_ticket = (
                Ticket.objects.select_for_update()
                .filter(division=division, ticket_code__startswith=f"{division.code}-")
                .order_by("-ticket_code")
                .first()
            )
            next_number = 1
            if last_ticket and "-" in last_ticket.ticket_code:
                try:
                    next_number = int(last_ticket.ticket_code.rsplit("-", 1)[-1]) + 1
                except ValueError:
                    pass
            return f"{division.code}-{next_number:03d}"


class User(AbstractUser):
    """Custom user model. Menambahkan role & divisi di atas Django's AbstractUser."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        AGENT = "agent", "Agent"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    division = models.ForeignKey(
        Division, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    phone_number = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    position = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_agent(self):
        return self.role == self.Role.AGENT

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER
