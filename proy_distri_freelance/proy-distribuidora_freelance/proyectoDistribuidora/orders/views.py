from django.contrib import messages
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from catalog.models import Category, Product, ProductImage, ProductStatus, Store
from .cart import Cart
from .exceptions import EmptyOrder, InsufficientStock
from .models import Order, OrderItem, OrderStatus
from .forms import OrderForm, OrderItemForm, ReportarIncidenciaForm, ResolverIncidenciaForm


def _ensure_cart(request, product_id, quantity):
    """Return (Cart, None) with a ready cart, or (None, response) when the
    caller must render/redirect instead (no orderable store, or a store picker
    is needed)."""
    cart = Cart(request.session)
    if cart.exists:
        return cart, None

    stores = list(Store.objects.orderable_for(request.user))
    if not stores:
        messages.error(request, 'No tienes tiendas con vendedor asignado. Contacta al distribuidor.')
        return None, redirect('explorar_productos')
    if len(stores) == 1:
        cart.start(stores[0].id)
        return cart, None

    store_id = request.POST.get('store_id')
    if not store_id:
        return None, render(request, 'orders/seleccionar_tienda.html', {
            'stores': stores,
            'product_id': product_id,
            'quantity': quantity,
        })
    try:
        store = next(s for s in stores if str(s.id) == store_id)
    except StopIteration:
        messages.error(request, 'Tienda no válida.')
        return None, redirect('explorar_productos')
    cart.start(store.id)
    return cart, None


@role_required('STORE_OWNER', 'VENDOR', 'DISTRIBUTOR')
def index(request):
    contexto = {'pedidos': Order.objects.for_user(request.user).with_related()}
    if request.user.role == 'VENDOR':
        # Vendor new-order polling cadence/mute (Configuración → Alertas).
        from accounts.models import NotificationPreference
        prefs = NotificationPreference.for_user(request.user)
        contexto['polling_enabled'] = prefs.new_order_alerts
        contexto['poll_interval_ms'] = max(10, prefs.poll_interval_seconds) * 1000
    return render(request, 'orders/index.html', contexto)


@role_required('STORE_OWNER')
def iniciar_carrito(request):
    if request.method == 'POST':
        formulario = OrderForm(request.POST, owner=request.user)
        if formulario.is_valid():
            store = formulario.cleaned_data['store']
            if not store.vendor:
                formulario.add_error(
                    'store',
                    'Esta tienda no tiene un vendedor asignado. Contacta al distribuidor.'
                )
            else:
                Cart(request.session).start(store.id)
                return redirect('carrito')
    else:
        formulario = OrderForm(owner=request.user)
    return render(request, 'orders/iniciar_carrito.html', {'formulario': formulario})


@role_required('STORE_OWNER')
def carrito(request):
    cart = Cart(request.session)
    if not cart.exists:
        return redirect('explorar_productos')
    store = get_object_or_404(
        Store.objects.select_related('vendor', 'distributor'),
        pk=cart.store_id, owner=request.user,
    )

    if request.method == 'POST':
        if 'add' in request.POST:
            formulario = OrderItemForm(request.POST, vendor=store.vendor)
            if formulario.is_valid():
                cart.add_or_update(
                    formulario.cleaned_data['product'].id,
                    formulario.cleaned_data['quantity'],
                )
                return redirect('carrito')
            # fall through to re-render with form errors
        else:
            # Single cart form: always apply qty edits first, then branch on button.
            cart.apply_quantity_edits(request.POST)

            if 'confirm' in request.POST:
                return redirect('confirmar_carrito')
            elif 'discard' in request.POST:
                cart.clear()
                return redirect('index_orders')
            elif 'remove' in request.POST:
                try:
                    product_id = int(request.POST['remove'])
                except (ValueError, TypeError):
                    product_id = 0
                cart.remove(product_id)
                return redirect('carrito')

    display_items = cart.display_items()
    return render(request, 'orders/carrito.html', {
        'store': store,
        'display_items': display_items,
        'cart_total': Cart.total(display_items),
    })


@role_required('STORE_OWNER')
def confirmar_carrito(request):
    cart = Cart(request.session)
    if not cart.exists or not cart.items:
        return redirect('carrito')
    store = get_object_or_404(
        Store.objects.select_related('vendor', 'distributor'),
        pk=cart.store_id, owner=request.user,
    )

    if request.method == 'POST':
        try:
            pedido = Order.objects.create_from_cart(store, cart.data, request.user)
        except InsufficientStock as error:
            # D6 placement gate: one or more lines exceed on-hand stock. Keep the
            # cart intact and re-render this step with the per-line errors so the
            # owner can go back and adjust quantities.
            display_items = cart.display_items()
            return render(request, 'orders/confirmar_carrito.html', {
                'store': store,
                'display_items': display_items,
                'cart_total': Cart.total(display_items),
                'errores': error.errors,
            })
        cart.clear()
        return redirect('ver_pedido', id=pedido.id)

    display_items = cart.display_items()
    return render(request, 'orders/confirmar_carrito.html', {
        'store': store,
        'display_items': display_items,
        'cart_total': Cart.total(display_items),
    })


@role_required('STORE_OWNER')
def explorar_productos(request):
    distributor = request.user.distributor

    if request.method == 'POST':
        try:
            product_id = int(request.POST.get('product_id', 0))
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (ValueError, TypeError):
            return redirect('explorar_productos')

        cart, response = _ensure_cart(request, product_id, quantity)
        if response is not None:
            return response

        try:
            product = Product.objects.get(
                id=product_id, distributor=distributor, status=ProductStatus.ACTIVE,
            )
        except Product.DoesNotExist:
            return redirect('explorar_productos')

        cart.add_or_update(product.id, quantity)
        return redirect('explorar_productos')

    # GET
    products_qs = (
        Product.objects.for_distributor(distributor).active()
        .search(request.GET.get('q', ''))
        .select_related('category', 'brand')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_main=True), to_attr='main_images')
        )
        .order_by('name')
    )
    q = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    if categoria_id:
        products_qs = products_qs.filter(category_id=categoria_id)

    categorias = Category.objects.filter(distributor=distributor).order_by('name')
    cart = Cart(request.session)
    cart_map = cart.cart_map()
    store = Store.objects.filter(pk=cart.store_id, owner=request.user).first() if cart.exists else None

    display_products = []
    for product in products_qs:
        display_products.append({
            'product': product,
            'price': product.current_price(),
            'stock': product.total_stock(),
            'in_cart': cart_map.get(product.id, 0),
            'main_image': product.main_images[0] if product.main_images else None,
        })

    return render(request, 'orders/explorar_productos.html', {
        'display_products': display_products,
        'categorias': categorias,
        'q': q,
        'categoria_id': categoria_id,
        'cart_count': cart.count,
        'store': store,
    })


@role_required('STORE_OWNER')
def ver_producto_orden(request, id):
    distributor = request.user.distributor
    product = get_object_or_404(
        Product.objects.filter(distributor=distributor, status=ProductStatus.ACTIVE)
        .select_related('category', 'brand')
        .prefetch_related('images', 'stock_levels__warehouse'),
        pk=id,
    )
    cart = Cart(request.session)

    if request.method == 'POST':
        try:
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (ValueError, TypeError):
            quantity = 1

        cart, response = _ensure_cart(request, product.id, quantity)
        if response is not None:
            return response

        cart.add_or_update(product.id, quantity)
        return redirect('explorar_productos')

    return render(request, 'orders/ver_producto_orden.html', {
        'product': product,
        'price': product.current_price(),
        'stock': product.total_stock(),
        'stock_levels': product.stock_levels.select_related('warehouse').all(),
        'images': product.images.all(),
        'in_cart': cart.quantity_of(product.id),
        'cart_count': cart.count,
    })


@role_required('STORE_OWNER', 'VENDOR', 'DISTRIBUTOR')
def ver_pedido(request, id):
    pedido = get_object_or_404(Order.objects.for_user(request.user).with_related(), id=id)
    return render(request, 'orders/ver_pedido.html', {
        'pedido': pedido,
        'items': pedido.items.select_related('product').all(),
    })


@role_required('STORE_OWNER')
def cancelar_pedido(request, id):
    """US-23: a store owner may withdraw an order only while it's still
    PENDING — once a vendor has acted on it, only they can reject it."""
    pedido = get_object_or_404(
        Order, id=id, store__owner=request.user, status=OrderStatus.PENDING
    )
    if request.method == 'POST':
        pedido.cancel(request.user)
        messages.success(request, 'Pedido cancelado.')
    return redirect('ver_pedido', id=id)


@role_required('STORE_OWNER')
def crear_item_pedido(request, order_id):
    pedido = get_object_or_404(
        Order, id=order_id, store__owner=request.user, status=OrderStatus.PENDING
    )
    if request.method == 'POST':
        formulario = OrderItemForm(request.POST, vendor=pedido.vendor)
        if formulario.is_valid():
            item = formulario.save(commit=False)
            item.order = pedido
            item.snapshot()
            item.save()
            return redirect('ver_pedido', id=order_id)
    else:
        formulario = OrderItemForm(vendor=pedido.vendor)
    return render(request, 'orders/crear_item_pedido.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


@role_required('STORE_OWNER')
def editar_item_pedido(request, id):
    item = get_object_or_404(
        OrderItem, id=id, order__store__owner=request.user, order__status=OrderStatus.PENDING
    )
    if request.method == 'POST':
        formulario = OrderItemForm(request.POST, instance=item, vendor=item.order.vendor)
        if formulario.is_valid():
            item = formulario.save(commit=False)
            item.snapshot()
            item.save()
            return redirect('ver_pedido', id=item.order.id)
    else:
        formulario = OrderItemForm(instance=item, vendor=item.order.vendor)
    return render(request, 'orders/editar_item_pedido.html', {
        'formulario': formulario,
        'item': item,
    })


@role_required('STORE_OWNER')
def eliminar_item_pedido(request, id):
    item = get_object_or_404(
        OrderItem, id=id, order__store__owner=request.user, order__status=OrderStatus.PENDING
    )
    order_id = item.order.id
    item.delete()
    return redirect('ver_pedido', id=order_id)


# --- Vendor state-machine transitions (UC-11, UC-12, UC-13) ---

@role_required('VENDOR')
def aceptar_pedido(request, id):
    pedido = get_object_or_404(Order, id=id, vendor=request.user, status=OrderStatus.PENDING)
    if request.method == 'POST':
        try:
            pedido.accept(request.user)
        except EmptyOrder as error:
            messages.error(request, str(error))
            return redirect('ver_pedido', id=id)
        except InsufficientStock as error:
            for mensaje in error.errors:
                messages.error(request, mensaje)
            return redirect('ver_pedido', id=id)
        messages.success(request, 'Pedido aceptado — inventario actualizado.')
    return redirect('ver_pedido', id=id)


@role_required('VENDOR')
def rechazar_pedido(request, id):
    pedido = get_object_or_404(Order, id=id, vendor=request.user, status=OrderStatus.PENDING)
    if request.method == 'POST':
        pedido.reject(request.user, request.POST.get('rejection_reason', ''))
        messages.success(request, 'Pedido rechazado.')
        return redirect('ver_pedido', id=id)
    return render(request, 'orders/rechazar_pedido.html', {'pedido': pedido})


@role_required('VENDOR')
def despachar_pedido(request, id):
    pedido = get_object_or_404(Order, id=id, vendor=request.user, status=OrderStatus.ACCEPTED)
    if request.method == 'POST':
        pedido.dispatch(request.user)
        messages.success(request, 'Pedido marcado como despachado.')
    return redirect('ver_pedido', id=id)


# --- Post-delivery confirmation / dispute (DR-09) ---

@role_required('STORE_OWNER')
def confirmar_recepcion(request, id):
    pedido = get_object_or_404(
        Order, id=id, store__owner=request.user, status=OrderStatus.DELIVERED
    )
    if request.method == 'POST':
        pedido.confirm_receipt(request.user)
        messages.success(request, 'Recepción confirmada.')
    return redirect('ver_pedido', id=id)


@role_required('STORE_OWNER')
def reportar_incidencia(request, id):
    pedido = get_object_or_404(
        Order, id=id, store__owner=request.user, status=OrderStatus.DELIVERED
    )
    if request.method == 'POST':
        formulario = ReportarIncidenciaForm(request.POST, instance=pedido)
        if formulario.is_valid():
            formulario.save(commit=False)  # populate issue_description onto pedido
            pedido.report_issue(request.user)
            messages.success(request, 'Incidencia reportada.')
            return redirect('ver_pedido', id=id)
    else:
        formulario = ReportarIncidenciaForm(instance=pedido)
    return render(request, 'orders/reportar_incidencia.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


@role_required('VENDOR', 'DISTRIBUTOR')
def resolver_incidencia(request, id):
    pedido = get_object_or_404(
        Order.objects.for_user(request.user).filter(status=OrderStatus.DELIVERY_ISSUE),
        id=id,
    )
    if request.method == 'POST':
        formulario = ResolverIncidenciaForm(request.POST, instance=pedido)
        if formulario.is_valid():
            formulario.save(commit=False)  # populate resolution_notes onto pedido
            pedido.resolve_issue(request.user)
            messages.success(request, 'Incidencia resuelta.')
            return redirect('ver_pedido', id=id)
    else:
        formulario = ResolverIncidenciaForm(instance=pedido)
    return render(request, 'orders/resolver_incidencia.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


# --- JSON polling endpoint — vendor dashboard, 30s interval (FR-06.6, FR-10.1) ---

@role_required('VENDOR')
def pending_orders_api(request):
    pedidos = Order.objects.pending_for_vendor(request.user)
    return JsonResponse({
        'orders': [
            {
                'id': p.id,
                'store': p.store.name,
                'created_at': p.created_at.isoformat(),
                'item_count': p.item_count,
                'url': f'/orders/{p.id}/',
            }
            for p in pedidos
        ],
    })
