from django import template
from django.utils.html import format_html

from accounts.models import Role

register = template.Library()


@register.filter(name="role_pill")
def role_pill(role, label):
    """Wrap a Role code + its display label in the status-pill markup, mirroring
    orders/templatetags/status_tags.status_pill. Only two visual tiers: DISTRIBUTOR
    (elevated/admin) vs. everyone else — see DESIGN.md role-badge note in styles.css."""
    css_role = "admin" if role == Role.DISTRIBUTOR else "default"
    return format_html(
        '<span class="status-pill status-pill--role-{}">{}</span>',
        css_role,
        label,
    )
