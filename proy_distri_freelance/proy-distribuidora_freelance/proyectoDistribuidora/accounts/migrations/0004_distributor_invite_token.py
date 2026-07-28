import secrets

from django.db import migrations, models


def backfill_invite_tokens(apps, schema_editor):
    Distributor = apps.get_model('accounts', 'Distributor')
    for distributor in Distributor.objects.all():
        distributor.invite_token = secrets.token_urlsafe(32)
        distributor.save(update_fields=['invite_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_managers'),
    ]

    operations = [
        migrations.AddField(
            model_name='distributor',
            name='invite_token',
            field=models.CharField(max_length=64, null=True, editable=False),
        ),
        migrations.RunPython(backfill_invite_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='distributor',
            name='invite_token',
            field=models.CharField(max_length=64, unique=True, editable=False),
        ),
    ]
