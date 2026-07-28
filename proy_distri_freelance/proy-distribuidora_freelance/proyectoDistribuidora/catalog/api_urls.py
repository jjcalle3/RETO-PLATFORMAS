from rest_framework.routers import DefaultRouter

from .api_views import (
    BrandViewSet,
    CategoryViewSet,
    DiscountViewSet,
    ProductImageViewSet,
    ProductViewSet,
    StockLevelViewSet,
    StoreViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='api-store')
router.register(r'products', ProductViewSet, basename='api-product')
router.register(r'categories', CategoryViewSet, basename='api-category')
router.register(r'brands', BrandViewSet, basename='api-brand')
router.register(r'warehouses', WarehouseViewSet, basename='api-warehouse')
router.register(r'stock-levels', StockLevelViewSet, basename='api-stock-level')
router.register(r'product-images', ProductImageViewSet, basename='api-product-image')
router.register(r'discounts', DiscountViewSet, basename='api-discount')

urlpatterns = router.urls
