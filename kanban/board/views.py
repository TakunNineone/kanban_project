from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.formats import localize
from django.contrib.auth.models import User
from .models import BoardGroup
from .forms import BoardForm, SignUpForm


def register(request):
    if request.user.is_authenticated:
        return redirect("board:boards")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("board:boards")
    else:
        form = SignUpForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def boards(request):
    if request.user.is_superuser:
        boards = BoardGroup.objects.all()
    else:
        boards = BoardGroup.objects.filter(members=request.user)

    return render(
        request,
        "board.html",
        {
            "boards": boards
        }
    )


@login_required
def home(request, board_uuid):
    if request.user.is_superuser:
        board = get_object_or_404(BoardGroup, uuid=board_uuid)
    else:
        board = get_object_or_404(
            BoardGroup,
            uuid=board_uuid,
            members=request.user
        )

    tasks = board.tasks.all()

    all_tasks = []

    for t in tasks:
        all_tasks.append({
            "uuid": str(t.uuid),
            "name": t.name,
            "boardName": t.boardName,
            "date": str(localize(t.date)),
            "priority": t.priority,
        })

    return render(
        request,
        "kanban.html",
        {
            "tasks": all_tasks,
            "board": board,
        },
    )


@login_required
def create_board(request):
    if request.method == "POST":
        form = BoardForm(request.POST)
        if form.is_valid():
            board = form.save(commit=False)
            board.owner = request.user
            board.save()
            board.members.add(request.user)
            return redirect("board:boards")
    else:
        form = BoardForm()
    return render(
        request,
        "create_board.html",
        {
            "form": form
        }
    )


@login_required
def board_settings(request, uuid):
    if request.user.is_superuser:
        board = get_object_or_404(BoardGroup, uuid=uuid)
    else:
        board = get_object_or_404(
            BoardGroup,
            uuid=uuid,
            owner=request.user
        )

    users = User.objects.exclude(id=request.user.id)

    if request.method == "POST":

        user_ids = request.POST.getlist("members")

        board.members.set(
            [request.user.id] + user_ids
        )

        return redirect(
            "board:settings",
            uuid=board.uuid
        )


    return render(
        request,
        "settings.html",
        {
            "board": board,
            "users": users
        }
    )
