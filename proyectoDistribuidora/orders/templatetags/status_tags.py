from django import template
from django.utils.html import format_html

from orders.models import OrderStatus

register = template.Library()

# DESIGN.md "Sort/priority": needs-action states sort above informational
# ones. Kept here (not in orders/views.py) so every table using status_pill
# derives its sort key from the same source as its display label.
NEEDS_ACTION_STATUSES = {OrderStatus.PENDING, OrderStatus.DELIVERY_ISSUE}


@register.filter(name="status_pill")
def status_pill(status, label):
    """Wrap a status code + its display label in the DESIGN.md status-pill markup."""
    css_status = (status or "").lower()
    return format_html(
        '<span class="status-pill status-pill--{}">{}</span>',
        css_status,
        label,
    )


@register.filter(name="status_priority")
def status_priority(status):
    """0 for needs-action statuses, 1 for informational — DataTables sort key."""
    return 0 if status in NEEDS_ACTION_STATUSES else 1


@register.filter(name="status_pill_for_code")
def status_pill_for_code(code):
    """Same status-pill markup as status_pill, but derives the Spanish label
    from a raw status code string. AuditLog.previous_status/new_status are
    plain CharFields (snapshots of Order.status at transition time), not a
    choices field, so there's no get_status_display() to call — this is the
    equivalent for that case."""
    if not code:
        return "—"
    try:
        label = OrderStatus(code).label
    except ValueError:
        label = code
    return status_pill(code, label)


# Happy-path lifecycle for the order-detail stepper (partials/order_stepper.html).
ORDER_STEP_LABELS = [
    (OrderStatus.PENDING, "Pendiente"),
    (OrderStatus.ACCEPTED, "Aceptado"),
    (OrderStatus.DISPATCHED, "Despachado"),
    (OrderStatus.DELIVERED, "Entregado"),
    (OrderStatus.CONFIRMED, "Confirmado"),
]


@register.simple_tag(name="order_steps")
def order_steps(status):
    """Return the lifecycle steps for the order stepper as [{label, state, n}].

    Happy path: Pendiente → Aceptado → Despachado → Entregado → Confirmado.
    Two branches off it:
      - REJECTED collapses to a single terminal 'rejected' node (the order died
        while pending); the remaining nodes render as inert 'upcoming'.
      - DELIVERY_ISSUE keeps the first four steps done and marks the final
        Confirmado node as 'error' (incidencia reported, awaiting resolution).
    """
    labels = [label for _, label in ORDER_STEP_LABELS]
    sequence = [code for code, _ in ORDER_STEP_LABELS]

    def build(state_for):
        return [{"label": labels[i], "state": state_for(i), "n": i + 1} for i in range(len(labels))]

    if status == OrderStatus.REJECTED:
        steps = build(lambda i: "upcoming")
        steps[0] = {"label": "Rechazado", "state": "rejected", "n": 1}
        return steps

    if status == OrderStatus.DELIVERY_ISSUE:
        return build(lambda i: "done" if i < 4 else "error")

    current = sequence.index(status) if status in sequence else 0
    terminal = status == OrderStatus.CONFIRMED
    return build(
        lambda i: "done" if i < current or (terminal and i == current)
        else ("active" if i == current else "upcoming")
    )
