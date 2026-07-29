from django import template
from django.utils.html import format_html_join

register = template.Library()


def _humanize_key(key):
    return str(key).replace("_", " ").capitalize()


def _format_value(value):
    if value in (None, ""):
        return "—"
    if isinstance(value, dict):
        return ", ".join(f"{_humanize_key(k)}: {_format_value(v)}" for k, v in value.items())
    if isinstance(value, list):
        if not value:
            return "—"
        return "; ".join(_format_value(item) for item in value)
    return str(value)


@register.filter(name="format_audit_details")
def format_audit_details(details):
    """Render AuditLog.details (a free-form JSONField) as a readable key/value
    list instead of Python's raw dict repr (single-quoted, brace-wrapped —
    what {{ log.details }} produces by default). Keys come from ~16 different
    AuditLog.objects.create() call sites across the codebase with no shared
    vocabulary, so they're humanized (snake_case -> "Snake case") rather than
    translated to Spanish, which would need a maintained glossary."""
    if not details:
        return "—"
    return format_html_join(
        "",
        '<div class="audit-details__row"><span class="audit-details__key">{}</span>'
        '<span class="audit-details__value">{}</span></div>',
        ((_humanize_key(k), _format_value(v)) for k, v in details.items()),
    )
