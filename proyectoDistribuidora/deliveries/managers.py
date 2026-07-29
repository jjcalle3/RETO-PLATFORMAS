"""Custom manager/queryset for the deliveries app.

Holds the delivery-history query and the atomic delivery-confirmation
transition (previously inlined in deliveries/views.py).
"""
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.db.models.manager import Manager


class DeliveryConfirmationQuerySet(QuerySet):
    def recent_for_distributor(self, distributor, limit=20):
        return (
            self.filter(order__store__distributor=distributor)
            .select_related('order__store', 'order__vendor', 'delivery_user')
            .order_by('-confirmed_at')[:limit]
        )


class DeliveryConfirmationManager(Manager.from_queryset(DeliveryConfirmationQuerySet)):
    def confirm(self, order_id, distributor, actor):
        """Atomically confirm a delivery: lock the DISPATCHED order, create the
        confirmation, transition it to DELIVERED, audit, and notify the store
        owner. Returns the created confirmation.

        Raises Order.DoesNotExist if `order_id` isn't a DISPATCHED order for
        this distributor (the `status=DISPATCHED` filter IS the status guard),
        or DeliveryAlreadyConfirmed on the OneToOne race.
        """
        from accounts.models import Notification
        from audit.models import AuditLog
        from orders.models import Order, OrderStatus
        from .exceptions import DeliveryAlreadyConfirmed

        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(store__distributor=distributor, status=OrderStatus.DISPATCHED)
                .get(pk=order_id)
            )
            try:
                confirmacion = self.create(order=order, delivery_user=actor)
            except IntegrityError:
                # Lost the race — another delivery person confirmed first.
                raise DeliveryAlreadyConfirmed(
                    'Este pedido ya fue confirmado por otro repartidor.'
                )
            order.status = OrderStatus.DELIVERED
            order.save(update_fields=['status', 'updated_at'])
            AuditLog.objects.create(
                user=actor,
                action='order_delivered',
                entity_type='Order',
                entity_id=str(order.id),
                previous_status=OrderStatus.DISPATCHED,
                new_status=OrderStatus.DELIVERED,
            )
            Notification.objects.create(  # Store.owner is a non-nullable FK
                user=order.store.owner,
                order=order,
                message=f'Tu pedido #{order.id} fue entregado. Confírmalo cuando lo recibas.',
            )
        return confirmacion
