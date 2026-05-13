import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_ai_extensions', '0007_aiworkflowscope_specificity_index_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiworkflowsession',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='aiworkflowsession',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
