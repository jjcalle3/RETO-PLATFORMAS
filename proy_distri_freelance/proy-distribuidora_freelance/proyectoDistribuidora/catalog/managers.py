"""Custom managers/querysets for the catalog app.

Business logic that used to live in catalog/views.py (product stock/discount
filtering, the CSV import pipeline, store map partitioning) lives here so views
stay thin and the same query is reusable across call sites.

Model classes/enums are imported lazily inside methods: catalog/models.py
imports these querysets at class-definition time, so a top-level import back
into models would be circular.
"""
import csv
import io

from django.db import IntegrityError, transaction
from django.db.models import Exists, F, OuterRef, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.db.models.manager import Manager
from django.utils import timezone


def sanitize_cell(value):
    """Formula-injection guardrail (CEO review, Section 3): strip a leading
    =/+/-/@ so a value like "=cmd()" can't execute if this data is later
    opened in a spreadsheet."""
    value = (value or '').strip()
    if value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value


class ProductQuerySet(QuerySet):
    def for_distributor(self, distributor):
        return self.filter(distributor=distributor)

    def active(self):
        from .models import ProductStatus
        return self.filter(status=ProductStatus.ACTIVE)

    def search(self, term):
        term = (term or '').strip()
        if not term:
            return self
        return self.filter(
            Q(name__icontains=term) | Q(sku__icontains=term) | Q(barcode__icontains=term)
        )

    def with_stock(self):
        """Annotate `_stock` with the total across all warehouses. Idempotent
        so it can be chained ahead of the stock filters below without the
        annotation being applied twice."""
        if '_stock' in self.query.annotations:
            return self
        return self.annotate(_stock=Coalesce(Sum('stock_levels__quantity'), 0))

    def in_stock(self):
        return self.with_stock().filter(_stock__gt=0)

    def out_of_stock(self):
        return self.with_stock().filter(_stock=0)

    def low_stock(self):
        """In stock but below the per-product threshold (the product listing's
        "low" filter): 0 < total < threshold."""
        return self.with_stock().filter(_stock__gt=0, _stock__lt=F('low_stock_threshold'))

    def needs_restock(self):
        """At or below the threshold, including zero-stock — the low-stock
        digest's definition."""
        return self.with_stock().filter(_stock__lt=F('low_stock_threshold'))

    def on_sale(self):
        from .models import Discount
        today = timezone.now().date()
        vigente = Discount.objects.filter(
            product=OuterRef('pk'), start_date__lte=today, end_date__gte=today,
        )
        return self.annotate(_on_sale=Exists(vigente)).filter(_on_sale=True)


class ProductManager(Manager.from_queryset(ProductQuerySet)):
    def import_from_csv(self, distributor, archivo):
        """Parse an uploaded product CSV and create one Product per valid row.

        Returns (imported_count, errors) where errors is a list of per-row
        human-readable strings. Category/Brand are pre-loaded once per
        distributor (was one query per row). Each row commits in its own
        atomic savepoint so a bad row never poisons the good ones.
        """
        from .models import Brand, Category

        texto = archivo.read().decode('utf-8-sig', errors='replace')
        lector = csv.DictReader(io.StringIO(texto))

        categorias = {c.name: c for c in Category.objects.filter(distributor=distributor)}
        marcas = {b.name: b for b in Brand.objects.filter(distributor=distributor)}

        importados = 0
        errores = []
        for numero, fila in enumerate(lector, start=2):  # header is row 1
            fila = {k: sanitize_cell(v) for k, v in fila.items()}
            try:
                with transaction.atomic():
                    categoria = categorias.get(fila.get('categoria', ''))
                    if categoria is None:
                        raise Category.DoesNotExist
                    marca = marcas.get(fila.get('brand', ''))
                    if marca is None:
                        raise Brand.DoesNotExist
                    self.create(
                        distributor=distributor,
                        name=fila['nombre'],
                        sku=fila['sku'],
                        barcode=fila.get('codigo_barras', ''),
                        category=categoria,
                        brand=marca,
                        unit_price=fila['precio'],
                        unit_of_measure=fila.get('unidad_medida') or self.model._meta.get_field('unit_of_measure').default,
                        low_stock_threshold=fila.get('stock_minimo') or self.model._meta.get_field('low_stock_threshold').default,
                    )
                    importados += 1
            except IntegrityError:
                errores.append(f'Fila {numero}: SKU "{fila.get("sku", "")}" ya existe')
            except Category.DoesNotExist:
                errores.append(f'Fila {numero}: categoría "{fila.get("categoria", "")}" no encontrada')
            except Brand.DoesNotExist:
                errores.append(f'Fila {numero}: marca "{fila.get("brand", "")}" no encontrada')
            except (KeyError, ValueError):
                errores.append(f'Fila {numero}: datos inválidos')

        return importados, errores


class StockLevelQuerySet(QuerySet):
    def for_distributor(self, distributor):
        """Active-product stock rows for the distributor's dashboard inventory
        table, eager-loaded and ordered for display."""
        from .models import ProductStatus
        return (
            self.filter(product__distributor=distributor, product__status=ProductStatus.ACTIVE)
            .select_related('warehouse', 'product')
            .order_by('product__name', 'warehouse__name')
        )

    def low_stock(self, distributor):
        """Stock rows whose quantity is below the product's threshold —
        the dashboard's low-stock alert count (per warehouse row)."""
        from .models import ProductStatus
        return self.filter(
            product__distributor=distributor,
            product__status=ProductStatus.ACTIVE,
            quantity__lt=F('product__low_stock_threshold'),
        )

    def lock_for_items(self, items):
        """`select_for_update()` the (product, warehouse) rows backing these
        order items, keyed by (product_id, warehouse_id). MUST be called
        inside an open `transaction.atomic()` — this is the lock target for
        Order.accept's concurrency-safe stock deduction (NFR-03.1)."""
        rows = self.select_for_update().filter(
            warehouse_id__in={item.warehouse_id for item in items},
            product_id__in=[item.product_id for item in items],
        )
        return {(row.product_id, row.warehouse_id): row for row in rows}


class StoreQuerySet(QuerySet):
    def for_distributor(self, distributor):
        return self.filter(distributor=distributor)

    def orderable_for(self, user):
        """Stores this owner can order for — i.e. with a vendor assigned."""
        return self.filter(owner=user, vendor__isnull=False)

    def with_coordinates(self):
        return self.exclude(latitude__isnull=True).exclude(longitude__isnull=True)

    def without_coordinates(self):
        return self.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))


class StockMovementQuerySet(QuerySet):
    """T8: Stock movement ledger queries for audit and history views."""

    def for_product(self, product, distributor=None):
        """Movements for a product (optionally scoped by distributor).
        Ordered by id (deterministic timeline, not clock-skew-prone created_at).
        Returns newest first."""
        qs = self.filter(product=product).select_related('actor', 'order')
        if distributor is not None:
            qs = qs.filter(product__distributor=distributor)
        return qs.order_by('-id')
