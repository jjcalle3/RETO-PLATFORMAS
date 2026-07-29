from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Brand, Category, Discount, Product, ProductImage, StockLevel, Store, Warehouse
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    DiscountSerializer,
    ProductImageSerializer,
    ProductSerializer,
    StockLevelSerializer,
    StoreSerializer,
    WarehouseSerializer,
)
from .permissions import IsDistributor


class StoreViewSet(viewsets.ModelViewSet):
    """
    API REST para Tiendas (Store).
    Requiere autenticación (token o sesión, ver /api/token-auth/) y rol
    DISTRIBUTOR. Todas las operaciones quedan acotadas al distribuidor
    del usuario autenticado.
    """
    serializer_class = StoreSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Store.objects.filter(distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        owner = serializer.validated_data.get('owner')
        vendor = serializer.validated_data.get('vendor')
        distributor = self.request.user.distributor
        if owner is not None and owner.distributor_id != distributor.id:
            raise PermissionDenied('owner debe pertenecer al mismo distribuidor.')
        if vendor is not None and vendor.distributor_id != distributor.id:
            raise PermissionDenied('vendor debe pertenecer al mismo distribuidor.')
        serializer.save(distributor=distributor)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Category.objects.filter(distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        serializer.save(distributor=self.request.user.distributor)


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Brand.objects.filter(distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        serializer.save(distributor=self.request.user.distributor)


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Warehouse.objects.filter(distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        serializer.save(distributor=self.request.user.distributor)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API REST para Productos (Product).
    Acotada al distribuidor del usuario autenticado. category/brand deben
    pertenecer al mismo distribuidor (mismo patrón que owner/vendor en
    StoreViewSet).
    """
    serializer_class = ProductSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Product.objects.filter(distributor=self.request.user.distributor)

    def _validate_tenant_fks(self, serializer, distributor):
        category = serializer.validated_data.get('category')
        brand = serializer.validated_data.get('brand')
        if category is not None and category.distributor_id != distributor.id:
            raise PermissionDenied('category debe pertenecer al mismo distribuidor.')
        if brand is not None and brand.distributor_id != distributor.id:
            raise PermissionDenied('brand debe pertenecer al mismo distribuidor.')

    def perform_create(self, serializer):
        distributor = self.request.user.distributor
        self._validate_tenant_fks(serializer, distributor)
        serializer.save(distributor=distributor)

    def perform_update(self, serializer):
        self._validate_tenant_fks(serializer, self.request.user.distributor)
        serializer.save()


class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return ProductImage.objects.filter(product__distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        product = serializer.validated_data.get('product')
        if product is not None and product.distributor_id != self.request.user.distributor_id:
            raise PermissionDenied('product debe pertenecer al mismo distribuidor.')
        serializer.save()


class DiscountViewSet(viewsets.ModelViewSet):
    serializer_class = DiscountSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Discount.objects.filter(product__distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        product = serializer.validated_data.get('product')
        if product is not None and product.distributor_id != self.request.user.distributor_id:
            raise PermissionDenied('product debe pertenecer al mismo distribuidor.')
        serializer.save()


class StockLevelViewSet(viewsets.ModelViewSet):
    serializer_class = StockLevelSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return StockLevel.objects.filter(product__distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        product = serializer.validated_data.get('product')
        warehouse = serializer.validated_data.get('warehouse')
        distributor = self.request.user.distributor
        if product is not None and product.distributor_id != distributor.id:
            raise PermissionDenied('product debe pertenecer al mismo distribuidor.')
        if warehouse is not None and warehouse.distributor_id != distributor.id:
            raise PermissionDenied('warehouse debe pertenecer al mismo distribuidor.')
        serializer.save()
