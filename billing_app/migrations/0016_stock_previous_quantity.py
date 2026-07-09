from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing_app', '0015_remove_bill_gst_amount_remove_bill_gst_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='stock',
            name='previous_quantity',
            field=models.IntegerField(blank=True, editable=False, null=True),
        ),
    ]
