from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(name="stock_status_pill")
def stock_status_pill(product):
    """Render a product's stock state as the DESIGN.md status-pill shape.

    Mirrors orders/templatetags/status_tags.status_pill, but keys off two new
    stock-specific hues (--color-stock-out-*/--color-stock-low-*) rather than
    the order-status hues, since stock severity and order status are distinct
    semantic systems (DESIGN.md reserves the order hues for order status).
    "En stock" is deliberately left as plain text, not a pill — the absence
    of a badge is itself the signal that a row needs no attention.
    """
    if product.is_out_of_stock():
        return format_html('<span class="status-pill status-pill--stock-out">⚠ Agotado</span>')
    if product.total_stock() < product.low_stock_threshold:
        return format_html('<span class="status-pill status-pill--stock-low">⚠ Stock bajo</span>')
    return "En stock"
