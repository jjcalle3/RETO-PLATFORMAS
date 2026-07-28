from django.urls import path
from . import views

urlpatterns = [
    # Operator panel — platform-level, @superuser_required on each view
    path('admin-panel/', views.operator_dashboard, name='operator_dashboard'),
    path('admin-panel/distributors/<int:id>/', views.operator_tenant_detail, name='operator_tenant_detail'),
    path('admin-panel/distributors/<int:id>/activate/', views.operator_activate_tenant, name='operator_activate_tenant'),
    path('admin-panel/distributors/<int:id>/suspend/', views.operator_suspend_tenant, name='operator_suspend_tenant'),

    path('config/', views.configuracion, name='configuracion'),
    path('dashboard/', views.dashboard, name='distributor_dashboard'),
    path('users/', views.index, name='index_accounts'),
    path('distributors/<int:id>/', views.obtener_distribuidor, name='obtener_distribuidor'),
    path('distributors/new/', views.crear_distribuidor, name='crear_distribuidor'),
    path('distributors/<int:id>/edit/', views.editar_distribuidor, name='editar_distribuidor'),
    path('distributors/<int:id>/delete/', views.eliminar_distribuidor, name='eliminar_distribuidor'),
    path('users/new/<str:role>/', views.crear_usuario, name='crear_usuario'),
    path('users/<int:id>/edit/', views.editar_usuario, name='editar_usuario'),
    path('users/<int:id>/delete/', views.eliminar_usuario, name='eliminar_usuario'),
    path('password-reset/', views.solicitar_reset_password, name='solicitar_reset_password'),
    path('password-reset/<str:token>/', views.confirmar_reset_password, name='confirmar_reset_password'),
    path('invite-token/regenerate/', views.regenerar_invite_token, name='regenerar_invite_token'),
    path('join/<str:token>/', views.registrar_tienda, name='registrar_tienda'),
    path('invitations/new/', views.emitir_invitacion, name='emitir_invitacion'),
    path('invitations/', views.invitaciones, name='invitaciones'),
    path('invitations/<int:id>/revoke/', views.revocar_invitacion, name='revocar_invitacion'),
    path('join-distributor/<str:token>/', views.registrar_distribuidor, name='registrar_distribuidor'),
    path('notifications/', views.notificaciones, name='notificaciones'),
    path('notifications/<int:id>/read/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notifications/read-all/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
]
