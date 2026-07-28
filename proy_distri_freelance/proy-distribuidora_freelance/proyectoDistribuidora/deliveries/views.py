from django.contrib import messages
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from orders.models import Order
from .exceptions import DeliveryAlreadyConfirmed
from .models import DeliveryConfirmation
from .forms import DeliveryConfirmationForm


def _wants_json(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


@role_required('DELIVERY', 'DISTRIBUTOR')
def index(request):
    return render(request, 'deliveries/index.html', {
        'pending': Order.objects.dispatched_for_distributor(request.user.distributor),
        'issues': Order.objects.issues_for(request.user),
        'history': DeliveryConfirmation.objects.recent_for_distributor(request.user.distributor),
    })


@role_required('DELIVERY')
def crear_confirmacion(request):
    return redirect('index_deliveries')


@role_required('DELIVERY')
def ver_pedido_entrega(request, order_id):
    order = get_object_or_404(
        Order.objects
        .filter(store__distributor=request.user.distributor)
        .select_related('store', 'vendor')
        .prefetch_related('items__product'),
        pk=order_id,
    )
    return render(request, 'deliveries/ver_pedido_entrega.html', {
        'order': order,
        'order_total': order.total(),
        'is_dispatched': order.is_dispatched,
    })


@role_required('DELIVERY')
def confirmar_entrega(request, order_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    wants_json = _wants_json(request)
    try:
        confirmacion = DeliveryConfirmation.objects.confirm(
            order_id, request.user.distributor, request.user
        )
    except Order.DoesNotExist:
        raise Http404('Pedido no disponible para confirmar.')
    except DeliveryAlreadyConfirmed as error:
        if wants_json:
            # DESIGN.md "Interaction States": the optimistic UI reverts the
            # card and shows this text on any non-2xx response.
            return JsonResponse({'success': False, 'error': str(error)}, status=409)
        messages.error(request, str(error))
        return redirect('index_deliveries')

    if wants_json:
        return JsonResponse({
            'success': True,
            'order_id': confirmacion.order_id,
            'store_name': confirmacion.order.store.name,
            'delivery_user': request.user.email,
            'confirmed_at': confirmacion.confirmed_at.isoformat(),
        })
    messages.success(request, 'Entrega confirmada.')
    return redirect('index_deliveries')


@role_required('DELIVERY', 'DISTRIBUTOR')
def editar_confirmacion(request, id):
    lookup = {'id': id, 'order__store__distributor': request.user.distributor}
    if request.user.role == 'DELIVERY':
        lookup['delivery_user'] = request.user
    confirmacion = get_object_or_404(DeliveryConfirmation, **lookup)
    if request.method == 'POST':
        formulario = DeliveryConfirmationForm(
            request.POST, instance=confirmacion, distributor=request.user.distributor
        )
        if formulario.is_valid():
            formulario.save()
            return redirect('index_deliveries')
    else:
        formulario = DeliveryConfirmationForm(instance=confirmacion, distributor=request.user.distributor)
    return render(request, 'deliveries/editar_confirmacion.html', {
        'formulario': formulario,
        'confirmacion': confirmacion,
    })


@role_required('DISTRIBUTOR')
def eliminar_confirmacion(request, id):
    get_object_or_404(
        DeliveryConfirmation, id=id, order__store__distributor=request.user.distributor
    ).delete()
    return redirect('index_deliveries')
