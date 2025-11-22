from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    """Инлайн для отображения профиля вместе с пользователем"""

    model = Profile
    can_delete = False
    verbose_name = "Профиль"
    verbose_name_plural = "Профиль"
    fields = ("patronymic", "phone_number", "email_confirmed")
    readonly_fields = ("email_confirmed",)


class CustomUserAdmin(BaseUserAdmin):
    """Кастомная админка для пользователей с фильтрами"""

    inlines = (ProfileInline,)

    # Фильтры в правой панели
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
        "groups",
    )

    # Поля для отображения в списке
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "date_joined",
    )

    # Поля для поиска
    search_fields = ("username", "email", "first_name", "last_name")

    # Сортировка по умолчанию (новые сверху)
    ordering = ("-date_joined",)

    # Дата иерархия для быстрой навигации
    date_hierarchy = "date_joined"


# Перерегистрируем User с новой админкой
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
