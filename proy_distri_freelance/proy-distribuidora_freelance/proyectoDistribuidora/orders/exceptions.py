"""Domain exceptions raised by Order state-machine methods so views can
translate a failed transition into user-facing messages without embedding the
business rule themselves."""


class OrderError(Exception):
    """Base class for order state-machine failures."""


class EmptyOrder(OrderError):
    """Raised when trying to accept an order that has no items."""


class InsufficientStock(OrderError):
    """Raised when one or more items can't be fulfilled from current stock.

    Carries the per-item error strings so the view can surface each one.
    """

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__('; '.join(self.errors))
