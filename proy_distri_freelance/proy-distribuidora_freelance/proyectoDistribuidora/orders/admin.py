from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1



class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'store',
        'vendor',
        'status',
        'rejection_reason',
        'created_at',
        'updated_at',
    )

    list_filter = (
        'status',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'store__name',
        'vendor__email',
    )

    inlines = [OrderItemInline]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'product',
        'quantity',
        'unit_price_at_time',
    )

    search_fields = (
        'order__id',
        'product__name',
    )
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)  