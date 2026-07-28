from django.db import models, transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Store, Product, Warehouse, StockMovement
from .managers import OrderManager


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    ACCEPTED = "ACCEPTED", "Aceptado"
    REJECTED = "REJECTED", "Rechazado"
    DISPATCHED = "DISPATCHED", "Despachado"
    # DELIVERED is non-terminal: it means "delivery person dropped it off,
    # awaiting store owner confirmation" (DR-09). The store owner then moves
    # it to CONFIRMED (received as expected) or DELIVERY_ISSUE (dispute);
    # resolving an issue moves it back to CONFIRMED.
    DELIVERED = "DELIVERED", "Entregado"
    DELIVERY_ISSUE = "DELIVERY_ISSUE", "Problema de Entrega"
    CONFIRMED = "CONFIRMED", "Confirmado"


class Order(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )

    previous_order = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resubmissions"
    )

    # Set by vendor on rejection; surfaced in store owner notification (US-12)
    rejection_reason = models.CharField(max_length=500, blank=True)

    # DR-09: store owner's delivery-issue report and the vendor's resolution.
    # No structured remediation (inventory adjustment, partial fulfillment)
    # yet — notes only; see docs/requirements.md.
    issue_description = models.TextField(blank=True)
    issue_reported_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = OrderManager()

    class Meta:
        # NFR-02.6: composite index for the vendor's pending-orders queries
        # and the polling endpoint; a separate index for store-scoped
        # lookups (store owner's order list, distributor dashboard).
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['store']),
        ]

    def __str__(self):
        return f"Order {self.id}"

    # --- derived values ---

    @property
    def is_dispatched(self):
        return self.status == OrderStatus.DISPATCHED

    def total(self):
        """Sum of each line's frozen price × quantity. Iterates the related
        items — callers rendering many orders should prefetch 'items'."""
        return sum(item.unit_price_at_time * item.quantity for item in self.items.all())

    def _log(self, actor, action, previous_status='', new_status='', details=None):
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=actor,
            action=action,
            entity_type='Order',
            entity_id=str(self.id),
            previous_status=previous_status,
            new_status=new_status,
            details=details or {},
        )

    def _notify(self, user, message):
        from accounts.models import Notification, NotificationPreference
        # Respect the recipient's opt-out for order status notifications.
        if not NotificationPreference.for_user(user).wants('order_updates'):
            return
        Notification.objects.create(user=user, order=self, message=message)

    # --- state-machine transitions ---
    # Each owns its own status change, audit entry, and notification so views
    # shrink to a single call. accept() additionally owns the atomic stock
    # lock/deduct; the rest are single-row saves.

    def accept(self, actor):
        """PENDING → ACCEPTED (vendor). Atomically locks the order (to detect
        double-accept races), verifies stock availability, deducts via
        apply_movement, and notifies the store owner (UC-11, NFR-03.1, D9).
        Raises EmptyOrder if the order has no items, or InsufficientStock
        (with per-item messages) if any line can't be filled — in which case
        a failure is audited and no stock or status change is committed."""
        from catalog.models import StockLevel
        from .exceptions import EmptyOrder, InsufficientStock

        items = list(self.items.select_related('product'))
        if not items:
            raise EmptyOrder('El pedido no tiene items.')

        errores = []
        with transaction.atomic():
            # D9: Lock and re-check order status to prevent same-order double-accept.
            self_locked = Order.objects.select_for_update().get(pk=self.pk)
            if self_locked.status != OrderStatus.PENDING:
                raise InsufficientStock([f'El pedido ya fue procesado (estado: {self_locked.status}).'])

            niveles = StockLevel.objects.lock_for_items(items)
            for item in items:
                nivel = niveles.get((item.product_id, item.warehouse_id))
                disponible = nivel.quantity if nivel else 0
                if disponible < item.quantity:
                    errores.append(
                        f'{item.product.name}: disponible {disponible}, solicitado {item.quantity}'
                    )
            if not errores:
                deducciones = []
                for item in items:
                    nivel = niveles[(item.product_id, item.warehouse_id)]
                    # Route deduction through apply_movement (D7) with locked=True
                    # since we already hold the select_for_update lock on the row.
                    nivel.apply_movement(
                        delta=-item.quantity,
                        reason=StockMovement.ReasonChoices.ORDER_DEDUCT,
                        actor=actor,
                        order=self_locked,
                        locked=True,
                    )
                    deducciones.append({
                        'product': item.product.name,
                        'quantity_deducted': item.quantity,
                        'remaining_stock': nivel.quantity,
                    })
                self_locked.status = OrderStatus.ACCEPTED
                self_locked.save(update_fields=['status', 'updated_at'])
                self_locked._log(
                    actor, 'order_accepted',
                    previous_status=OrderStatus.PENDING, new_status=OrderStatus.ACCEPTED,
                    details={'inventory_deductions': deducciones},
                )
                self_locked._notify(self_locked.store.owner, f'Tu pedido #{self_locked.id} fue aceptado.')
                self.status = self_locked.status
        # The empty commit above leaves the order PENDING on failure; the
        # failure is audited outside that transaction so it persists.
        if errores:
            self._log(actor, 'order_accept_failed', details={'errors': errores})
            raise InsufficientStock(errores)

    def reject(self, actor, reason):
        """PENDING → REJECTED (vendor), with the vendor's reason."""
        self.status = OrderStatus.REJECTED
        self.rejection_reason = (reason or '').strip()[:500]
        self.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        self._log(
            actor, 'order_rejected',
            previous_status=OrderStatus.PENDING, new_status=OrderStatus.REJECTED,
            details={'rejection_reason': self.rejection_reason},
        )
        mensaje = f'Tu pedido #{self.id} fue rechazado.'
        if self.rejection_reason:
            mensaje += f' Motivo: {self.rejection_reason}'
        self._notify(self.store.owner, mensaje)

    def cancel(self, actor):
        """PENDING → REJECTED (store owner withdraws — US-23). No notification;
        the owner initiated it."""
        self.status = OrderStatus.REJECTED
        self.rejection_reason = 'Cancelado por el propietario de la tienda'
        self.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        self._log(
            actor, 'order_cancelled',
            previous_status=OrderStatus.PENDING, new_status=OrderStatus.REJECTED,
            details={'rejection_reason': self.rejection_reason},
        )

    def dispatch(self, actor):
        """ACCEPTED → DISPATCHED (vendor)."""
        self.status = OrderStatus.DISPATCHED
        self.save(update_fields=['status', 'updated_at'])
        self._log(
            actor, 'order_dispatched',
            previous_status=OrderStatus.ACCEPTED, new_status=OrderStatus.DISPATCHED,
        )
        self._notify(self.store.owner, f'Tu pedido #{self.id} fue despachado.')

    def confirm_receipt(self, actor):
        """DELIVERED → CONFIRMED (store owner, terminal)."""
        self.status = OrderStatus.CONFIRMED
        self.save(update_fields=['status', 'updated_at'])
        self._log(
            actor, 'order_confirmed',
            previous_status=OrderStatus.DELIVERED, new_status=OrderStatus.CONFIRMED,
        )
        self._notify(
            self.vendor,
            f'La tienda {self.store.name} confirmó la recepción del pedido #{self.id}.',
        )

    def report_issue(self, actor):
        """DELIVERED → DELIVERY_ISSUE (store owner). Expects issue_description
        already set on the instance (populated by ReportarIncidenciaForm).
        Notifies the vendor and, if on record, the delivery person."""
        self.status = OrderStatus.DELIVERY_ISSUE
        self.issue_reported_at = timezone.now()
        self.save(update_fields=['status', 'issue_description', 'issue_reported_at', 'updated_at'])
        self._notify(
            self.vendor,
            f'La tienda {self.store.name} reportó un problema con el pedido #{self.id}.',
        )
        confirmacion = getattr(self, 'delivery_confirmation', None)
        if confirmacion is not None:
            self._notify(
                confirmacion.delivery_user,
                f'Se reportó un problema con la entrega del pedido #{self.id}.',
            )

    def resolve_issue(self, actor):
        """DELIVERY_ISSUE → CONFIRMED (vendor or distributor, terminal). Expects
        resolution_notes already set on the instance (ResolverIncidenciaForm)."""
        self.status = OrderStatus.CONFIRMED
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolution_notes', 'resolved_at', 'updated_at'])
        self._log(
            actor, 'delivery_issue_resolved',
            previous_status=OrderStatus.DELIVERY_ISSUE, new_status=OrderStatus.CONFIRMED,
            details={'resolution_notes': self.resolution_notes},
        )
        self._notify(
            self.store.owner,
            f'El vendedor resolvió la incidencia del pedido #{self.id}.',
        )


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    # Tier 4.5: explicit warehouse so aceptar_pedido's StockLevel lock is
    # scoped by (product, warehouse) from day one — otherwise "multi-
    # warehouse ready" is cosmetic, since accept-time deduction would have
    # nowhere to route once a second warehouse exists. Set server-side from
    # the store's distributor's default warehouse, never client-supplied.
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    quantity = models.PositiveIntegerField()

    unit_price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_order_product"
            )
        ]

    def __str__(self):
        return f"{self.product} ({self.quantity})"

    def snapshot(self):
        """Freeze the line's price and route it to the distributor's default
        warehouse — the single source of both facts, previously duplicated
        (and inconsistent: cart used current_price, item forms used
        unit_price). current_price() is authoritative: the discounted price at
        order time, never changing afterward. Warehouse is always server-side,
        never client-supplied."""
        self.unit_price_at_time = self.product.current_price()
        self.warehouse = Warehouse.get_or_create_default(self.order.store.distributor)