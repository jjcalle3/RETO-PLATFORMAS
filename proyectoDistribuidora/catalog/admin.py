from django.contrib import admin

from .models import (
    Brand,
    Category,
    Discount,
    Product,
    ProductImage,
    StockLevel,
    Store,
    Warehouse,
)


class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'owner', 'distributor')
    search_fields = ('name', 'address', 'phone_number', 'distributor__name')
    list_filter = ('distributor',)

admin.site.register(Store, StoreAdmin)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'sku', 'unit_price', 'status', 'category', 'brand',
        'low_stock_threshold', 'distributor',
    )
    search_fields = ('name', 'sku', 'barcode', 'description')
    list_filter = ('status', 'category', 'brand', 'distributor')
    inlines = [ProductImageInline, DiscountInline]

admin.site.register(Product, ProductAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'distributor')
    search_fields = ('name',)
    list_filter = ('distributor',)

admin.site.register(Category, CategoryAdmin)


class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'distributor')
    search_fields = ('name',)
    list_filter = ('distributor',)

admin.site.register(Brand, BrandAdmin)


class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'distributor')
    list_filter = ('distributor',)

admin.site.register(Warehouse, WarehouseAdmin)


class StockLevelAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity')
    search_fields = ('product__name', 'product__sku')
    list_filter = ('warehouse',)

admin.site.register(StockLevel, StockLevelAdmin)
