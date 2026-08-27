from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import BoardGroup

INPUT_CLASS = (
    "w-full border border-gray-300 rounded px-3 py-2 "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class SignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Имя пользователя"
        self.fields["password1"].label = "Пароль"
        self.fields["password2"].label = "Подтверждение пароля"
        self.fields["password1"].help_text = ""
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASS


class BoardForm(forms.ModelForm):
    class Meta:
        model = BoardGroup
        fields = [
            "name",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2 "
                         "focus:outline-none focus:ring-2 focus:ring-blue-500",
            }),
        }