"""Domain exceptions for the deliveries app."""


class DeliveryAlreadyConfirmed(Exception):
    """Raised when a second delivery person races to confirm an order that was
    already confirmed (the DeliveryConfirmation OneToOne uniqueness guard)."""
