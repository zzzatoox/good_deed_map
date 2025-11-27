from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordResetForm,
)
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
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


class CustomPasswordResetTsxForm(PasswordResetForm):
    """Форма восстановления пароля с капчей для TSX версии"""

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

    def save(
        self,
        domain_override=None,
        subject_template_name="registration/password_reset_subject.txt",
        email_template_name="registration/password_reset_email.html",
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """
        Override save to use tsx URL names in password reset email
        """
        if extra_email_context is None:
            extra_email_context = {}

        # Add flag to use tsx URLs in email template
        extra_email_context["use_tsx_urls"] = True

        return super().save(
            domain_override=domain_override,
            subject_template_name=subject_template_name,
            email_template_name=email_template_name,
            use_https=use_https,
            token_generator=token_generator,
            from_email=from_email,
            request=request,
            html_email_template_name=html_email_template_name,
            extra_email_context=extra_email_context,
        )


class UserRegisterTsxForm(UserCreationForm):
    """Форма регистрации для TSX версии с одним полем ФИО"""

    email = forms.EmailField(
        required=True,
        label="Email",
    )
    full_name = forms.CharField(
        max_length=200,
        required=True,
        label="ФИО",
        help_text="Введите Фамилию, Имя и Отчество через пробел",
    )
    captcha = CaptchaField(
        label="Подтверждение",
        error_messages={
            "invalid": "Неверный ответ. Попробуйте ещё раз.",
            "required": "Пожалуйста, решите пример.",
        },
    )

    class Meta:
        model = User
        fields = [
            "email",
            "full_name",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Общие стили для всех полей
        common_classes = (
            "w-full pl-11 pr-4 py-3 bg-white dark:bg-slate-800 text-slate-800 "
            "dark:text-slate-200 border border-slate-300 dark:border-slate-700 "
            "rounded-lg focus:ring-brand-green focus:border-brand-green outline-none transition"
        )

        # Применяем стили к полям
        if "full_name" in self.fields:
            self.fields["full_name"].widget.attrs.update(
                {"class": common_classes, "placeholder": "Фамилия Имя Отчество"}
            )

        if "email" in self.fields:
            self.fields["email"].widget.attrs.update(
                {
                    "class": common_classes,
                    "placeholder": "you@example.com",
                    "type": "email",
                }
            )

        if "password1" in self.fields:
            self.fields["password1"].widget.attrs.update(
                {"class": common_classes, "placeholder": "••••••••"}
            )

        if "password2" in self.fields:
            self.fields["password2"].widget.attrs.update(
                {"class": common_classes, "placeholder": "••••••••"}
            )

        if "captcha" in self.fields:
            self.fields["captcha"].widget.attrs.update(
                {
                    "class": "w-full pl-4 pr-4 py-3 bg-white dark:bg-slate-800 text-slate-800 "
                    "dark:text-slate-200 border border-slate-300 dark:border-slate-700 "
                    "rounded-lg focus:ring-brand-green focus:border-brand-green outline-none transition"
                }
            )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким Email уже существует")
        return email

    def clean_full_name(self):
        """Валидация и разбор ФИО"""
        full_name = self.cleaned_data.get("full_name")
        if not full_name:
            return full_name

        full_name = full_name.strip()

        import re

        if not re.match(r"^[а-яёА-ЯЁa-zA-Z\-\s]+$", full_name):
            raise forms.ValidationError(
                "ФИО может содержать только буквы (кириллица или латиница), пробелы и дефис."
            )

        # Разбиваем на части
        parts = [part.strip() for part in full_name.split() if part.strip()]

        if len(parts) < 2:
            raise forms.ValidationError(
                "Пожалуйста, введите как минимум Фамилию и Имя."
            )

        # Форматируем каждую часть (первая буква заглавная)
        formatted_parts = []
        for part in parts:
            formatted_part = "-".join(word.capitalize() for word in part.split("-"))
            formatted_parts.append(formatted_part)

        return " ".join(formatted_parts)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]

        # Разбираем ФИО
        full_name = self.cleaned_data["full_name"]
        parts = full_name.split()

        user.last_name = parts[0] if len(parts) > 0 else ""
        user.first_name = parts[1] if len(parts) > 1 else ""

        patronymic = parts[2] if len(parts) > 2 else ""

        if commit:
            user.save()
            profile = user.profile
            profile.patronymic = patronymic
            profile.save()

        return user
