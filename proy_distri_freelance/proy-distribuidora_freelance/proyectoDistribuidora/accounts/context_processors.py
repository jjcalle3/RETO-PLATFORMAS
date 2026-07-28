from orders.cart import Cart


def notifications(request):
    """Unread notification count, available in every template without each
    view having to pass it explicitly (US-16: "visible on every page load").
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    cart_items_count = Cart(request.session).count if hasattr(request, 'session') else 0
    return {
        'unread_notification_count': user.notifications.unread().count(),
        'cart_items_count': cart_items_count,
    }
