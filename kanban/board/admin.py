from django.contrib import admin
from .models import Task, BoardGroup


@admin.register(BoardGroup)
class BoardGroupAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'owner',
        'created'
    )

    filter_horizontal = (
        'members',
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'group',
        'boardName',
        'priority',
        'date'
    )

    list_filter = (
        'boardName',
        'priority',
        'group'
    )