from django.urls import path
from . import views

app_name = "board"

urlpatterns = [
    path("", views.boards, name="boards"),
    path("create/", views.create_board, name="create_board"),
    path("<uuid:board_uuid>/", views.home, name="home"),
    path("board/<uuid:uuid>/settings/", views.board_settings, name="settings"),
]