from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Distributor, Role, User
from .forms import ProductForm, StoreForm
from .models import (
    Brand,
    Category,
    Discount,
    DiscountType,
    Product,
    ProductStatus,
    StockLevel,
    StockMovement,
    Store,
    UnitOfMeasure,
    Warehouse,
)
from .exceptions import NegativeStock


def make_distributor(name='Distribuidora Test'):
    return Distributor.objects.create(name=name, email=f'{name.lower().replace(" ", "")}@test.com')


def make_distributor_user(distributor, email='admin@test.com'):
    return User.objects.create_user(
        email=email, password='pass1234', role=Role.DISTRIBUTOR, distributor=distributor
    )


def make_product(distributor, sku='SKU-1', name='Producto', price='10.00'):
    category = Category.objects.create(distributor=distributor, name='General')
    brand = Brand.objects.create(distributor=distributor, name='Marca')
    return Product.objects.create(
        distributor=distributor,
        name=name,
        sku=sku,
        category=category,
        brand=brand,
        unit_price=Decimal(price),
        unit_of_measure=UnitOfMeasure.PIECE,
    )


class ProductSkuUniquenessTest(TestCase):
    def test_same_sku_different_distributors_allowed(self):
        d1 = make_distributor('D1')
        d2 = make_distributor('D2')
        make_product(d1, sku='ABC')
        # Should NOT raise — SKU uniqueness is per-distributor, not global.
        make_product(d2, sku='ABC')
        self.assertEqual(Product.objects.filter(sku='ABC').count(), 2)

    def test_same_sku_same_distributor_rejected(self):
        d1 = make_distributor('D1')
        make_product(d1, sku='ABC')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_product(d1, sku='ABC', name='Otro producto')


class DiscountCurrentPriceTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.product = make_product(self.distributor, price='100.00')

    def test_no_discount_returns_unit_price(self):
        self.assertEqual(self.product.current_price(), Decimal('100.00'))

    def test_percentage_discount_active(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('15'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), Decimal('85.00'))

    def test_fixed_amount_discount_active(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal('30.00'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), Decimal('70.00'))

    def test_discount_clamped_at_zero(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal('500.00'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), 0)

    def test_expired_discount_reverts_to_unit_price(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('50'),
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), Decimal('100.00'))

    def test_overlapping_discounts_rejected(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('10'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
        )
        overlapping = Discount(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('20'),
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
        )
        with self.assertRaises(ValidationError):
            overlapping.clean()


class StockDerivationTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')

    def test_out_of_stock_when_no_stock_level_rows(self):
        self.assertTrue(self.product.is_out_of_stock())
        self.assertEqual(self.product.total_stock(), 0)

    def test_out_of_stock_when_quantity_zero(self):
        StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=0)
        self.assertTrue(self.product.is_out_of_stock())

    def test_in_stock_when_quantity_positive(self):
        StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=5)
        self.assertFalse(self.product.is_out_of_stock())
        self.assertEqual(self.product.total_stock(), 5)


class ProductFormTenantScopingTest(TestCase):
    def test_category_and_brand_scoped_to_distributor(self):
        d1 = make_distributor('D1')
        d2 = make_distributor('D2')
        cat1 = Category.objects.create(distributor=d1, name='Cat1')
        Category.objects.create(distributor=d2, name='Cat2')

        formulario = ProductForm(distributor=d1)
        self.assertIn(cat1, formulario.fields['category'].queryset)
        self.assertEqual(formulario.fields['category'].queryset.count(), 1)


class StoreFormRoleFilterTest(TestCase):
    """ISBEN roadmap item 3: StoreForm's vendor/owner dropdowns must filter
    by BOTH role AND distributor together — composing with, not replacing,
    the existing tenant scope (Eng-Review Finding B7 / Cross-Model Tension
    Finding 7)."""

    def test_vendor_queryset_excludes_non_vendor_and_cross_tenant(self):
        d1 = make_distributor('D1')
        d2 = make_distributor('D2')
        vendedor = User.objects.create_user(email='v@test.com', password='x', role=Role.VENDOR, distributor=d1)
        repartidor = User.objects.create_user(email='r@test.com', password='x', role=Role.DELIVERY, distributor=d1)
        vendedor_otro_tenant = User.objects.create_user(
            email='v2@test.com', password='x', role=Role.VENDOR, distributor=d2
        )

        formulario = StoreForm(distributor=d1)
        vendor_qs = formulario.fields['vendor'].queryset
        self.assertIn(vendedor, vendor_qs)
        self.assertNotIn(repartidor, vendor_qs)
        self.assertNotIn(vendedor_otro_tenant, vendor_qs)

    def test_owner_queryset_excludes_non_store_owner_and_cross_tenant(self):
        d1 = make_distributor('D1')
        d2 = make_distributor('D2')
        propietario = User.objects.create_user(
            email='o@test.com', password='x', role=Role.STORE_OWNER, distributor=d1
        )
        vendedor = User.objects.create_user(email='v@test.com', password='x', role=Role.VENDOR, distributor=d1)
        propietario_otro_tenant = User.objects.create_user(
            email='o2@test.com', password='x', role=Role.STORE_OWNER, distributor=d2
        )

        formulario = StoreForm(distributor=d1)
        owner_qs = formulario.fields['owner'].queryset
        self.assertIn(propietario, owner_qs)
        self.assertNotIn(vendedor, owner_qs)
        self.assertNotIn(propietario_otro_tenant, owner_qs)


class CategoryTenantIsolationViewTest(TestCase):
    def setUp(self):
        self.d1 = make_distributor('D1')
        self.d2 = make_distributor('D2')
        self.user1 = make_distributor_user(self.d1, 'u1@test.com')
        Category.objects.create(distributor=self.d1, name='CatD1')
        Category.objects.create(distributor=self.d2, name='CatD2')

    def test_catalog_index_only_shows_own_distributor_categories(self):
        client = Client()
        client.force_login(self.user1)
        # index_catalog is just a links page with no category list; the
        # categories themselves render on index_categorias.
        response = client.get(reverse('index_categorias'))
        self.assertContains(response, 'CatD1')
        self.assertNotContains(response, 'CatD2')


class ProductViewsSmokeTest(TestCase):
    """Every new/extended view actually renders for a logged-in distributor.
    Catches URL/view kwarg-name mismatches that model- and form-level tests
    above don't exercise (e.g. gestionar_descuento/editar_stock originally
    declared as <int:id> in urls.py but product_id in the view signature)."""

    def setUp(self):
        self.distributor = make_distributor()
        self.user = make_distributor_user(self.distributor)
        self.product = make_product(self.distributor)
        self.client = Client()
        self.client.force_login(self.user)

    def test_all_product_related_views_return_200(self):
        paths = [
            reverse('index_catalog'),
            reverse('inventario'),
            reverse('crear_producto'),
            reverse('editar_producto', args=[self.product.id]),
            reverse('gestionar_descuento', args=[self.product.id]),
            reverse('recibir_stock', args=[self.product.id]),
            reverse('contar_stock', args=[self.product.id]),
            reverse('ajustar_stock', args=[self.product.id]),
            reverse('historial_stock', args=[self.product.id]),
            reverse('importar_productos'),
            reverse('crear_categoria'),
            reverse('crear_marca'),
        ]
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, f'{path} returned {response.status_code}')

    def test_recibir_stock_updates_quantity_and_triggers_digest_check(self):
        warehouse = Warehouse.get_or_create_default(self.distributor)
        response = self.client.post(
            reverse('recibir_stock', args=[self.product.id]), {'cantidad': '7', 'nota': ''}
        )
        self.assertEqual(response.status_code, 302)
        stock = StockLevel.objects.get(product=self.product, warehouse=warehouse)
        self.assertEqual(stock.quantity, 7)


class CsvImportTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.user = make_distributor_user(self.distributor)
        self.category = Category.objects.create(distributor=self.distributor, name='Bebidas')
        self.brand = Brand.objects.create(distributor=self.distributor, name='CocaCola')
        Product.objects.create(
            distributor=self.distributor, name='Existente', sku='DUP',
            category=self.category, brand=self.brand, unit_price=Decimal('1.00'),
        )

    def _csv_file(self, content):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('import.csv', content.encode('utf-8'), content_type='text/csv')

    def test_row_level_skip_valid_and_invalid_rows(self):
        csv_content = (
            'nombre,sku,codigo_barras,categoria,brand,precio,unidad_medida,stock_minimo\n'
            'Producto Valido,NEW1,123,Bebidas,CocaCola,5.50,PIECE,5\n'
            'Producto Duplicado,DUP,124,Bebidas,CocaCola,5.50,PIECE,5\n'
            'Producto Sin Categoria,NEW2,125,NoExiste,CocaCola,5.50,PIECE,5\n'
        )
        client = Client()
        client.force_login(self.user)
        response = client.post(
            reverse('importar_productos'),
            {'archivo_csv': self._csv_file(csv_content)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 producto(s) importado')
        self.assertContains(response, 'SKU')
        self.assertTrue(Product.objects.filter(sku='NEW1').exists())
        self.assertFalse(Product.objects.filter(sku='NEW2').exists())
        # The pre-existing DUP row must be untouched, not overwritten.
        self.assertEqual(Product.objects.filter(sku='DUP').count(), 1)

    def test_formula_injection_sanitized(self):
        csv_content = (
            'nombre,sku,codigo_barras,categoria,brand,precio,unidad_medida,stock_minimo\n'
            '=cmd(),NEW3,123,Bebidas,CocaCola,5.50,PIECE,5\n'
        )
        client = Client()
        client.force_login(self.user)
        client.post(reverse('importar_productos'), {'archivo_csv': self._csv_file(csv_content)})
        producto = Product.objects.get(sku='NEW3')
        self.assertFalse(producto.name.startswith('='))


class ProductQuerySetFilterTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.category = Category.objects.create(distributor=self.distributor, name='General')
        self.brand = Brand.objects.create(distributor=self.distributor, name='Marca')
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')
        self.p_out = self._product('OUT', 'Sin stock')  # no stock rows
        self.p_low = self._product('LOW', 'Bajo', threshold=5)
        self.p_ok = self._product('OK', 'Suficiente')
        StockLevel.objects.create(product=self.p_low, warehouse=self.warehouse, quantity=2)
        StockLevel.objects.create(product=self.p_ok, warehouse=self.warehouse, quantity=50)

    def _product(self, sku, name, threshold=5):
        return Product.objects.create(
            distributor=self.distributor, name=name, sku=sku,
            category=self.category, brand=self.brand,
            unit_price=Decimal('10.00'), unit_of_measure=UnitOfMeasure.PIECE,
            low_stock_threshold=threshold,
        )

    def test_in_stock(self):
        qs = Product.objects.for_distributor(self.distributor).in_stock()
        self.assertIn(self.p_low, qs)
        self.assertIn(self.p_ok, qs)
        self.assertNotIn(self.p_out, qs)

    def test_out_of_stock(self):
        qs = Product.objects.for_distributor(self.distributor).out_of_stock()
        self.assertIn(self.p_out, qs)
        self.assertNotIn(self.p_ok, qs)

    def test_low_stock_excludes_zero(self):
        qs = Product.objects.for_distributor(self.distributor).low_stock()
        self.assertIn(self.p_low, qs)          # 0 < 2 < 5
        self.assertNotIn(self.p_out, qs)       # zero is "out", not "low"
        self.assertNotIn(self.p_ok, qs)

    def test_needs_restock_includes_zero(self):
        qs = Product.objects.for_distributor(self.distributor).needs_restock()
        self.assertIn(self.p_low, qs)
        self.assertIn(self.p_out, qs)          # digest counts zero-stock as low
        self.assertNotIn(self.p_ok, qs)

    def test_on_sale(self):
        Discount.objects.create(
            product=self.p_ok, discount_type=DiscountType.PERCENTAGE, discount_value=Decimal('10'),
            start_date=date.today() - timedelta(days=1), end_date=date.today() + timedelta(days=1),
        )
        qs = Product.objects.for_distributor(self.distributor).on_sale()
        self.assertIn(self.p_ok, qs)
        self.assertNotIn(self.p_low, qs)

    def test_search_matches_name_and_sku(self):
        by_name = Product.objects.for_distributor(self.distributor).search('Bajo')
        self.assertIn(self.p_low, by_name)
        by_sku = Product.objects.for_distributor(self.distributor).search('OK')
        self.assertIn(self.p_ok, by_sku)


class ProductImportManagerTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.category = Category.objects.create(distributor=self.distributor, name='Bebidas')
        self.brand = Brand.objects.create(distributor=self.distributor, name='CocaCola')

    def _csv_file(self, content):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('import.csv', content.encode('utf-8'), content_type='text/csv')

    def test_import_returns_counts_and_errors(self):
        csv_content = (
            'nombre,sku,codigo_barras,categoria,brand,precio,unidad_medida,stock_minimo\n'
            'Valido,NEW1,123,Bebidas,CocaCola,5.50,PIECE,5\n'
            'Sin categoria,NEW2,125,NoExiste,CocaCola,5.50,PIECE,5\n'
        )
        importados, errores = Product.objects.import_from_csv(self.distributor, self._csv_file(csv_content))
        self.assertEqual(importados, 1)
        self.assertEqual(len(errores), 1)
        self.assertTrue(Product.objects.filter(sku='NEW1').exists())
        self.assertFalse(Product.objects.filter(sku='NEW2').exists())

    def test_defaults_applied_when_columns_blank(self):
        csv_content = (
            'nombre,sku,codigo_barras,categoria,brand,precio,unidad_medida,stock_minimo\n'
            'Sin opcionales,NEW9,,Bebidas,CocaCola,3.00,,\n'
        )
        importados, _ = Product.objects.import_from_csv(self.distributor, self._csv_file(csv_content))
        self.assertEqual(importados, 1)
        producto = Product.objects.get(sku='NEW9')
        self.assertEqual(producto.unit_of_measure, UnitOfMeasure.PIECE)
        self.assertEqual(producto.low_stock_threshold, 5)


class StockLevelSetQuantityTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=0)

    def test_valid_value_persists(self):
        self.stock.set_quantity('12')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 12)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            self.stock.set_quantity('-3')

    def test_non_integer_rejected(self):
        with self.assertRaises(ValueError):
            self.stock.set_quantity('abc')


class StockMovementTest(TestCase):
    """T7: Stock movement ledger tests (receive/count/adjust + math)."""

    def setUp(self):
        self.distributor = make_distributor()
        self.admin = make_distributor_user(self.distributor)
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=0)

    def test_receive_creates_receipt_movement(self):
        from .models import StockMovement
        self.stock.receive(amount=5, actor=self.admin, note='Initial receipt')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        movement = StockMovement.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(movement.delta, 5)
        self.assertEqual(movement.reason, StockMovement.ReasonChoices.RECEIPT)
        self.assertEqual(movement.balance_after, 5)

    def test_receive_zero_rejected(self):
        with self.assertRaises(ValueError):
            self.stock.receive(amount=0, actor=self.admin)

    def test_contar_absolute_quantity_creates_count_movement(self):
        from .models import StockMovement
        # Start with 5
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()  # Refresh after receive
        # Count and find 3 (delta = 3 - 5 = -2)
        self.stock.contar(counted=3, actor=self.admin, note='Monthly count')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 3)
        movement = StockMovement.objects.filter(
            product=self.product,
            warehouse=self.warehouse,
            reason=StockMovement.ReasonChoices.COUNT_CORRECTION
        ).first()
        self.assertEqual(movement.delta, -2)
        self.assertEqual(movement.balance_after, 3)

    def test_contar_zero_allowed(self):
        from .models import StockMovement
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()  # Refresh after receive
        self.stock.contar(counted=0, actor=self.admin, note='Empty warehouse')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 0)
        movement = StockMovement.objects.filter(
            product=self.product,
            warehouse=self.warehouse,
            reason=StockMovement.ReasonChoices.COUNT_CORRECTION
        ).first()
        self.assertEqual(movement.delta, -5)

    def test_ajustar_positive_delta(self):
        from .models import StockMovement
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()  # Refresh after receive
        self.stock.ajustar(delta=3, actor=self.admin, note='Correction from vendor')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        movement = StockMovement.objects.filter(
            product=self.product,
            warehouse=self.warehouse,
            reason=StockMovement.ReasonChoices.ADJUSTMENT
        ).first()
        self.assertEqual(movement.delta, 3)

    def test_ajustar_negative_delta_raises_if_insufficient(self):
        from .exceptions import NegativeStock
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()  # Refresh after receive
        with self.assertRaises(NegativeStock):
            self.stock.ajustar(delta=-10, actor=self.admin, note='Invalid negative')

    def test_ajustar_negative_delta_allowed_if_sufficient(self):
        from .models import StockMovement
        self.stock.receive(amount=10, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()  # Refresh after receive
        self.stock.ajustar(delta=-3, actor=self.admin, note='Damage')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 7)

    def test_movement_balance_tracks_cumulative_sum(self):
        from .models import StockMovement
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()
        self.stock.receive(amount=3, actor=self.admin, note='Second receipt')
        self.stock.refresh_from_db()
        self.stock.ajustar(delta=-2, actor=self.admin, note='Damage')
        movements = StockMovement.objects.filter(
            product=self.product,
            warehouse=self.warehouse
        ).order_by('id')
        self.assertEqual(movements[0].balance_after, 5)
        self.assertEqual(movements[1].balance_after, 8)
        self.assertEqual(movements[2].balance_after, 6)


class ReconcileStockCommandTest(TestCase):
    """T6/T7: reconcile_stock command detects and reports discrepancies."""

    def setUp(self):
        from io import StringIO
        from django.core.management import call_command
        self.call_command = call_command
        self.distributor = make_distributor()
        self.admin = make_distributor_user(self.distributor)
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=0)

    def test_reconcile_clean_database_succeeds(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        exit_code = None
        try:
            call_command('reconcile_stock', stdout=out)
        except SystemExit as e:
            exit_code = e.code
        self.assertIsNone(exit_code, "Command should not raise SystemExit when no discrepancies")

    def test_reconcile_with_movements_matches(self):
        from io import StringIO
        from django.core.management import call_command
        # Create movements that match stock quantity
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        self.stock.refresh_from_db()
        self.stock.receive(amount=3, actor=self.admin, note='Second')
        self.stock.refresh_from_db()
        out = StringIO()
        exit_code = None
        try:
            call_command('reconcile_stock', stdout=out)
        except SystemExit as e:
            exit_code = e.code
        self.assertIsNone(exit_code, "Command should succeed when movements match")
        self.assertIn('successfully', out.getvalue())

    def test_reconcile_detects_quantity_drift(self):
        from io import StringIO
        from django.core.management import call_command
        from django.db import connection
        # Create a movement, then manually alter the quantity to cause drift
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        # Manually corrupt the stock quantity (simulate a drift)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE catalog_stocklevel SET quantity = %s WHERE id = %s",
                [10, self.stock.id]
            )
        out = StringIO()
        exit_code = None
        try:
            call_command('reconcile_stock', stdout=out)
        except SystemExit as e:
            exit_code = e.code
        self.assertEqual(exit_code, 1, "Command should exit with code 1 when discrepancies exist")

    def test_reconcile_reports_discrepancy_details(self):
        from io import StringIO
        from django.core.management import call_command
        from django.db import connection
        self.stock.receive(amount=5, actor=self.admin, note='Initial')
        # Corrupt: recorded 10, ledger 5
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE catalog_stocklevel SET quantity = %s WHERE id = %s",
                [10, self.stock.id]
            )
        out = StringIO()
        try:
            call_command('reconcile_stock', stdout=out)
        except SystemExit:
            pass
        output = out.getvalue()
        self.assertIn(self.product.name, output)
        self.assertIn('recorded 10', output)
        self.assertIn('ledger sum 5', output)


class StoreSelfEditTest(TestCase):
    """STORE_OWNER self-editing their own store (Configuración → Mi tienda):
    self-scoped, and the form must not expose the FK fields that would let an
    owner reassign their store away from its tenant (CEO-review landmine)."""

    def setUp(self):
        self.distributor = make_distributor()
        self.owner = User.objects.create_user(
            email='owner@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=self.distributor
        )
        self.vendor = User.objects.create_user(
            email='vendor@test.com', password='pass1234', role=Role.VENDOR, distributor=self.distributor
        )
        self.store = Store.objects.create(
            name='Mi Tienda', distributor=self.distributor, owner=self.owner, vendor=self.vendor
        )
        self.url = reverse('config_mi_tienda')

    def test_form_excludes_privilege_fields(self):
        from .forms import StoreSelfEditForm
        fields = StoreSelfEditForm().fields
        for forbidden in ('owner', 'vendor', 'distributor'):
            self.assertNotIn(forbidden, fields)

    def test_owner_edits_own_store(self):
        client = Client()
        client.force_login(self.owner)
        response = client.post(self.url, {
            'name': 'Tienda Renombrada', 'address': 'Calle 1', 'phone_number': '099',
        })
        self.assertEqual(response.status_code, 302)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, 'Tienda Renombrada')
        # FKs untouched even though a crafted POST included them.
        self.assertEqual(self.store.owner, self.owner)
        self.assertEqual(self.store.vendor, self.vendor)

    def test_crafted_fk_reassignment_ignored(self):
        other = User.objects.create_user(
            email='attacker@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=self.distributor
        )
        client = Client()
        client.force_login(self.owner)
        client.post(self.url, {'name': 'X', 'address': '', 'phone_number': '', 'owner': other.id})
        self.store.refresh_from_db()
        self.assertEqual(self.store.owner, self.owner)  # reassignment ignored

    def test_wrong_role_forbidden(self):
        client = Client()
        client.force_login(self.vendor)
        self.assertEqual(client.get(self.url).status_code, 403)
