import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_initial'),
        ('catalog', '0003_alter_product_id_alter_store_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('distributor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='accounts.distributor')),
            ],
            options={'verbose_name_plural': 'Categories'},
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.UniqueConstraint(fields=('distributor', 'name'), name='unique_category_name_per_distributor'),
        ),
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('distributor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brands', to='accounts.distributor')),
            ],
        ),
        migrations.AddConstraint(
            model_name='brand',
            constraint=models.UniqueConstraint(fields=('distributor', 'name'), name='unique_brand_name_per_distributor'),
        ),
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('distributor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='warehouses', to='accounts.distributor')),
            ],
        ),
        migrations.AddConstraint(
            model_name='warehouse',
            constraint=models.UniqueConstraint(fields=('distributor', 'name'), name='unique_warehouse_name_per_distributor'),
        ),
        migrations.AddField(
            model_name='product',
            name='status',
            field=models.CharField(choices=[('ACTIVE', 'Activo'), ('INACTIVE', 'Inactivo'), ('DISCONTINUED', 'Descontinuado')], default='ACTIVE', max_length=20),
        ),
        migrations.AddField(
            model_name='product',
            name='sku',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='barcode',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='product',
            name='unit_of_measure',
            field=models.CharField(choices=[('PIECE', 'Pieza'), ('BOX', 'Caja'), ('PACK', 'Paquete'), ('BOTTLE', 'Botella'), ('KG', 'Kilogramo'), ('LITER', 'Litro')], default='PIECE', max_length=20),
        ),
        migrations.AddField(
            model_name='product',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='catalog.category'),
        ),
        migrations.AddField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='catalog.brand'),
        ),
        migrations.CreateModel(
            name='StockLevel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_levels', to='catalog.product')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_levels', to='catalog.warehouse')),
            ],
        ),
        migrations.AddConstraint(
            model_name='stocklevel',
            constraint=models.UniqueConstraint(fields=('product', 'warehouse'), name='unique_product_warehouse'),
        ),
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_type', models.CharField(choices=[('PERCENTAGE', 'Porcentaje'), ('FIXED_AMOUNT', 'Monto fijo')], max_length=20)),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discounts', to='catalog.product')),
            ],
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='products/')),
                ('is_main', models.BooleanField(default=False)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.product')),
            ],
        ),
    ]
