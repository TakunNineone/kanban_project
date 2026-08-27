import uuid
from django.db import models
from django.contrib.auth.models import User


class BoardGroup(models.Model):
    """Общая канбан-доска (команда/проект)"""
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        editable=False
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Название группы"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_board_groups',
        verbose_name="Создатель"
    )
    members = models.ManyToManyField(
        User,
        related_name='board_groups',
        blank=True,
        verbose_name="Участники"
    )
    created = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.members.add(self.owner)

    class Meta:
        verbose_name = "Группа доски"
        verbose_name_plural = "Группы досок"

    def __str__(self):
        return self.name


class Task(models.Model):
    class BoardNames(models.TextChoices):
        TODO = "todo", "Сделать"
        IN_PROGRESS = "progress", "В процессе"
        REVIEW = "review", "На проверке"
        DONE = "done", "Выполнено"

    class Priority(models.IntegerChoices):
        LOW = 1, 'Низкий'
        MEDIUM = 2, 'Средний'
        HIGH = 3, 'Высокий'
        CRITICAL = 4, 'Критический'

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        editable=False
    )
    id_num = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="Номер задачи"
    )
    group = models.ForeignKey(
        BoardGroup,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Группа"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        verbose_name="Создатель"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name="Ответственный исполнитель"
    )
    co_executors = models.ManyToManyField(
        User,
        related_name='co_assigned_tasks',
        blank=True,
        verbose_name="Соисполнители"
    )
    followers = models.ManyToManyField(
        User,
        related_name='followed_tasks',
        blank=True,
        verbose_name="Наблюдатели"
    )
    name = models.CharField(
        max_length=500,
        verbose_name="Название"
    )
    boardName = models.CharField(
        max_length=12,
        choices=BoardNames.choices,
        default=BoardNames.TODO,
        verbose_name="Статус"
    )
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Приоритет"
    )
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дедлайн"
    )
    updated = models.DateTimeField(auto_now=True)
    position = models.PositiveIntegerField(default=0)

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата завершения"
    )

    is_archived = models.BooleanField(
        default=False,
        verbose_name="В архиве"
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата архивации"
    )
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_tasks',
        verbose_name="Архивировано пользователем"
    )
    archive_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Причина архивации"
    )

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-priority', '-date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id_num:
            max_id = Task.objects.aggregate(models.Max('id_num'))['id_num__max'] or 0
            self.id_num = max_id + 1
        super().save(*args, **kwargs)

    @property
    def formatted_id(self):
        return f"#{self.id_num:06d}" if self.id_num else ""


class ChecklistItem(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="checklist_items",
        verbose_name="Задача"
    )
    text = models.CharField(
        max_length=300,
        verbose_name="Текст подзадачи"
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name="Выполнено"
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Элемент чек-листа"
        verbose_name_plural = "Элементы чек-листа"
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.task.name} - {self.text}"


class TaskComment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    # Поле текста сделано необязательным для комментариев только с вложениями
    text = models.TextField(blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return f"{self.author} - {self.task}"


class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    file = models.FileField(upload_to="kanban/tasks/")
    original_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name.split('/')[-1]
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)


class CommentAttachment(models.Model):
    comment = models.ForeignKey(
        TaskComment,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    file = models.FileField(upload_to="kanban/comments/")
    original_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name.split('/')[-1]
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)


class TaskHistory(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="history"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE
    )
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task.name}: {self.action}"