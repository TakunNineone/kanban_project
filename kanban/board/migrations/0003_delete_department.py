from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('board', '0002_alter_task_options_commentattachment_file_size_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Department',
        ),
    ]
