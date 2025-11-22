from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        help_text="Обязательное поле. На этот email придет ссылка для восстановления пароля.",
    )
    first_name = forms.CharField(max_length=30, required=True, label="Имя")
    last_name = forms.CharField(max_length=30, required=True, label="Фамилия")
    patronymic = forms.CharField(max_length=150, required=False, label="Отчество")

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = (
            "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 "
            "text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 "
            "focus:ring-[#4495D1] transition duration-200 shadow-md text-base "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
        )

        for name, field in self.fields.items():
            field.widget.attrs.update({"class": common_classes})

        # Field-specific attributes and placeholders
        if "email" in self.fields:
            self.fields["email"].widget.attrs.update(
                {
                    "placeholder": "Электронная почта",
                    "type": "email",
                    "autocomplete": "email",
                }
            )
        if "first_name" in self.fields:
            self.fields["first_name"].widget.attrs.update({"placeholder": "Имя"})
        if "last_name" in self.fields:
            self.fields["last_name"].widget.attrs.update({"placeholder": "Фамилия"})
        if "patronymic" in self.fields:
            self.fields["patronymic"].widget.attrs.update(
                {"placeholder": "Отчество (опционально)"}
            )
        if "password1" in self.fields:
            self.fields["password1"].widget.attrs.update(
                {"placeholder": "Пароль", "autocomplete": "new-password"}
            )
        if "password2" in self.fields:
            self.fields["password2"].widget.attrs.update(
                {"placeholder": "Подтвердите пароль", "autocomplete": "new-password"}
            )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким Email уже существует")
        return email

    def _clean_name_field(self, field_name, field_label):
        """
        Общий метод для валидации и форматирования полей ФИО.
        Приводит к формату: Первая буква заглавная, остальные строчные.
        Поддерживает дефисы для двойных фамилий/имен.
        """
        value = self.cleaned_data.get(field_name)
        if not value:
            return value

        value = value.strip()

        import re

        if not re.match(r"^[а-яёА-ЯЁa-zA-Z\-]+$", value):
            raise forms.ValidationError(
                f"{field_label} может содержать только буквы (кириллица или латиница) и дефис."
            )

        formatted_value = "-".join(part.capitalize() for part in value.split("-"))

        return formatted_value

    def clean_first_name(self):
        return self._clean_name_field("first_name", "Имя")

    def clean_last_name(self):
        return self._clean_name_field("last_name", "Фамилия")

    def clean_patronymic(self):
        value = self.cleaned_data.get("patronymic")
        if not value or not value.strip():
            return ""
        return self._clean_name_field("patronymic", "Отчество")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        if commit:
            user.save()
            profile = user.profile
            profile.patronymic = self.cleaned_data.get("patronymic", "")
            profile.save()

        return user


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = (
            "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 "
            "text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 "
            "focus:ring-[#4495D1] transition duration-200 shadow-md text-base "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
        )

        if "username" in self.fields:
            self.fields["username"].widget.attrs.update(
                {
                    "class": common_classes,
                    "placeholder": "Электронная почта",
                    "type": "email",
                    "autocomplete": "email",
                }
            )

        if "password" in self.fields:
            self.fields["password"].widget.attrs.update(
                {
                    "class": common_classes,
                    "placeholder": "Пароль",
                    "autocomplete": "current-password",
                }
            )

    def confirm_login_allowed(self, user):
        """Проверка, может ли пользователь войти"""
        if not user.is_active:
            raise forms.ValidationError(
                "Этот аккаунт не активирован. Пожалуйста, подтвердите свой email адрес. "
                "Проверьте почту или запросите повторную отправку письма подтверждения.",
                code="inactive",
            )
        super().confirm_login_allowed(user)
