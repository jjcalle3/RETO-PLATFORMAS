import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_finalize_tier_4_5'),
        ('orders', '0005_alter_order_id_alter_orderitem_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='warehouse',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='catalog.warehouse'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='warehouse',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='catalog.warehouse'),
        ),
    ]
