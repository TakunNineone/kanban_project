import os
import re
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404, HttpResponse
from django.contrib.auth.models import User
from django.db.models import F

from rest_framework import generics, exceptions
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from kanban.board.models import (
    BoardGroup, TaskComment, TaskAttachment, CommentAttachment,
    Task, TaskHistory, Notification, ChecklistItem
)
from kanban.api.serializers import (
    TaskSerializer, BoardGroupSerializer, UserSerializer, TaskCommentSerializer,
    CommentAttachmentCreateSerializer,
    TaskAttachmentSerializer, TaskHistorySerializer, NotificationSerializer,
    ChecklistItemSerializer, CommentAttachmentSerializer
)


def notify_task_users(task, actor, action_text, mentioned_users=None):
    targets = set()

    if task.created_by:
        targets.add(task.created_by)
    if task.assigned_to:
        targets.add(task.assigned_to)
    for user in task.co_executors.all():
        targets.add(user)
    for user in task.followers.all():
        targets.add(user)
    if mentioned_users:
        for user in mentioned_users:
            targets.add(user)

    targets.discard(actor)

    notifications = [
        Notification(user=u, task=task, action=action_text)
        for u in targets
    ]
    Notification.objects.bulk_create(notifications)


def get_board_groups_for_user(user):
    queryset = BoardGroup.objects.all()
    if not user.is_superuser:
        queryset = queryset.filter(members=user)
    return queryset


def get_board_group_for_user(user, uuid):
    if user.is_superuser:
        return get_object_or_404(BoardGroup, uuid=uuid)
    return get_object_or_404(BoardGroup, uuid=uuid, members=user)


def can_manage_group_members(user, group):
    return user.is_superuser or group.owner_id == user.id


def get_optimized_task_queryset():
    return Task.objects.select_related(
        'created_by',
        'assigned_to',
        'group',
        'archived_by'
    ).prefetch_related(
        'co_executors',
        'followers',
        'checklist_items',
        'attachments',
        'comments'
    )


class ListTask(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        board = get_board_group_for_user(
            self.request.user,
            self.kwargs["board_uuid"],
        )
        return get_optimized_task_queryset().filter(
            group=board,
            is_archived=False
        )

    def perform_create(self, serializer):
        board = get_board_group_for_user(
            self.request.user,
            self.kwargs["board_uuid"],
        )

        assigned_to = None
        user_id = self.request.data.get("assigned_to")
        if user_id:
            assigned_to = board.members.filter(id=user_id).first()

        co_executor_ids = self.request.data.get("co_executors", [])

        task = serializer.save(
            created_by=self.request.user,
            group=board,
            assigned_to=assigned_to
        )

        if co_executor_ids:
            task.co_executors.set(board.members.filter(id__in=co_executor_ids))

        task.followers.add(self.request.user)

        TaskHistory.objects.create(
            task=task,
            user=self.request.user,
            action="Создана задача"
        )

        notify_task_users(task, self.request.user, f"{self.request.user.username} создал задачу '{task.name}'")


class DetailTask(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_optimized_task_queryset().filter(
            group__members=self.request.user
        ).distinct()

    def perform_update(self, serializer):
        task = self.get_object()
        user = self.request.user
        is_creator = (task.created_by == user)
        is_assigned = (task.assigned_to == user)

        new_board_name = serializer.validated_data.get("boardName", task.boardName)
        old_board_name = task.boardName

        if new_board_name == Task.BoardNames.DONE and old_board_name != Task.BoardNames.DONE:
            if not is_assigned:
                raise exceptions.PermissionDenied(
                    "Только ответственный исполнитель задачи может переводить её в статус 'Выполнено'."
                )

        if not is_creator:
            restricted_fields = ["name", "description", "priority", "deadline", "co_executors"]
            field_changed = any(
                field in serializer.validated_data and serializer.validated_data[field] != getattr(task, field)
                for field in restricted_fields
            )
            if field_changed:
                raise exceptions.PermissionDenied(
                    "Только создатель задачи может редактировать её параметры."
                )

        if new_board_name == Task.BoardNames.DONE and old_board_name != Task.BoardNames.DONE:
            serializer.validated_data["completed_at"] = timezone.now()
        elif new_board_name != Task.BoardNames.DONE and old_board_name == Task.BoardNames.DONE:
            serializer.validated_data["completed_at"] = None

        updated_task = serializer.save()

        action_msg = "Изменена задача"
        if old_board_name != new_board_name:
            action_msg = f"Статус изменен: {old_board_name} -> {new_board_name}"

        TaskHistory.objects.create(
            task=updated_task,
            user=user,
            action=action_msg
        )

        notify_task_users(updated_task, user, f"{user.username}: {action_msg}")

        # 3. АВТО-АРХИВАЦИЯ ПРИ ПРЕВЫШЕНИИ 15 ЗАДАЧ
        if new_board_name == Task.BoardNames.DONE:
            # Заполняем пропущенный completed_at если у каких-то задач он равен NULL
            Task.objects.filter(
                group=updated_task.group,
                boardName=Task.BoardNames.DONE,
                completed_at__isnull=True
            ).update(completed_at=timezone.now())

            done_tasks = Task.objects.filter(
                group=updated_task.group,
                boardName=Task.BoardNames.DONE,
                is_archived=False
            ).order_by("completed_at", "date")

            if done_tasks.count() > 15:
                excess_count = done_tasks.count() - 15
                tasks_to_archive = list(done_tasks[:excess_count])
                now = timezone.now()
                for t in tasks_to_archive:
                    t.is_archived = True
                    t.archived_at = now
                    t.archive_reason = "Автоматическая архивация (лимит >15 задач)"
                Task.objects.bulk_update(tasks_to_archive, ["is_archived", "archived_at", "archive_reason"])

    def perform_destroy(self, instance):
        instance.is_archived = True
        instance.archived_at = timezone.now()
        instance.archived_by = self.request.user
        instance.archive_reason = f"Удалена пользователем {self.request.user.username}"
        instance.save()

        TaskHistory.objects.create(
            task=instance,
            user=self.request.user,
            action="Задача отправлена в архив (удалена)"
        )


class TaskToggleFollow(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(Task, uuid=pk, group__members=request.user)
        if request.user in task.followers.all():
            task.followers.remove(request.user)
            is_following = False
        else:
            task.followers.add(request.user)
            is_following = True

        return Response({
            "is_following": is_following,
            "followers_count": task.followers.count()
        })


class TaskRestoreView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(Task, uuid=pk, group__members=request.user)
        task.is_archived = False
        task.archived_at = None
        task.archived_by = None
        task.archive_reason = None
        task.save()

        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action="Задача восстановлена из архива"
        )
        return Response({"status": "restored"})


class ChecklistItemListCreate(generics.ListCreateAPIView):
    serializer_class = ChecklistItemSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChecklistItem.objects.filter(
            task__uuid=self.kwargs["task_uuid"],
            task__group__members=self.request.user
        )

    def perform_create(self, serializer):
        task = get_object_or_404(Task, uuid=self.kwargs["task_uuid"], group__members=self.request.user)
        serializer.save(task=task)


class ChecklistItemDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChecklistItemSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChecklistItem.objects.filter(task__group__members=self.request.user)


class TaskCommentList(generics.ListCreateAPIView):
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def get_queryset(self):
        return TaskComment.objects.select_related('author').prefetch_related('attachments').filter(
            task__uuid=self.kwargs["task_uuid"],
            task__group__members=self.request.user
        )

    def perform_create(self, serializer):
        task = get_object_or_404(
            Task,
            uuid=self.kwargs["task_uuid"],
            group__members=self.request.user
        )
        comment = serializer.save(task=task, author=self.request.user)

        TaskHistory.objects.create(
            task=task,
            user=self.request.user,
            action="Добавлен комментарий"
        )

        mentioned_usernames = re.findall(r'@(\w+)', comment.text)
        mentioned_users = list(User.objects.filter(
            username__in=mentioned_usernames,
            board_groups=task.group
        ).exclude(id=self.request.user.id))

        notify_task_users(
            task,
            self.request.user,
            f"{self.request.user.username} добавил комментарий",
            mentioned_users=mentioned_users
        )


class TaskCommentDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskCommentSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskComment.objects.filter(task__group__members=self.request.user)

    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.author != self.request.user:
            raise exceptions.PermissionDenied("Вы можете редактировать только свои комментарии.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise exceptions.PermissionDenied("Вы можете удалять только свои комментарии.")
        instance.delete()


class DownloadTaskAttachment(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        attachment = get_object_or_404(TaskAttachment, id=pk, task__group__members=request.user)
        if not attachment.file:
            raise Http404("Файл не найден")

        filename = attachment.original_name or os.path.basename(attachment.file.name)
        return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=filename)


class DownloadCommentAttachment(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        attachment = get_object_or_404(CommentAttachment, id=pk, comment__task__group__members=request.user)
        if not attachment.file:
            raise Http404("Файл не найден")

        filename = attachment.original_name or os.path.basename(attachment.file.name)
        return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=filename)


class TaskAttachmentUpload(generics.ListCreateAPIView):
    serializer_class = TaskAttachmentSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskAttachment.objects.filter(
            task__uuid=self.kwargs["task_uuid"],
            task__group__members=self.request.user
        )

    def perform_create(self, serializer):
        task = get_object_or_404(Task, uuid=self.kwargs["task_uuid"], group__members=self.request.user)
        uploaded_file = self.request.FILES.get('file')
        original_name = uploaded_file.name if uploaded_file else ""
        file_size = uploaded_file.size if uploaded_file else 0

        serializer.save(task=task, original_name=original_name, file_size=file_size)
        notify_task_users(task, self.request.user, f"{self.request.user.username} добавил вложение")


class TaskAttachmentDetail(generics.DestroyAPIView):
    serializer_class = TaskAttachmentSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskAttachment.objects.filter(task__group__members=self.request.user)

    def perform_destroy(self, instance):
        task = instance.task
        instance.file.delete(save=False)
        instance.delete()

        TaskHistory.objects.create(
            task=task,
            user=self.request.user,
            action="Удалено вложение"
        )


class CommentAttachmentUpload(generics.CreateAPIView):
    serializer_class = CommentAttachmentCreateSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        comment = get_object_or_404(
            TaskComment,
            id=self.kwargs["comment_id"],
            task__group__members=self.request.user
        )
        uploaded_file = self.request.FILES.get('file')
        original_name = uploaded_file.name if uploaded_file else ""
        file_size = uploaded_file.size if uploaded_file else 0

        serializer.save(comment=comment, original_name=original_name, file_size=file_size)


class CommentAttachmentDetail(generics.DestroyAPIView):
    serializer_class = CommentAttachmentSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommentAttachment.objects.filter(comment__task__group__members=self.request.user)


class ArchivedTaskListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        board = get_board_group_for_user(
            self.request.user,
            self.kwargs["board_uuid"],
        )
        return get_optimized_task_queryset().filter(
            group=board,
            is_archived=True
        ).order_by("-archived_at")


class ListGroups(generics.ListAPIView):
    serializer_class = BoardGroupSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_board_groups_for_user(self.request.user)


class UserList(generics.ListAPIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.order_by('username')


class AddMember(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, board_uuid):
        if request.user.is_superuser:
            board = get_object_or_404(BoardGroup, uuid=board_uuid)
        else:
            board = get_object_or_404(BoardGroup, uuid=board_uuid, owner=request.user)
        user = get_object_or_404(User, id=request.data.get("user_id"))
        board.members.add(user)
        return Response({"status": "added", "user": user.username})


class GroupMembers(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group = get_board_group_for_user(self.request.user, self.kwargs["group_uuid"])
        return group.members.all()

    def create(self, request, *args, **kwargs):
        group = get_board_group_for_user(request.user, self.kwargs["group_uuid"])
        if not can_manage_group_members(request.user, group):
            return Response(
                {"detail": "Только создатель группы может изменять состав участников."},
                status=403,
            )
        user_ids = request.data.get("users", [])
        allowed_ids = list(
            User.objects.filter(
                id__in=user_ids,
            ).values_list('id', flat=True)
        )
        member_ids = set(allowed_ids)
        member_ids.add(group.owner_id)
        group.members.set(member_ids)
        return Response(UserSerializer(group.members.all(), many=True).data)


class TaskHistoryList(generics.ListAPIView):
    serializer_class = TaskHistorySerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskHistory.objects.select_related('user').filter(
            task__uuid=self.kwargs["task_uuid"],
            task__group__members=self.request.user
        )


class NotificationList(generics.ListAPIView):
    serializer_class = NotificationSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.select_related('user', 'task', 'task__group').filter(
            user=self.request.user
        ).order_by("-created_at")


class NotificationDetail(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(is_read=True)


class NotificationReadAll(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"status": "ok"})
