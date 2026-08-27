from django.contrib.auth.models import User
from rest_framework import serializers
from kanban.board.models import (
    BoardGroup, TaskComment, Task, CommentAttachment,
    TaskAttachment, TaskHistory, Notification, ChecklistItem
)
from django.utils import timezone


class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ("id", "text", "is_completed", "position")


class TaskHistorySerializer(serializers.ModelSerializer):
    task_uuid = serializers.ReadOnlyField(source="task.uuid")
    user_name = serializers.ReadOnlyField(source="user.username")
    created_at = serializers.DateTimeField(format="%d.%m.%Y %H:%M", read_only=True)

    class Meta:
        model = TaskHistory
        fields = (
            "id",
            "task_uuid",
            "user",
            "user_name",
            "action",
            "created_at",
        )


class CommentAttachmentSerializer(serializers.ModelSerializer):
    file_size_formatted = serializers.SerializerMethodField()

    class Meta:
        model = CommentAttachment
        fields = ("id", "file", "original_name", "file_size", "file_size_formatted")

    def get_file_size_formatted(self, obj):
        size = obj.file_size or 0
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{round(size / 1024, 1)} KB"
        return f"{round(size / (1024 * 1024), 1)} MB"


class TaskAttachmentSerializer(serializers.ModelSerializer):
    file_size_formatted = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = ("id", "file", "original_name", "file_size", "file_size_formatted", "uploaded_at")

    def get_file_size_formatted(self, obj):
        size = obj.file_size or 0
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{round(size / 1024, 1)} KB"
        return f"{round(size / (1024 * 1024), 1)} MB"


class TaskCommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    author_id = serializers.ReadOnlyField(source="author.id")
    created = serializers.DateTimeField(format="%d.%m.%Y %H:%M", read_only=True)
    attachments = CommentAttachmentSerializer(many=True, read_only=True)
    text = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = TaskComment
        fields = (
            "id",
            "author",
            "author_id",
            "text",
            "created",
            "attachments",
        )


class TaskSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(read_only=True)
    created_by = serializers.ReadOnlyField(source="created_by.username")
    created_by_id = serializers.ReadOnlyField(source="created_by.id")

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    assigned_to_name = serializers.ReadOnlyField(source="assigned_to.username")

    co_executors = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False
    )
    co_executors_details = serializers.SerializerMethodField()

    checklist_items = ChecklistItemSerializer(many=True, read_only=True)
    checklist_progress = serializers.SerializerMethodField()

    history = TaskHistorySerializer(many=True, read_only=True)

    comments_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    description_short = serializers.SerializerMethodField()

    archived_by_name = serializers.ReadOnlyField(source="archived_by.username")
    formatted_id = serializers.ReadOnlyField()

    is_following = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(id=request.user.id).exists()
        return False

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_description_short(self, obj):
        if not obj.description:
            return ""
        return obj.description[:50] + ("..." if len(obj.description) > 50 else "")

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_attachments_count(self, obj):
        return obj.attachments.count()

    def get_is_overdue(self, obj):
        if not obj.deadline:
            return False
        return obj.deadline < timezone.now().date()

    def get_co_executors_details(self, obj):
        return [{"id": u.id, "username": u.username} for u in obj.co_executors.all()]

    def get_checklist_progress(self, obj):
        items = obj.checklist_items.all()
        total = items.count()
        if total == 0:
            return None
        completed = items.filter(is_completed=True).count()
        return {"total": total, "completed": completed}

    class Meta:
        model = Task
        fields = (
            "uuid",
            "formatted_id",
            "name",
            "boardName",
            "priority",
            "date",
            "created_by",
            "created_by_id",
            "assigned_to",
            "assigned_to_name",
            "co_executors",
            "co_executors_details",
            "group",
            "description",
            "description_short",
            "deadline",
            "updated",
            "comments_count",
            "attachments_count",
            "is_overdue",
            "position",
            "completed_at",
            "is_archived",
            "archived_at",
            "archived_by_name",
            "archive_reason",
            "checklist_items",
            "checklist_progress",
            "history",
            "is_following",
            "followers_count",
        )
        read_only_fields = (
            "uuid",
            "formatted_id",
            "date",
            "created_by",
            "completed_at",
            "is_archived",
            "archived_at",
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class BoardGroupSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)

    class Meta:
        model = BoardGroup
        fields = ["uuid", "name", "owner_id"]


class CommentAttachmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentAttachment
        fields = ("file",)


class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    task_name = serializers.ReadOnlyField(source="task.name")
    task_uuid = serializers.ReadOnlyField(source="task.uuid")
    group_uuid = serializers.ReadOnlyField(source="task.group.uuid")
    group_name = serializers.ReadOnlyField(source="task.group.name")

    class Meta:
        model = Notification
        fields = (
            "id",
            "user",
            "action",
            "created_at",
            "task_uuid",
            "task_name",
            "group_uuid",
            "group_name",
            "is_read",
        )