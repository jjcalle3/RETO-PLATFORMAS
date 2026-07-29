from django.db import models
from django.utils import timezone

from accounts.models import User
from orders.models import Order
from .managers import DeliveryConfirmationManager


class DeliveryConfirmation(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_confirmation"
    )

    delivery_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    # DR-09: photo proof is no longer the source of truth for delivery —
    # the store owner's confirmation is (see Order.status). This is now just
    # optional metadata the delivery person may leave; never validated.
    photo_public_id = models.CharField(max_length=255, blank=True)

    confirmed_at = models.DateTimeField(default=timezone.now)

    objects = DeliveryConfirmationManager()

    def __str__(self):
        return f"Delivery {self.order} by {self.delivery_user} at {self.confirmed_at}"