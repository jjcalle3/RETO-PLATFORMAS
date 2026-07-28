from django import forms
from catalog.models import ProductStatus, Store, Product
from .models import Order, OrderItem


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['store']
        labels = {'store': 'Tienda'}

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields['store'].queryset = Store.objects.filter(owner=owner)


class ReportarIncidenciaForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['issue_description']
        widgets = {'issue_description': forms.Textarea(attrs={'rows': 4})}
        labels = {'issue_description': 'Describe el problema'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # blank=True on the model allows orders with no issue; a submitted
        # report itself must not be empty.
        self.fields['issue_description'].required = True


class ResolverIncidenciaForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['resolution_notes']
        widgets = {'resolution_notes': forms.Textarea(attrs={'rows': 4})}
        labels = {'resolution_notes': 'Notas de resolución'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolution_notes'].required = True


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']
        labels = {'product': 'Producto', 'quantity': 'Cantidad'}

    def __init__(self, *args, vendor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vendor is not None:
            # FR-05.3 (Tier 4.5 resolution, 2026-07-21): stock is centralized,
            # not per-vendor, so any active product in the distributor's
            # catalog is orderable regardless of which vendor is assigned —
            # the old inventory__vendor filter is gone, not just relaxed.
            self.fields['product'].queryset = Product.objects.filter(
                distributor=vendor.distributor, status=ProductStatus.ACTIVE
            )
