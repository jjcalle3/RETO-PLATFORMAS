from rest_framework import serializers
from .models import Brand, Category, Discount, Product, ProductImage, StockLevel, Store, Warehouse

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'address', 'phone_number', 'distributor', 'owner', 'vendor']
        # distributor is stamped server-side from the caller's own tenant
        # (see catalog/api_views.py) — never client-supplied.
        read_only_fields = ['distributor']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'distributor']
        read_only_fields = ['distributor']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'distributor']
        read_only_fields = ['distributor']

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'distributor']
        read_only_fields = ['distributor']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_main']

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ['id', 'product', 'discount_type', 'discount_value', 'start_date', 'end_date']

class ProductSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'unit_price', 'current_price', 'status',
            'low_stock_threshold', 'sku', 'barcode', 'category', 'brand',
            'unit_of_measure', 'distributor',
        ]
        read_only_fields = ['distributor']

    def get_current_price(self, obj):
        return obj.current_price()

class StockLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLevel
        fields = ['id', 'product', 'warehouse', 'quantity']
        read_only_fields = ['quantity']  # Stock only changes via receive/contar/ajustar
