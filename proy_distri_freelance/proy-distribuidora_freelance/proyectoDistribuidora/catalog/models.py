from django.db import models, transaction
from django.db.models import F
from accounts.models import Distributor, User
from .managers import ProductManager, StockLevelQuerySet, StoreQuerySet, StockMovementQuerySet
from .exceptions import NegativeStock


class Store(models.Model):
    name = models.CharField(max_length=255)

    address = models.CharField(
        max_length=255,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="stores"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="stores"
    )

    # DR-01: vendor assigned by distributor; auto-populates Order.vendor at order creation
    vendor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_stores"
    )

    objects = StoreQuerySet.as_manager()

    def __str__(self):
        return self.name

    def as_marker(self):
        """Serialize to the dict the store-map template's JS expects. Assumes
        latitude/longitude are set — callers filter with `with_coordinates()`."""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'lat': float(self.latitude),
            'lng': float(self.longitude),
        }


class Category(models.Model):
    name = models.CharField(max_length=100)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="categories"
    )

    class Meta:
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "name"],
                name="unique_category_name_per_distributor"
            )
        ]

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="brands"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "name"],
                name="unique_brand_name_per_distributor"
            )
        ]

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """Tier 4.5: a single row per distributor today, real model so a second
    warehouse later needs no further schema change to Product/Order/OrderItem."""
    name = models.CharField(max_length=100)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="warehouses"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "name"],
                name="unique_warehouse_name_per_distributor"
            )
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_or_create_default(cls, distributor):
        """Single row per distributor today — centralizes the "which
        warehouse" question so callers (orders app, catalog stock
        management) never hardcode a lookup."""
        warehouse, _ = cls.objects.get_or_create(
            distributor=distributor,
            defaults={'name': 'Principal'},
        )
        return warehouse


class ProductStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    INACTIVE = "INACTIVE", "Inactivo"
    DISCONTINUED = "DISCONTINUED", "Descontinuado"


class UnitOfMeasure(models.TextChoices):
    PIECE = "PIECE", "Pieza"
    BOX = "BOX", "Caja"
    PACK = "PACK", "Paquete"
    BOTTLE = "BOTTLE", "Botella"
    KG = "KG", "Kilogramo"
    LITER = "LITER", "Litro"


class Product(models.Model):
    name = models.CharField(max_length=255)

    # DR-05/DR-06 era fields
    description = models.TextField(blank=True)

    # IVA-exclusive (Tier 4.5 resolution) — Ecuador's 15% IVA is calculated
    # on top wherever a final charged amount is shown, never baked in here.
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Tier 4.5: replaces the DR-06 `is_active` boolean outright. Migration
    # 0005 maps is_active=True -> ACTIVE, is_active=False -> INACTIVE.
    # DISCONTINUED is a distinct explicit action, never auto-mapped.
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE
    )

    # DR-05: alert threshold per product, configurable by distributor (US-25)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="products"
    )

    # Tier 4.5 additions
    sku = models.CharField(max_length=64)

    # Free text, no EAN-13/UPC validation (Tier 4.5 resolution) — Ecuadorian
    # retail mixes real GS1 barcodes with internally-assigned codes for
    # repackaged/bulk goods; blank when the product has no scannable code.
    barcode = models.CharField(max_length=64, blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products"
    )

    unit_of_measure = models.CharField(
        max_length=20,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.PIECE
    )

    objects = ProductManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "sku"],
                name="unique_product_sku_per_distributor"
            )
        ]

    def __str__(self):
        return self.name

    def _change_status(self, new_status, actor, action):
        """Set status + write the audit entry for a status transition, in the
        one shape the three status views (deactivate/reactivate/discontinue)
        used to inline verbatim."""
        from audit.models import AuditLog
        self.status = new_status
        self.save(update_fields=['status'])
        AuditLog.objects.create(
            user=actor,
            action=action,
            entity_type='Product',
            entity_id=str(self.id),
            details={'name': self.name},
        )

    def deactivate(self, actor):
        # DR-06 (Tier 4.5): status -> INACTIVE, not a hard delete — hard delete
        # would cascade to OrderItems.
        self._change_status(ProductStatus.INACTIVE, actor, 'product_deactivated')

    def reactivate(self, actor):
        self._change_status(ProductStatus.ACTIVE, actor, 'product_reactivated')

    def discontinue(self, actor):
        """Discontinued is a distinct explicit action from deactivate — never
        auto-mapped from is_active (Tier 4.5 resolution)."""
        self._change_status(ProductStatus.DISCONTINUED, actor, 'product_discontinued')

    def current_or_latest_discount(self):
        """The active discount if there is one, else the most recently-ended
        discount — what the discount-management form pre-populates from."""
        return self.active_discount() or self.discounts.order_by('-end_date').first()

    def total_stock(self):
        """Sum of StockLevel quantities across all warehouses. Call sites
        that iterate many products should prefetch_related('stock_levels')
        first to avoid one query per product."""
        return sum(sl.quantity for sl in self.stock_levels.all())

    def is_out_of_stock(self):
        return self.total_stock() == 0

    def active_discount(self):
        """Returns the currently-active Discount, if any. Expects callers
        that iterate many products to prefetch_related('discounts') first —
        this filters the already-fetched list in Python rather than issuing
        a new query per product (avoids the N+1 class Tier 3 already fixed
        once for FK joins)."""
        from django.utils import timezone
        today = timezone.now().date()
        for discount in self.discounts.all():
            if discount.start_date <= today <= discount.end_date:
                return discount
        return None

    def current_price(self):
        """unit_price with the active discount applied, if any. Never
        stored — expiry needs no cleanup job. Clamped at zero."""
        discount = self.active_discount()
        if discount is None:
            return self.unit_price
        return discount.apply_to(self.unit_price)


class DiscountType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Porcentaje"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Monto fijo"


class Discount(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="discounts"
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices
    )

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    start_date = models.DateField()

    end_date = models.DateField()

    def apply_to(self, price):
        """Compute the discounted price, clamped at zero. Percentage math is
        computed against the clean (IVA-exclusive) base price."""
        if self.discount_type == DiscountType.PERCENTAGE:
            discounted = price * (1 - (self.discount_value / 100))
        else:
            discounted = price - self.discount_value
        return max(discounted, 0)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        # Stacking rule: at most one active discount per product — checked at
        # the Python/form layer rather than a DB exclusion constraint, since
        # this project runs on SQLite in dev (no native date-range overlap
        # constraint support).
        if self.product_id:
            overlapping = Discount.objects.filter(product_id=self.product_id).exclude(pk=self.pk)
            for other in overlapping:
                if self.start_date <= other.end_date and other.start_date <= self.end_date:
                    raise ValidationError(
                        'Ya existe un descuento activo para este producto en ese rango de fechas.'
                    )

    def __str__(self):
        return f"{self.product} — {self.get_discount_type_display()} {self.discount_value}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="products/")

    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"{'Principal' if self.is_main else 'Adicional'} — {self.product}"


class StockLevel(models.Model):
    """Tier 4.5: replaces VendorInventory as the source of truth for stock,
    both for catalog display and for orders/views.py's aceptar_pedido lock.
    Centralized (not per-vendor) — confirmed with the business 2026-07-21."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_levels"
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_levels"
    )

    quantity = models.PositiveIntegerField(default=0)

    objects = StockLevelQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse"
            )
        ]

    def __str__(self):
        return f"{self.product} @ {self.warehouse} - {self.quantity}"

    def apply_movement(self, delta, reason, actor, order=None, note='', locked=False):
        """Private shared writer for all stock mutations. Owns atomic block + negative guard.

        Args:
            delta: signed int (positive for receipt, negative for deduct)
            reason: choice from StockMovement.ReasonChoices
            actor: User (who made the change)
            order: Order (nullable, for ORDER_DEDUCT movements)
            note: str (optional, for RECEIPT/ADJUSTMENT/COUNT_CORRECTION)
            locked: bool — if True, assumes this row is already select_for_update()'d
                    (used by Order.accept() which holds the lock); if False, acquires lock.

        Returns:
            StockMovement instance created

        Raises:
            NegativeStock if new quantity would be negative
        """
        if delta == 0:
            raise ValueError('El delta debe ser diferente de cero.')

        new_qty = self.quantity + delta
        if new_qty < 0:
            raise NegativeStock(self.quantity, delta)

        def do_update():
            self.quantity = new_qty
            self.save(update_fields=['quantity'])
            return StockMovement.objects.create(
                product=self.product,
                warehouse=self.warehouse,
                delta=delta,
                reason=reason,
                actor=actor,
                order=order,
                note=note,
                balance_after=new_qty,
            )

        if locked:
            # Called from Order.accept() which already holds select_for_update.
            return do_update()
        else:
            # Acquire lock for receive/contar/ajustar.
            with transaction.atomic():
                sl = StockLevel.objects.select_for_update().get(pk=self.pk)
                sl.quantity = new_qty
                sl.save(update_fields=['quantity'])
                return StockMovement.objects.create(
                    product=sl.product,
                    warehouse=sl.warehouse,
                    delta=delta,
                    reason=reason,
                    actor=actor,
                    order=order,
                    note=note,
                    balance_after=new_qty,
                )

    def receive(self, amount, actor, note=''):
        """Record a stock receipt. Amount must be positive."""
        if amount <= 0:
            raise ValueError('La cantidad recibida debe ser positiva.')
        return self.apply_movement(
            delta=amount,
            reason=StockMovement.ReasonChoices.RECEIPT,
            actor=actor,
            note=note,
            order=None,
        )

    def contar(self, counted, actor, note=''):
        """Record a physical count. Derives delta from counted absolute quantity."""
        if counted < 0:
            raise ValueError('La cantidad contada debe ser no negativa.')
        delta = counted - self.quantity
        return self.apply_movement(
            delta=delta,
            reason=StockMovement.ReasonChoices.COUNT_CORRECTION,
            actor=actor,
            note=note,
            order=None,
        )

    def ajustar(self, delta, actor, note):
        """Record an adjustment (breakage, correction, etc.). Delta is signed;
        note is mandatory."""
        if delta == 0:
            raise ValueError('El ajuste debe ser diferente de cero.')
        if not note:
            raise ValueError('La nota es obligatoria para un ajuste.')
        return self.apply_movement(
            delta=delta,
            reason=StockMovement.ReasonChoices.ADJUSTMENT,
            actor=actor,
            note=note,
            order=None,
        )

    def set_quantity(self, value):
        """Validate and persist a new stock quantity. Raises ValueError with a
        user-facing message when the value isn't a non-negative integer.

        DEPRECATED: Use receive/contar/ajustar instead. Kept for backward compat
        with legacy code."""
        try:
            cantidad = int(value)
        except (TypeError, ValueError):
            raise ValueError('La cantidad debe ser un número entero no negativo.')
        if cantidad < 0:
            raise ValueError('La cantidad debe ser un número entero no negativo.')
        self.quantity = cantidad
        self.save(update_fields=['quantity'])


class StockMovement(models.Model):
    """Append-only audit ledger for all stock changes. Every mutation to
    StockLevel.quantity must write a corresponding row here."""

    class ReasonChoices(models.TextChoices):
        OPENING_BALANCE = 'OPENING_BALANCE', 'Saldo inicial'
        RECEIPT = 'RECEIPT', 'Recepción'
        ADJUSTMENT = 'ADJUSTMENT', 'Ajuste'
        COUNT_CORRECTION = 'COUNT_CORRECTION', 'Corrección de conteo'
        ORDER_DEDUCT = 'ORDER_DEDUCT', 'Descuento de pedido'

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )

    delta = models.IntegerField()  # signed: positive for receipt, negative for deduct
    reason = models.CharField(
        max_length=20,
        choices=ReasonChoices.choices
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    note = models.TextField(blank=True)
    balance_after = models.PositiveIntegerField()  # the quantity AFTER this movement
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StockMovementQuerySet.as_manager()

    class Meta:
        # Timeline ordered by id (deterministic), not created_at (clock-skew risk).
        # Composite index for fast product-timeline queries.
        indexes = [
            models.Index(fields=['product', 'warehouse', 'id']),
        ]
        ordering = ['id']

    def __str__(self):
        return f"{self.reason} {self.delta:+d} @ {self.product} (bal={self.balance_after})"
