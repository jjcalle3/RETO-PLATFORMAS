"""Custom manager/queryset for the orders app.

Role-scoping, dashboard aggregations, and order-from-cart creation used to be
inlined in views. Centralized here so views stay thin and each query is reused
across the store-owner, vendor, distributor, and delivery call sites.

Model classes/enums are imported lazily inside methods to avoid a circular
import with orders/models.py, which imports OrderManager at class-definition
time.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
)
from django.db.models.manager import Manager


class OrderQuerySet(QuerySet):
    # --- role / tenant scoping ---

    def for_user(self, user):
        """Scope to the orders this role is allowed to see (US-* RBAC)."""
        if user.role == 'STORE_OWNER':
            return self.filter(store__owner=user)
        if user.role == 'VENDOR':
            return self.filter(vendor=user)
        if user.role == 'DISTRIBUTOR':
            return self.filter(store__distributor=user.distributor)
        return self.none()

    def for_distributor(self, distributor):
        return self.filter(store__distributor=distributor)

    def with_related(self):
        """Eager-load store+vendor and apply the stable oldest-first base order
        the order tables rely on (NFR-02.5, DESIGN.md "Sort/priority")."""
        return self.select_related('store', 'vendor').order_by('created_at')

    def with_item_count(self):
        return self.annotate(item_count=Count('items'))

    def recent(self, limit):
        return self.select_related('store', 'vendor').order_by('-created_at')[:limit]

    # --- role-specific work queues ---

    def pending_for_vendor(self, user):
        from .models import OrderStatus
        return (
            self.filter(vendor=user, status=OrderStatus.PENDING)
            .select_related('store')
            .with_item_count()
            .order_by('created_at')
        )

    def dispatched_for_distributor(self, distributor):
        from .models import OrderStatus
        return (
            self.filter(store__distributor=distributor, status=OrderStatus.DISPATCHED)
            .select_related('store', 'vendor')
            .prefetch_related('items__product')
            .order_by('created_at')
        )

    def issues_for(self, user):
        """DELIVERY_ISSUE orders for the delivery queue. A DELIVERY user only
        sees issues on deliveries they confirmed; a DISTRIBUTOR sees all."""
        from .models import OrderStatus
        qs = (
            self.filter(store__distributor=user.distributor, status=OrderStatus.DELIVERY_ISSUE)
            .select_related('store', 'vendor')
            .order_by('updated_at')
        )
        if user.role == 'DELIVERY':
            qs = qs.filter(delivery_confirmation__delivery_user=user)
        return qs

    # --- distributor dashboard (FR-08.*) ---

    def apply_dashboard_filters(self, date_from='', date_to='', vendor_ids=None, store_ids=None, statuses=None):
        qs = self
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if vendor_ids:
            qs = qs.filter(vendor_id__in=vendor_ids)
        if store_ids:
            qs = qs.filter(store_id__in=store_ids)
        if statuses:
            qs = qs.filter(status__in=statuses)
        return qs

    def counts_by_status(self):
        """[{status, total, status_label}] ordered needs-action first, then by
        status — the dashboard's orders-by-status cards."""
        from .models import OrderStatus
        from .templatetags.status_tags import NEEDS_ACTION_STATUSES
        labels = dict(OrderStatus.choices)
        filas = list(self.values('status').annotate(total=Count('id')))
        for fila in filas:
            fila['status_label'] = labels.get(fila['status'], fila['status'])
        filas.sort(
            key=lambda fila: (0 if fila['status'] in NEEDS_ACTION_STATUSES else 1, fila['status'])
        )
        return filas

    def average_fulfillment_time(self):
        """Mean created→CONFIRMED duration, rounded to whole seconds, or None
        when there are no confirmed orders. updated_at is exactly when a
        CONFIRMED order reached that terminal state."""
        from .models import OrderStatus
        duracion = ExpressionWrapper(
            F('updated_at') - F('created_at'), output_field=DurationField()
        )
        promedio = self.filter(status=OrderStatus.CONFIRMED).aggregate(
            promedio=Avg(duracion)
        )['promedio']
        if promedio is None:
            return None
        return timedelta(seconds=round(promedio.total_seconds()))

    def dashboard_metrics(self):
        """Summary KPIs in a single COUNT query plus the average-time query."""
        from .models import OrderStatus
        metricas = self.aggregate(
            total=Count('id'),
            fulfilled=Count('id', filter=Q(status=OrderStatus.CONFIRMED)),
            rejected=Count('id', filter=Q(status=OrderStatus.REJECTED)),
        )
        metricas['tiempo_promedio'] = self.average_fulfillment_time()
        return metricas


class OrderManager(Manager.from_queryset(OrderQuerySet)):
    def create_from_cart(self, store, cart, actor):
        """Create a PENDING order and its items from a session cart, snapshotting
        each line's current price and routing to the default warehouse, all in
        one atomic block. Inactive/foreign products are skipped.

        D6: Placement gate — validates each line has on-hand stock before creating
        the order. Raises InsufficientStock with per-line messages if any line
        exceeds available quantity; order is NOT created in that case."""
        from audit.models import AuditLog
        from catalog.models import Product, ProductStatus, Warehouse, StockLevel
        from .exceptions import InsufficientStock
        from .models import OrderItem, OrderStatus

        # D6: Aggregate cart lines by product (handle duplicates)
        aggregated = {}
        for item in cart['items']:
            product_id = item['product_id']
            try:
                qty = int(item['quantity'])
            except (TypeError, ValueError):
                raise InsufficientStock([f'Producto {product_id}: cantidad inválida.'])
            if qty <= 0:
                raise InsufficientStock([f'Producto {product_id}: cantidad debe ser positiva.'])
            aggregated[product_id] = aggregated.get(product_id, 0) + qty

        # D6: Resolve the same default warehouse OrderItem.snapshot() uses
        warehouse = Warehouse.get_or_create_default(store.distributor)

        # D6: Fetch products and stock levels in one query
        product_ids = list(aggregated.keys())
        products = {
            p.id: p
            for p in Product.objects.filter(
                id__in=product_ids, distributor=store.distributor, status=ProductStatus.ACTIVE
            )
        }
        stock_levels = {
            (sl.product_id, sl.warehouse_id): sl
            for sl in StockLevel.objects.filter(
                product_id__in=product_ids, warehouse=warehouse
            )
        }

        # D6: Validate on-hand availability before creating order
        errores = []
        for product_id, qty in aggregated.items():
            product = products.get(product_id)
            if product is None:
                continue  # Inactive/foreign products skipped silently
            sl = stock_levels.get((product_id, warehouse.id))
            disponible = sl.quantity if sl else 0
            if disponible < qty:
                errores.append(
                    f'{product.name}: disponible {disponible}, solicitado {qty}'
                )

        if errores:
            raise InsufficientStock(errores)

        # D6: All validations passed; create order atomically
        with transaction.atomic():
            pedido = self.create(store=store, vendor=store.vendor, status=OrderStatus.PENDING)
            for item in cart['items']:
                product = products.get(item['product_id'])
                if product is None:
                    continue
                try:
                    qty = int(item['quantity'])
                except (TypeError, ValueError):
                    continue
                linea = OrderItem(
                    order=pedido,
                    product=product,
                    quantity=qty,
                )
                linea.snapshot()  # Sets warehouse + unit_price_at_time
                linea.save()
            AuditLog.objects.create(
                user=actor,
                action='order_created',
                entity_type='Order',
                entity_id=str(pedido.id),
                new_status=OrderStatus.PENDING,
            )
        return pedido
