from django.urls import path
from . import views

urlpatterns = [
    path('queue/', views.index, name='index_deliveries'),
    path('new/confirm/', views.crear_confirmacion, name='crear_confirmacion'),
    path('orders/<int:order_id>/', views.ver_pedido_entrega, name='ver_pedido_entrega'),
    path('orders/<int:order_id>/confirm/', views.confirmar_entrega, name='confirmar_entrega'),
    path('<int:id>/edit/', views.editar_confirmacion, name='editar_confirmacion'),
    path('<int:id>/delete/', views.eliminar_confirmacion, name='eliminar_confirmacion'),
]
