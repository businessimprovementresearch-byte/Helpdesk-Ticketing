from django import template
register = template.Library()

PRIORITY_ID = {"low": "Rendah", "medium": "Sedang", "high": "Tinggi"}
STATUS_ID = {"open": "Terbuka", "pending": "Pending", "closed": "Selesai"}
STATUS_BADGE = {"open": "primary", "pending": "warning", "closed": "success"}

@register.filter
def priority_id(value):
    return PRIORITY_ID.get(value, value)

@register.filter
def status_id(value):
    return STATUS_ID.get(value, value)

@register.filter
def status_badge(value):
    return STATUS_BADGE.get(value, "secondary")

@register.filter
def initials(user):
    if not user:
        return "?"
    name = user.get_full_name() or user.username
    return name[:2].upper() if name else "?"

ROLE_LABEL = {"admin": "Admin", "agent": "Operator", "customer": "User"}
ROLE_BADGE = {"admin": "danger", "agent": "primary", "customer": "secondary"}

@register.filter
def role_label(value):
    return ROLE_LABEL.get(value, value)

@register.filter
def role_badge(value):
    return ROLE_BADGE.get(value, "secondary")