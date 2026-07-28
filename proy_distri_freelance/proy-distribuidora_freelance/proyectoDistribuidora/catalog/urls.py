from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_catalog'),
    path('products/', views.index_productos, name='index_productos'),
    path('inventory/', views.inventario, name='inventario'),
    path('categories/', views.index_categorias, name='index_categorias'),
    path('brands/', views.index_marcas, name='index_marcas'),
    path('stores/new/', views.crear_tienda, name='crear_tienda'),
    path('stores/<int:id>/edit/', views.editar_tienda, name='editar_tienda'),
    path('stores/<int:id>/delete/', views.eliminar_tienda, name='eliminar_tienda'),

    path('categories/new/', views.crear_categoria, name='crear_categoria'),
    path('categories/<int:id>/edit/', views.editar_categoria, name='editar_categoria'),
    path('brands/new/', views.crear_marca, name='crear_marca'),
    path('brands/<int:id>/edit/', views.editar_marca, name='editar_marca'),

    path('products/new/', views.crear_producto, name='crear_producto'),
    path('products/<int:id>/edit/', views.editar_producto, name='editar_producto'),
    path('products/<int:id>/deactivate/', views.eliminar_producto, name='eliminar_producto'),
    path('products/<int:id>/reactivate/', views.reactivar_producto, name='reactivar_producto'),
    path('products/<int:id>/discontinue/', views.descontinuar_producto, name='descontinuar_producto'),
    path('products/<int:product_id>/discount/', views.gestionar_descuento, name='gestionar_descuento'),
    path('products/<int:product_id>/discount/remove/', views.quitar_descuento, name='quitar_descuento'),
    path('products/<int:product_id>/stock/receive/', views.recibir_stock, name='recibir_stock'),
    path('products/<int:product_id>/stock/count/', views.contar_stock, name='contar_stock'),
    path('products/<int:product_id>/stock/adjust/', views.ajustar_stock, name='ajustar_stock'),
    path('products/<int:product_id>/stock/history/', views.historial_stock, name='historial_stock'),
    path('products/import/', views.importar_productos, name='importar_productos'),
    path('stores/map/', views.mapa_tiendas, name='mapa_tiendas'),
    path('my-store/', views.config_mi_tienda, name='config_mi_tienda'),
]
