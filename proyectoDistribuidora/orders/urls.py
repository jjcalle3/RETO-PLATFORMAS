from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_orders'),
    path('new/', views.iniciar_carrito, name='crear_pedido'),
    path('carrito/', views.carrito, name='carrito'),
    path('carrito/confirmar/', views.confirmar_carrito, name='confirmar_carrito'),
    path('items/<int:id>/edit/', views.editar_item_pedido, name='editar_item_pedido'),
    path('items/<int:id>/delete/', views.eliminar_item_pedido, name='eliminar_item_pedido'),
    path('browse/', views.explorar_productos, name='explorar_productos'),
    path('products/<int:id>/', views.ver_producto_orden, name='ver_producto_orden'),
    path('<int:id>/', views.ver_pedido, name='ver_pedido'),
    path('<int:id>/cancel/', views.cancelar_pedido, name='cancelar_pedido'),
    path('<int:id>/accept/', views.aceptar_pedido, name='aceptar_pedido'),
    path('<int:id>/reject/', views.rechazar_pedido, name='rechazar_pedido'),
    path('<int:id>/dispatch/', views.despachar_pedido, name='despachar_pedido'),
    path('<int:id>/confirm-receipt/', views.confirmar_recepcion, name='confirmar_recepcion'),
    path('<int:id>/report-issue/', views.reportar_incidencia, name='reportar_incidencia'),
    path('<int:id>/resolve-issue/', views.resolver_incidencia, name='resolver_incidencia'),
    path('<int:order_id>/items/new/', views.crear_item_pedido, name='crear_item_pedido'),
]
