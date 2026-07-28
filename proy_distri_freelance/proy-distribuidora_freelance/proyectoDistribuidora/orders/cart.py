"""Session-backed shopping cart for the browse-first store-owner flow.

The cart lives in `request.session['cart']` as {'store_id': int, 'items':
[{'product_id': int, 'quantity': int}, ...]} — HTTP session state, not ORM
data, so it belongs here rather than in a model. This wrapper centralizes the
item upsert loop and the display-items/total computation that were duplicated
across the browse, product-detail, and cart views.
"""


class Cart:
    def __init__(self, session):
        self.session = session
        self.data = session.get('cart')

    # --- state ---

    @property
    def exists(self):
        return bool(self.data)

    @property
    def store_id(self):
        return self.data['store_id'] if self.data else None

    @property
    def items(self):
        return self.data['items'] if self.data else []

    @property
    def count(self):
        return len(self.items)

    def start(self, store_id):
        """Begin a fresh cart for the given store, replacing any existing one."""
        self.data = {'store_id': store_id, 'items': []}
        self.session['cart'] = self.data

    def clear(self):
        if 'cart' in self.session:
            del self.session['cart']
        self.data = None

    # --- items ---

    def quantity_of(self, product_id):
        for item in self.items:
            if item['product_id'] == product_id:
                return item['quantity']
        return 0

    def add_or_update(self, product_id, quantity):
        """Set the quantity for a product, appending it if not already present."""
        for item in self.data['items']:
            if item['product_id'] == product_id:
                item['quantity'] = quantity
                break
        else:
            self.data['items'].append({'product_id': product_id, 'quantity': quantity})
        self.session.modified = True

    def apply_quantity_edits(self, post_data):
        """Read `qty_<product_id>` fields from a submitted form and update each
        line, clamping to a minimum of 1 and ignoring malformed values."""
        for item in self.items:
            key = f"qty_{item['product_id']}"
            if key in post_data:
                try:
                    item['quantity'] = max(1, int(post_data[key]))
                except (ValueError, TypeError):
                    pass
        self.session.modified = True

    def remove(self, product_id):
        self.data['items'] = [i for i in self.items if i['product_id'] != product_id]
        self.session.modified = True

    def cart_map(self):
        """{product_id: quantity} for marking in-cart state on listing pages."""
        return {item['product_id']: item['quantity'] for item in self.items}

    # --- pricing ---

    def display_items(self):
        """Resolve cart lines to {product, quantity, unit_price, subtotal,
        main_image} dicts, using the product's current (discount-aware) price.
        The main image is prefetched (one query, not one per line) so the cart
        page can show a thumbnail. Products that no longer exist are skipped."""
        from django.db.models import Prefetch
        from catalog.models import Product, ProductImage
        product_ids = [i['product_id'] for i in self.items]
        products = {
            p.id: p
            for p in Product.objects.filter(id__in=product_ids).prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_main=True), to_attr='main_images')
            )
        }
        display = []
        for i in self.items:
            product = products.get(i['product_id'])
            if product is None:
                continue
            price = product.current_price()
            display.append({
                'product': product,
                'quantity': i['quantity'],
                'unit_price': price,
                'subtotal': price * i['quantity'],
                'main_image': product.main_images[0] if product.main_images else None,
            })
        return display

    @staticmethod
    def total(display_items):
        return sum(item['subtotal'] for item in display_items)
