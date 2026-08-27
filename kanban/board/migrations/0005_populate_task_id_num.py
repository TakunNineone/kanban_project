from django.db import migrations, models


def populate_id_num(apps, schema_editor):
    Task = apps.get_model('board', 'Task')
    max_id = Task.objects.aggregate(models.Max('id_num'))['id_num__max'] or 0
    tasks = Task.objects.filter(id_num__isnull=True).order_by('date', 'uuid')
    for i, task in enumerate(tasks, start=max_id + 1):
        task.id_num = i
        task.save(update_fields=['id_num'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('board', '0004_task_id_num'),
    ]

    operations = [
        migrations.RunPython(populate_id_num, noop),
    ]
