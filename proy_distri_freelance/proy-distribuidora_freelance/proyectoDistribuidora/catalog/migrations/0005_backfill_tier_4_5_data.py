from django.db import migrations


def backfill(apps, schema_editor):
    """Tier 4.5 data migration (docs/TODOS.md): is_active=True -> ACTIVE,
    is_active=False -> INACTIVE. Never auto-maps to DISCONTINUED, which is a
    distinct explicit action. Also backfills sku and a placeholder
    category/brand for any pre-Tier-4.5 product rows so the fields can be
    made required in the next migration."""
    Product = apps.get_model('catalog', 'Product')
    Category = apps.get_model('catalog', 'Category')
    Brand = apps.get_model('catalog', 'Brand')

    for product in Product.objects.all():
        product.status = 'ACTIVE' if product.is_active else 'INACTIVE'
        if not product.sku:
            product.sku = f'SKU-{product.pk}'
        if product.category_id is None:
            category, _ = Category.objects.get_or_create(
                distributor=product.distributor, name='General'
            )
            product.category = category
        if product.brand_id is None:
            brand, _ = Brand.objects.get_or_create(
                distributor=product.distributor, name='Genérica'
            )
            product.brand = brand
        product.save()


def reverse_backfill(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    for product in Product.objects.all():
        product.is_active = product.status == 'ACTIVE'
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_tier_4_5_models'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_backfill),
    ]
