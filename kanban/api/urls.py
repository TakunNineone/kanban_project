from django.urls import path
from kanban.api.views import (
    ListGroups, ListTask, DetailTask, UserList, AddMember, GroupMembers,
    TaskCommentList, TaskCommentDetail,
    CommentAttachmentUpload, CommentAttachmentDetail, TaskAttachmentUpload,
    TaskAttachmentDetail, TaskHistoryList, NotificationList, NotificationDetail,
    NotificationReadAll, ChecklistItemListCreate, ChecklistItemDetail,
    DownloadTaskAttachment, DownloadCommentAttachment, ArchivedTaskListView,
    TaskToggleFollow, TaskRestoreView
)

urlpatterns = [
    # Доски и Участники
    path("groups/", ListGroups.as_view(), name="groups"),
    path("users/", UserList.as_view(), name="users"),
    path("boards/<uuid:board_uuid>/members/", AddMember.as_view()),
    path("groups/<uuid:group_uuid>/members/", GroupMembers.as_view(), name="group-members"),

    # Задачи, Слежение и Архив
    path("boards/<uuid:board_uuid>/tasks/", ListTask.as_view(), name="tasks"),
    path("boards/<uuid:board_uuid>/archived-tasks/", ArchivedTaskListView.as_view(), name="archived-tasks"),
    path("task/<uuid:pk>/", DetailTask.as_view(), name="task"),
    path("task/<uuid:pk>/toggle-follow/", TaskToggleFollow.as_view(), name="task-toggle-follow"),
    path("task/<uuid:pk>/restore/", TaskRestoreView.as_view(), name="task-restore"),
    path("task/<uuid:task_uuid>/history/", TaskHistoryList.as_view(), name="task-history"),

    # Чек-листы
    path("task/<uuid:task_uuid>/checklist/", ChecklistItemListCreate.as_view(), name="checklist-list"),
    path("checklist/<int:pk>/", ChecklistItemDetail.as_view(), name="checklist-detail"),

    # Комментарии
    path("task/<uuid:task_uuid>/comments/", TaskCommentList.as_view()),
    path("comment/<int:pk>/", TaskCommentDetail.as_view(), name="comment-detail"),

    # Вложения
    path("task/<uuid:task_uuid>/attachments/", TaskAttachmentUpload.as_view(), name="task-attachments"),
    path("task/attachments/<int:pk>/", TaskAttachmentDetail.as_view(), name="task-attachment-detail"),
    path("task/attachments/<int:pk>/download/", DownloadTaskAttachment.as_view(), name="task-attachment-download"),
    path("comment/<int:comment_id>/attachments/", CommentAttachmentUpload.as_view(), name="comment-attachments"),
    path("comment/attachments/<int:pk>/", CommentAttachmentDetail.as_view(), name="comment-attachment-detail"),
    path("comment/attachments/<int:pk>/download/", DownloadCommentAttachment.as_view(), name="comment-attachment-download"),

    # Уведомления
    path("notifications/", NotificationList.as_view()),
    path("notifications/<int:pk>/", NotificationDetail.as_view()),
    path("notifications/read-all/", NotificationReadAll.as_view()),
]