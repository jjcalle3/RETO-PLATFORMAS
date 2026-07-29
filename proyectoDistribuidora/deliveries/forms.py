from django import forms
from orders.models import Order, OrderStatus
from .models import DeliveryConfirmation


class DeliveryConfirmationForm(forms.ModelForm):
    class Meta:
        model = DeliveryConfirmation
        fields = ['order', 'confirmed_at']
        labels = {
            'order': 'Pedido',
            'confirmed_at': 'Confirmado en',
        }

    def __init__(self, *args, distributor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if distributor is not None:
            qs = Order.objects.filter(store__distributor=distributor)
            if self.instance.pk:
                # Editing an existing confirmation: the order is fixed —
                # its status has already moved past DISPATCHED by now, so
                # don't re-apply the DISPATCHED-only filter here.
                qs = qs.filter(pk=self.instance.order_id)
            else:
                # Only orders actually out for delivery can be confirmed —
                # closes a pre-existing gap where any order in the
                # distributor could be picked, regardless of status.
                qs = qs.filter(status=OrderStatus.DISPATCHED)
            self.fields['order'].queryset = qs
