from decimal import Decimal

from django.test import TestCase

from accounts.models import Distributor, Notification, Role, User
from audit.models import AuditLog
from catalog.models import Brand, Category, Product, Store, UnitOfMeasure, Warehouse
from orders.models import Order, OrderItem, OrderStatus
from .exceptions import DeliveryAlreadyConfirmed
from .models import DeliveryConfirmation


def _setup():
    distributor = Distributor.objects.create(name='D', email='d@t.com')
    vendor = User.objects.create_user(email='v@t.com', password='x', role=Role.VENDOR, distributor=distributor)
    owner = User.objects.create_user(email='o@t.com', password='x', role=Role.STORE_OWNER, distributor=distributor)
    delivery = User.objects.create_user(email='r@t.com', password='x', role=Role.DELIVERY, distributor=distributor)
    store = Store.objects.create(name='T', distributor=distributor, owner=owner, vendor=vendor)
    category = Category.objects.create(distributor=distributor, name='Gen')
    brand = Brand.objects.create(distributor=distributor, name='M')
    product = Product.objects.create(
        distributor=distributor, name='P', sku='S1', category=category, brand=brand,
        unit_price=Decimal('10.00'), unit_of_measure=UnitOfMeasure.PIECE,
    )
    warehouse = Warehouse.objects.create(distributor=distributor, name='Principal')
    order = Order.objects.create(store=store, vendor=vendor, status=OrderStatus.DISPATCHED)
    OrderItem.objects.create(order=order, product=product, warehouse=warehouse, quantity=2, unit_price_at_time=Decimal('10.00'))
    return distributor, vendor, owner, delivery, store, order


class DeliveryConfirmTest(TestCase):
    def setUp(self):
        (self.distributor, self.vendor, self.owner,
         self.delivery, self.store, self.order) = _setup()

    def test_confirm_transitions_audits_and_notifies(self):
        confirmacion = DeliveryConfirmation.objects.confirm(
            self.order.id, self.distributor, self.delivery
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.DELIVERED)
        self.assertEqual(confirmacion.delivery_user, self.delivery)
        self.assertTrue(AuditLog.objects.filter(action='order_delivered', entity_id=str(self.order.id)).exists())
        self.assertTrue(Notification.objects.filter(user=self.owner, order=self.order).exists())

    def test_race_confirm_raises_already_confirmed(self):
        # Simulate the race: a confirmation already exists while the order is
        # still DISPATCHED (both deliverers passed the status guard). The
        # second create hits the OneToOne uniqueness → DeliveryAlreadyConfirmed.
        other = User.objects.create_user(
            email='r2@t.com', password='x', role=Role.DELIVERY, distributor=self.distributor
        )
        DeliveryConfirmation.objects.create(order=self.order, delivery_user=other)
        with self.assertRaises(DeliveryAlreadyConfirmed):
            DeliveryConfirmation.objects.confirm(self.order.id, self.distributor, self.delivery)
        self.assertEqual(DeliveryConfirmation.objects.filter(order=self.order).count(), 1)

    def test_confirm_rejects_non_dispatched_order(self):
        self.order.status = OrderStatus.PENDING
        self.order.save()
        with self.assertRaises(Order.DoesNotExist):
            DeliveryConfirmation.objects.confirm(self.order.id, self.distributor, self.delivery)

    def test_recent_for_distributor_scopes_and_limits(self):
        DeliveryConfirmation.objects.confirm(self.order.id, self.distributor, self.delivery)
        historial = DeliveryConfirmation.objects.recent_for_distributor(self.distributor)
        self.assertEqual(historial.count(), 1)
