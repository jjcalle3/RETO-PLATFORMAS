import threading
from decimal import Decimal

from django.contrib.sessions.backends.db import SessionStore
from django.db import OperationalError, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from audit.models import AuditLog
from accounts.models import Distributor, Notification, Role, User
from catalog.models import Brand, Category, Discount, DiscountType, Product, StockLevel, Store, UnitOfMeasure, Warehouse
from datetime import date, timedelta
from .cart import Cart
from .exceptions import EmptyOrder, InsufficientStock
from .forms import OrderItemForm
from .models import Order, OrderItem, OrderStatus


def make_distributor():
    return Distributor.objects.create(name='Distribuidora Test', email='dist@test.com')


def make_product(distributor, sku='SKU-1', price='10.00'):
    category = Category.objects.create(distributor=distributor, name='General')
    brand = Brand.objects.create(distributor=distributor, name='Marca')
    return Product.objects.create(
        distributor=distributor, name='Producto', sku=sku, category=category, brand=brand,
        unit_price=Decimal(price), unit_of_measure=UnitOfMeasure.PIECE,
    )


class OrderAcceptStockLevelTest(TestCase):
    """Tier 4.5 regression suite (docs/TODOS.md): StockLevel replaces
    VendorInventory as aceptar_pedido's lock target. These tests re-verify
    the Tier 2 concurrency-critical accept flow against the new model."""

    def setUp(self):
        self.distributor = make_distributor()
        self.vendor = User.objects.create_user(
            email='vendor@test.com', password='pass1234', role=Role.VENDOR, distributor=self.distributor
        )
        self.owner = User.objects.create_user(
            email='owner@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=self.distributor
        )
        from catalog.models import Store
        self.store = Store.objects.create(
            name='Tienda', distributor=self.distributor, owner=self.owner, vendor=self.vendor
        )
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=10)

        self.order = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)
        OrderItem.objects.create(
            order=self.order, product=self.product, warehouse=self.warehouse,
            quantity=4, unit_price_at_time=self.product.unit_price,
        )

    def _accept(self):
        client = Client()
        client.force_login(self.vendor)
        return client.post(reverse('aceptar_pedido', args=[self.order.id]))

    def test_accept_deducts_stock_and_transitions_to_accepted(self):
        self._accept()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.ACCEPTED)
        self.assertEqual(self.stock.quantity, 6)

    def test_accept_notifies_store_owner(self):
        self._accept()
        self.assertTrue(
            Notification.objects.filter(user=self.owner, order=self.order).exists()
        )

    def test_insufficient_stock_rolls_back_order_stays_pending(self):
        self.stock.quantity = 2  # less than the 4 requested
        self.stock.save()
        self._accept()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PENDING)
        self.assertEqual(self.stock.quantity, 2)  # unchanged — nothing written

    def test_second_order_fails_after_first_depletes_stock(self):
        """Sequential double-spend regression: two orders against the same
        (product, warehouse) — the first accept must not let the second
        oversell what's left."""
        second_order = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)
        OrderItem.objects.create(
            order=second_order, product=self.product, warehouse=self.warehouse,
            quantity=8, unit_price_at_time=self.product.unit_price,
        )
        self._accept()  # first order takes 4, leaving 6
        client = Client()
        client.force_login(self.vendor)
        client.post(reverse('aceptar_pedido', args=[second_order.id]))
        second_order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(second_order.status, OrderStatus.PENDING)  # 8 > 6 remaining — rejected
        self.assertEqual(self.stock.quantity, 6)  # only the first accept deducted


class OrderItemFormFR053Test(TestCase):
    """FR-05.3 resolution (Tier 4.5): any active product in the distributor's
    catalog is orderable, not scoped to what a specific vendor stocks."""

    def test_product_queryset_not_scoped_by_vendor(self):
        distributor = make_distributor()
        vendor = User.objects.create_user(
            email='v@test.com', password='pass1234', role=Role.VENDOR, distributor=distributor
        )
        product = make_product(distributor)  # not stocked by any specific vendor
        formulario = OrderItemForm(vendor=vendor)
        self.assertIn(product, formulario.fields['product'].queryset)

    def test_inactive_product_excluded(self):
        from catalog.models import ProductStatus
        distributor = make_distributor()
        vendor = User.objects.create_user(
            email='v2@test.com', password='pass1234', role=Role.VENDOR, distributor=distributor
        )
        product = make_product(distributor, sku='INACTIVE-1')
        product.status = ProductStatus.INACTIVE
        product.save()
        formulario = OrderItemForm(vendor=vendor)
        self.assertNotIn(product, formulario.fields['product'].queryset)


class OrderAcceptConcurrencyTest(TransactionTestCase):
    """Genuine multi-threaded regression for the select_for_update() lock.
    SQLite serializes writers at the database-file level (no true row-level
    concurrency), so this proves "no double-spend", not "both threads ran
    in true parallel" — the latter needs Postgres. A thread that hits
    OperationalError (database is locked) is treated as a losing thread,
    not a failure, since that's SQLite's own serialization mechanism."""

    def test_concurrent_accepts_exactly_one_succeeds(self):
        distributor = make_distributor()
        vendor = User.objects.create_user(
            email='cvendor@test.com', password='pass1234', role=Role.VENDOR, distributor=distributor
        )
        owner = User.objects.create_user(
            email='cowner@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=distributor
        )
        from catalog.models import Store
        store = Store.objects.create(name='Tienda', distributor=distributor, owner=owner, vendor=vendor)
        product = make_product(distributor)
        warehouse = Warehouse.objects.create(distributor=distributor, name='Principal')
        StockLevel.objects.create(product=product, warehouse=warehouse, quantity=5)

        orders = []
        for _ in range(2):
            order = Order.objects.create(store=store, vendor=vendor, status=OrderStatus.PENDING)
            OrderItem.objects.create(
                order=order, product=product, warehouse=warehouse,
                quantity=5, unit_price_at_time=product.unit_price,
            )
            orders.append(order)

        def accept(order_id):
            try:
                client = Client()
                client.force_login(vendor)
                client.post(reverse('aceptar_pedido', args=[order_id]))
            except OperationalError:
                pass  # SQLite lock contention — treated as this thread losing
            finally:
                connection.close()

        threads = [threading.Thread(target=accept, args=(o.id,)) for o in orders]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for order in orders:
            order.refresh_from_db()
        accepted_count = sum(1 for o in orders if o.status == OrderStatus.ACCEPTED)
        self.assertEqual(accepted_count, 1)  # exactly one accept wins, never both
        stock = StockLevel.objects.get(product=product, warehouse=warehouse)
        self.assertEqual(stock.quantity, 0)  # only one deduction happened


def _order_setup():
    distributor = make_distributor()
    vendor = User.objects.create_user(
        email='v@t.com', password='x', role=Role.VENDOR, distributor=distributor
    )
    owner = User.objects.create_user(
        email='o@t.com', password='x', role=Role.STORE_OWNER, distributor=distributor
    )
    store = Store.objects.create(name='T', distributor=distributor, owner=owner, vendor=vendor)
    product = make_product(distributor)
    warehouse = Warehouse.objects.create(distributor=distributor, name='Principal')
    return distributor, vendor, owner, store, product, warehouse


class OrderForUserScopingTest(TestCase):
    def setUp(self):
        self.distributor, self.vendor, self.owner, self.store, self.product, self.warehouse = _order_setup()
        self.order = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)

    def test_store_owner_sees_own_orders(self):
        self.assertIn(self.order, Order.objects.for_user(self.owner))

    def test_vendor_sees_assigned_orders(self):
        self.assertIn(self.order, Order.objects.for_user(self.vendor))

    def test_distributor_sees_all_tenant_orders(self):
        admin = User.objects.create_user(
            email='d@t.com', password='x', role=Role.DISTRIBUTOR, distributor=self.distributor
        )
        self.assertIn(self.order, Order.objects.for_user(admin))

    def test_unknown_role_sees_nothing(self):
        stranger = User.objects.create_user(
            email='del@t.com', password='x', role=Role.DELIVERY, distributor=self.distributor
        )
        self.assertEqual(Order.objects.for_user(stranger).count(), 0)

    def test_cross_tenant_isolation(self):
        other = Distributor.objects.create(name='Otra', email='otra@test.com')
        other_owner = User.objects.create_user(
            email='o2@t.com', password='x', role=Role.STORE_OWNER, distributor=other
        )
        self.assertNotIn(self.order, Order.objects.for_user(other_owner))


class OrderAcceptMethodTest(TestCase):
    def setUp(self):
        self.distributor, self.vendor, self.owner, self.store, self.product, self.warehouse = _order_setup()
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=10)
        self.order = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)
        OrderItem.objects.create(
            order=self.order, product=self.product, warehouse=self.warehouse,
            quantity=4, unit_price_at_time=self.product.unit_price,
        )

    def test_accept_deducts_audits_and_notifies(self):
        self.order.accept(self.vendor)
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.ACCEPTED)
        self.assertEqual(self.stock.quantity, 6)
        self.assertTrue(AuditLog.objects.filter(action='order_accepted', entity_id=str(self.order.id)).exists())
        self.assertTrue(Notification.objects.filter(user=self.owner, order=self.order).exists())

    def test_insufficient_stock_raises_and_stays_pending(self):
        self.stock.quantity = 1
        self.stock.save()
        with self.assertRaises(InsufficientStock):
            self.order.accept(self.vendor)
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PENDING)
        self.assertEqual(self.stock.quantity, 1)  # nothing deducted
        # The failure is still audited (persisted outside the rolled-back work).
        self.assertTrue(AuditLog.objects.filter(action='order_accept_failed', entity_id=str(self.order.id)).exists())

    def test_empty_order_raises(self):
        empty = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)
        with self.assertRaises(EmptyOrder):
            empty.accept(self.vendor)


class OrderCreateFromCartTest(TestCase):
    def setUp(self):
        self.distributor, self.vendor, self.owner, self.store, self.product, self.warehouse = _order_setup()
        # T4: Create stock for placement gate
        from catalog.models import StockLevel
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=100)

    def test_create_from_cart_snapshots_current_price(self):
        Discount.objects.create(
            product=self.product, discount_type=DiscountType.PERCENTAGE, discount_value=Decimal('10'),
            start_date=date.today() - timedelta(days=1), end_date=date.today() + timedelta(days=1),
        )
        cart = {'store_id': self.store.id, 'items': [{'product_id': self.product.id, 'quantity': 2}]}
        pedido = Order.objects.create_from_cart(self.store, cart, self.owner)
        self.assertEqual(pedido.status, OrderStatus.PENDING)
        item = pedido.items.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price_at_time, self.product.current_price())  # discounted
        self.assertEqual(item.warehouse, Warehouse.get_or_create_default(self.distributor))
        self.assertTrue(AuditLog.objects.filter(action='order_created', entity_id=str(pedido.id)).exists())

    def test_inactive_product_skipped(self):
        from catalog.models import ProductStatus
        self.product.status = ProductStatus.INACTIVE
        self.product.save()
        cart = {'store_id': self.store.id, 'items': [{'product_id': self.product.id, 'quantity': 1}]}
        pedido = Order.objects.create_from_cart(self.store, cart, self.owner)
        self.assertEqual(pedido.items.count(), 0)


class OrderDashboardMetricsTest(TestCase):
    def setUp(self):
        self.distributor, self.vendor, self.owner, self.store, self.product, self.warehouse = _order_setup()

    def _order(self, status):
        return Order.objects.create(store=self.store, vendor=self.vendor, status=status)

    def test_metrics_counts(self):
        self._order(OrderStatus.CONFIRMED)
        self._order(OrderStatus.CONFIRMED)
        self._order(OrderStatus.REJECTED)
        self._order(OrderStatus.PENDING)
        metricas = Order.objects.for_distributor(self.distributor).dashboard_metrics()
        self.assertEqual(metricas['total'], 4)
        self.assertEqual(metricas['fulfilled'], 2)
        self.assertEqual(metricas['rejected'], 1)

    def test_average_fulfillment_time_none_without_confirmed(self):
        self._order(OrderStatus.PENDING)
        self.assertIsNone(Order.objects.for_distributor(self.distributor).average_fulfillment_time())

    def test_counts_by_status_needs_action_first(self):
        self._order(OrderStatus.CONFIRMED)
        self._order(OrderStatus.PENDING)
        filas = Order.objects.for_distributor(self.distributor).counts_by_status()
        self.assertEqual(filas[0]['status'], OrderStatus.PENDING)  # needs-action sorts first


class CartTest(TestCase):
    def setUp(self):
        self.session = SessionStore()

    def test_add_or_update_appends_then_updates(self):
        cart = Cart(self.session)
        cart.start(1)
        cart.add_or_update(10, 3)
        cart.add_or_update(10, 5)  # same product -> update, not append
        cart.add_or_update(11, 1)
        self.assertEqual(cart.count, 2)
        self.assertEqual(cart.quantity_of(10), 5)
        self.assertEqual(cart.quantity_of(11), 1)

    def test_remove_and_clear(self):
        cart = Cart(self.session)
        cart.start(1)
        cart.add_or_update(10, 2)
        cart.remove(10)
        self.assertEqual(cart.count, 0)
        cart.clear()
        self.assertFalse(cart.exists)

    def test_total_uses_current_price(self):
        distributor = make_distributor()
        product = make_product(distributor, price='7.00')
        cart = Cart(self.session)
        cart.start(1)
        cart.add_or_update(product.id, 3)
        display = cart.display_items()
        self.assertEqual(Cart.total(display), Decimal('21.00'))
