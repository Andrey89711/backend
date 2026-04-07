from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0007_contract_waybill_file_path'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='materialsincontract',
            unique_together=set(),
        ),
    ]
