from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordResetForm,
)
from django.contrib.auth.models import User
from captcha.fields import CaptchaField
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
    captcha = CaptchaField(
        label="Подтверждение",
        help_text="Решите простой пример для защиты от ботов",
        error_messages={
            "invalid": "Неверный ответ. Попробуйте ещё раз.",
            "required": "Пожалуйста, решите пример.",
        },
    )

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


class ResendConfirmationForm(forms.Form):
    """Форма для повторной отправки письма подтверждения"""

    email = forms.EmailField(
        required=True,
        label="Email адрес",
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 "
                "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                "focus:ring-2 focus:ring-blue-500 focus:border-transparent "
                "transition duration-200",
                "placeholder": "example@mail.ru",
            }
        ),
    )
    captcha = CaptchaField(
        label="Введите результат",
        help_text="Решите простой пример для подтверждения",
        error_messages={
            "invalid": "Неверный ответ. Попробуйте ещё раз.",
            "required": "Пожалуйста, решите пример.",
        },
    )


class CustomPasswordResetForm(PasswordResetForm):
    """Форма восстановления пароля с капчей"""

    captcha = CaptchaField(
        label="Подтверждение",
        help_text="Решите простой пример для защиты от ботов",
        error_messages={
            "invalid": "Неверный ответ. Попробуйте ещё раз.",
            "required": "Пожалуйста, решите пример.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Стилизуем поле email
        self.fields["email"].widget.attrs.update(
            {
                "class": "w-full p-3 rounded-xl border-2 border-white bg-white bg-opacity-90 "
                "text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 "
                "focus:ring-[#4495D1] transition duration-200 shadow-md text-base "
                "dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400",
                "placeholder": "Электронная почта",
                "type": "email",
                "autocomplete": "email",
            }
        )
