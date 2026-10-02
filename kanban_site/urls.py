from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, reverse_lazy, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles import views as static_views

from kanban.board import views as board_views


urlpatterns = [
    path(
        '',
        RedirectView.as_view(
            pattern_name='board:boards',
            permanent=False,
        ),
    ),

    path('admin/', admin.site.urls),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html'
        ),
        name='login',
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(
            next_page=reverse_lazy('login')
        ),
        name='logout',
    ),

    path('register/', board_views.register, name='register'),
    path('kanban/', include('kanban.board.urls')),
    path('api/', include('kanban.api.urls')),
]


if settings.DEBUG:
    # JupyterHub удаляет /user/kosmenkoas/proxy/2020
    # перед передачей запроса Django.
    re_static = re_path(
        r'^static/(?P<path>.*)$',
        static_views.serve,
    )
    urlpatterns += [re_static]

    urlpatterns += static(
        '/media/',
        document_root=settings.MEDIA_ROOT,
    )