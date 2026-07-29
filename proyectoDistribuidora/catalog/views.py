from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from accounts.models import Notification, Role, User
from audit.models import AuditLog
from .models import (
    Brand,
    Category,
    Discount,
    Product,
    ProductImage,
    StockLevel,
    StockMovement,
    Store,
    Warehouse,
)
from .exceptions import NegativeStock
from .forms import (
    AjusteForm,
    BrandForm,
    CategoryForm,
    ConteoForm,
    DiscountForm,
    ProductForm,
    ProductImportForm,
    RecibidoForm,
    StoreForm,
    StoreSelfEditForm,
)


def check_low_stock_digest(distributor, actor):
    """Bundled low-stock digest (Tier 4.5, accepted in /plan-ceo-review):
    one Notification per DISTRIBUTOR user summarizing every product
    currently crossing low_stock_threshold, instead of one notification
    per product. Checked on every product/stock save (synchronous,
    request-response — no background job infra in this app)."""
    bajos = list(Product.objects.for_distributor(distributor).active().needs_restock())
    if not bajos:
        return
    nombres = ', '.join(p.name for p in bajos[:10])
    if len(bajos) > 10:
        nombres += f' y {len(bajos) - 10} más'
    mensaje = f'⚠ {len(bajos)} producto(s) con stock bajo: {nombres}'
    from accounts.models import NotificationPreference
    for user in User.objects.filter(distributor=distributor, role=Role.DISTRIBUTOR):
        if NotificationPreference.for_user(user).wants('low_stock_alerts'):
            Notification.objects.create(user=user, order=None, message=mensaje)


@role_required('DISTRIBUTOR')
def index(request):
    return render(request, 'catalog/index.html')


@role_required('DISTRIBUTOR')
def index_productos(request):
    distribuidor = request.user.distributor

    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    stock_status = request.GET.get('stock_status', '')
    only_on_sale = request.GET.get('only_on_sale', '')

    productos = (
        Product.objects.for_distributor(distribuidor)
        .search(q)
        .select_related('category', 'brand')
        .prefetch_related('stock_levels', 'discounts')
    )
    if category_id:
        productos = productos.filter(category_id=category_id)
    if brand_id:
        productos = productos.filter(brand_id=brand_id)

    if stock_status == 'in_stock':
        productos = productos.in_stock()
    elif stock_status == 'low':
        productos = productos.low_stock()
    elif stock_status == 'out':
        productos = productos.out_of_stock()
    if only_on_sale:
        productos = productos.on_sale()

    return render(request, 'catalog/index_productos.html', {
        'productos': productos,
        'categorias': Category.objects.filter(distributor=distribuidor),
        'marcas': Brand.objects.filter(distributor=distribuidor),
        'filtros': {
            'q': q, 'category': category_id, 'brand': brand_id,
            'stock_status': stock_status, 'only_on_sale': only_on_sale,
        },
    })


@role_required('DISTRIBUTOR')
def inventario(request):
    """Stock-centric hub: every product with its current stock, threshold and
    low-stock state, plus the four stock actions per row. Reuses the same search
    + stock-status filters as index_productos, but focused on inventory ops."""
    distribuidor = request.user.distributor

    q = request.GET.get('q', '').strip()
    stock_status = request.GET.get('stock_status', '')

    productos = (
        Product.objects.for_distributor(distribuidor)
        .with_stock()
        .search(q)
        .select_related('category', 'brand')
        .prefetch_related('stock_levels')
    )
    if stock_status == 'in_stock':
        productos = productos.in_stock()
    elif stock_status == 'low':
        productos = productos.low_stock()
    elif stock_status == 'out':
        productos = productos.out_of_stock()

    return render(request, 'catalog/inventario.html', {
        'productos': productos,
        'filtros': {'q': q, 'stock_status': stock_status},
    })


@role_required('DISTRIBUTOR')
def index_categorias(request):
    categorias = Category.objects.filter(distributor=request.user.distributor)
    return render(request, 'catalog/index_categorias.html', {'categorias': categorias})


@role_required('DISTRIBUTOR')
def index_marcas(request):
    marcas = Brand.objects.filter(distributor=request.user.distributor)
    return render(request, 'catalog/index_marcas.html', {'marcas': marcas})


# --- Store ---

@role_required('DISTRIBUTOR')
def crear_tienda(request):
    if request.method == 'POST':
        formulario = StoreForm(request.POST, distributor=request.user.distributor)
        if formulario.is_valid():
            tienda = formulario.save(commit=False)
            tienda.distributor = request.user.distributor
            tienda.save()
            return redirect('index_accounts')
    else:
        formulario = StoreForm(distributor=request.user.distributor)
    return render(request, 'catalog/crear_tienda.html', {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_tienda(request, id):
    tienda = get_object_or_404(Store, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = StoreForm(request.POST, instance=tienda, distributor=request.user.distributor)
        if formulario.is_valid():
            formulario.save()
            return redirect('index_accounts')
    else:
        formulario = StoreForm(instance=tienda, distributor=request.user.distributor)
    return render(request, 'catalog/editar_tienda.html', {
        'formulario': formulario,
        'tienda': tienda,
    })


@role_required('DISTRIBUTOR')
def eliminar_tienda(request, id):
    tienda = get_object_or_404(Store, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        nombre = tienda.name
        tienda_id = tienda.id
        pedidos_afectados = tienda.orders.count()
        tienda.delete()
        AuditLog.objects.create(
            user=request.user,
            action='store_deleted',
            entity_type='Store',
            entity_id=str(tienda_id),
            details={'name': nombre, 'pedidos_afectados': pedidos_afectados},
        )
        messages.success(request, f'Tienda "{nombre}" eliminada.')
    return redirect('index_accounts')


# --- Category ---

@role_required('DISTRIBUTOR')
def crear_categoria(request):
    is_popup = 'popup' in request.GET or 'popup' in request.POST
    if request.method == 'POST':
        formulario = CategoryForm(request.POST)
        if formulario.is_valid():
            categoria = formulario.save(commit=False)
            categoria.distributor = request.user.distributor
            categoria.save()
            if is_popup:
                return render(request, 'catalog/popup_creado.html', {
                    'obj_id': categoria.id,
                    'obj_name': categoria.name,
                    'callback': 'refreshCategorySelect',
                })
            return redirect('index_categorias')
    else:
        formulario = CategoryForm()
    template = 'catalog/crear_categoria_popup.html' if is_popup else 'catalog/crear_categoria.html'
    return render(request, template, {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_categoria(request, id):
    categoria = get_object_or_404(Category, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = CategoryForm(request.POST, instance=categoria)
        if formulario.is_valid():
            formulario.save()
            return redirect('index_categorias')
    else:
        formulario = CategoryForm(instance=categoria)
    return render(request, 'catalog/editar_categoria.html', {
        'formulario': formulario, 'categoria': categoria,
    })


# --- Brand ---

@role_required('DISTRIBUTOR')
def crear_marca(request):
    is_popup = 'popup' in request.GET or 'popup' in request.POST
    if request.method == 'POST':
        formulario = BrandForm(request.POST)
        if formulario.is_valid():
            marca = formulario.save(commit=False)
            marca.distributor = request.user.distributor
            marca.save()
            if is_popup:
                return render(request, 'catalog/popup_creado.html', {
                    'obj_id': marca.id,
                    'obj_name': marca.name,
                    'callback': 'refreshBrandSelect',
                })
            return redirect('index_marcas')
    else:
        formulario = BrandForm()
    template = 'catalog/crear_marca_popup.html' if is_popup else 'catalog/crear_marca.html'
    return render(request, template, {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_marca(request, id):
    marca = get_object_or_404(Brand, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = BrandForm(request.POST, instance=marca)
        if formulario.is_valid():
            formulario.save()
            return redirect('index_marcas')
    else:
        formulario = BrandForm(instance=marca)
    return render(request, 'catalog/editar_marca.html', {
        'formulario': formulario, 'marca': marca,
    })


# --- Product ---

def _save_product_images(producto, formulario, request):
    main_image = formulario.cleaned_data.get('main_image')
    if main_image:
        ProductImage.objects.filter(product=producto, is_main=True).delete()
        ProductImage.objects.create(product=producto, image=main_image, is_main=True)
    for f in request.FILES.getlist('additional_images'):
        ProductImage.objects.create(product=producto, image=f, is_main=False)



@role_required('DISTRIBUTOR')
def crear_producto(request):
    distribuidor = request.user.distributor
    if request.method == 'POST':
        formulario = ProductForm(request.POST, request.FILES, distributor=distribuidor)
        if formulario.is_valid():
            producto = formulario.save(commit=False)
            producto.distributor = distribuidor
            producto.save()
            _save_product_images(producto, formulario, request)
            AuditLog.objects.create(
                user=request.user,
                action='product_created',
                entity_type='Product',
                entity_id=str(producto.id),
                details={'name': producto.name, 'sku': producto.sku},
            )
            check_low_stock_digest(distribuidor, request.user)
            return redirect('index_productos')
    else:
        formulario = ProductForm(distributor=distribuidor)
    return render(request, 'catalog/crear_producto.html', {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_producto(request, id):
    distribuidor = request.user.distributor
    producto = get_object_or_404(Product, id=id, distributor=distribuidor)
    if request.method == 'POST':
        formulario = ProductForm(
            request.POST, request.FILES, instance=producto, distributor=distribuidor
        )
        if formulario.is_valid():
            formulario.save()
            _save_product_images(producto, formulario, request)
            AuditLog.objects.create(
                user=request.user,
                action='product_updated',
                entity_type='Product',
                entity_id=str(producto.id),
                details={'name': producto.name, 'sku': producto.sku},
            )
            check_low_stock_digest(distribuidor, request.user)
            return redirect('index_productos')
    else:
        formulario = ProductForm(instance=producto, distributor=distribuidor)
    return render(request, 'catalog/editar_producto.html', {
        'formulario': formulario,
        'producto': producto,
    })


@role_required('DISTRIBUTOR')
def eliminar_producto(request, id):
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.deactivate(request.user)
    return redirect('index_productos')


@role_required('DISTRIBUTOR')
def reactivar_producto(request, id):
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.reactivate(request.user)
    return redirect('index_productos')


@role_required('DISTRIBUTOR')
def descontinuar_producto(request, id):
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.discontinue(request.user)
    return redirect('index_productos')


# --- Discount ---

@role_required('DISTRIBUTOR')
def gestionar_descuento(request, product_id):
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    descuento = producto.current_or_latest_discount()
    if request.method == 'POST':
        instance = descuento if descuento and descuento.pk else None
        formulario = DiscountForm(request.POST, instance=instance)
        if formulario.is_valid():
            nuevo = formulario.save(commit=False)
            nuevo.product = producto
            nuevo.full_clean()
            nuevo.save()
            return redirect('editar_producto', id=producto.id)
    else:
        formulario = DiscountForm(instance=descuento)
    return render(request, 'catalog/gestionar_descuento.html', {
        'formulario': formulario,
        'producto': producto,
    })


@role_required('DISTRIBUTOR')
def quitar_descuento(request, product_id):
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    if request.method == 'POST':
        Discount.objects.filter(product=producto).delete()
    return redirect('editar_producto', id=producto.id)


# --- Stock (T5 actions: recibir/contar/ajustar + historial) ---

@role_required('DISTRIBUTOR')
def recibir_stock(request, product_id):
    """Receive stock: add N units with optional note."""
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    warehouse = Warehouse.get_or_create_default(request.user.distributor)
    stock, _ = StockLevel.objects.get_or_create(product=producto, warehouse=warehouse)

    if request.method == 'POST':
        formulario = RecibidoForm(request.POST)
        if formulario.is_valid():
            try:
                stock.receive(
                    amount=formulario.cleaned_data['cantidad'],
                    actor=request.user,
                    note=formulario.cleaned_data.get('nota', ''),
                )
                check_low_stock_digest(request.user.distributor, request.user)
                return redirect('index_productos')
            except NegativeStock as e:
                formulario.add_error(None, str(e))
    else:
        formulario = RecibidoForm()

    return render(request, 'catalog/recibir_stock.html', {
        'formulario': formulario,
        'producto': producto,
        'stock': stock,
    })


@role_required('DISTRIBUTOR')
def contar_stock(request, product_id):
    """Physical count: set absolute quantity, derive delta."""
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    warehouse = Warehouse.get_or_create_default(request.user.distributor)
    stock, _ = StockLevel.objects.get_or_create(product=producto, warehouse=warehouse)

    if request.method == 'POST':
        formulario = ConteoForm(request.POST)
        if formulario.is_valid():
            try:
                stock.contar(
                    counted=formulario.cleaned_data['cantidad'],
                    actor=request.user,
                    note=formulario.cleaned_data.get('nota', ''),
                )
                check_low_stock_digest(request.user.distributor, request.user)
                return redirect('index_productos')
            except NegativeStock as e:
                formulario.add_error(None, str(e))
    else:
        formulario = ConteoForm()

    return render(request, 'catalog/contar_stock.html', {
        'formulario': formulario,
        'producto': producto,
        'stock': stock,
    })


@role_required('DISTRIBUTOR')
def ajustar_stock(request, product_id):
    """Adjustment: signed delta with mandatory note."""
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    warehouse = Warehouse.get_or_create_default(request.user.distributor)
    stock, _ = StockLevel.objects.get_or_create(product=producto, warehouse=warehouse)

    if request.method == 'POST':
        formulario = AjusteForm(request.POST)
        if formulario.is_valid():
            try:
                stock.ajustar(
                    delta=formulario.cleaned_data['delta'],
                    actor=request.user,
                    note=formulario.cleaned_data['nota'],
                )
                check_low_stock_digest(request.user.distributor, request.user)
                return redirect('index_productos')
            except NegativeStock as e:
                formulario.add_error(None, str(e))
    else:
        formulario = AjusteForm()

    return render(request, 'catalog/ajustar_stock.html', {
        'formulario': formulario,
        'producto': producto,
        'stock': stock,
    })


@role_required('DISTRIBUTOR')
def historial_stock(request, product_id):
    """Stock movement history timeline for a product."""
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    warehouse = Warehouse.get_or_create_default(request.user.distributor)

    # Use T8 for_product manager method for distributor-scoped ledger
    movimientos = StockMovement.objects.for_product(
        producto,
        distributor=request.user.distributor
    ).filter(warehouse=warehouse)

    return render(request, 'catalog/historial_stock.html', {
        'producto': producto,
        'movimientos': movimientos,
    })


# --- CSV Import ---

@role_required('DISTRIBUTOR')
def importar_productos(request):
    if request.method == 'POST':
        formulario = ProductImportForm(request.POST, request.FILES)
        if formulario.is_valid():
            distribuidor = request.user.distributor
            importados, errores = Product.objects.import_from_csv(
                distribuidor, formulario.cleaned_data['archivo_csv']
            )
            if importados:
                AuditLog.objects.create(
                    user=request.user,
                    action='product_csv_import',
                    entity_type='Product',
                    entity_id='',
                    details={'imported': importados, 'errors': len(errores)},
                )
                check_low_stock_digest(distribuidor, request.user)
            return render(request, 'catalog/importar_productos_resultado.html', {
                'importados': importados, 'errores': errores,
            })
    else:
        formulario = ProductImportForm()
    return render(request, 'catalog/importar_productos.html', {'formulario': formulario})


@role_required('STORE_OWNER')
def config_mi_tienda(request):
    """STORE_OWNER self-edits their own store (Configuración → Mi tienda).
    Self-scoped: loads the store by owner, and StoreSelfEditForm exposes only
    the owner-controlled fields (never owner/vendor/distributor)."""
    tienda = Store.objects.filter(owner=request.user).first()
    formulario = None
    if tienda is not None:
        if request.method == 'POST':
            formulario = StoreSelfEditForm(request.POST, instance=tienda)
            if formulario.is_valid():
                formulario.save()
                AuditLog.objects.create(
                    user=request.user, action='store_self_updated',
                    entity_type='Store', entity_id=str(tienda.id),
                )
                messages.success(request, 'Datos de tu tienda actualizados.')
                return redirect('config_mi_tienda')
        else:
            formulario = StoreSelfEditForm(instance=tienda)
    return render(request, 'catalog/mi_tienda.html', {'tienda': tienda, 'formulario': formulario})


@role_required('DISTRIBUTOR')
def mapa_tiendas(request):
    import json
    distribuidor = request.user.distributor
    tiendas = Store.objects.for_distributor(distribuidor)
    markers = [t.as_marker() for t in tiendas.with_coordinates()]
    return render(request, 'catalog/mapa_tiendas.html', {
        'markers_json': json.dumps(markers),
        'sin_coords': tiendas.without_coordinates(),
        'distribuidor': distribuidor,
    })
