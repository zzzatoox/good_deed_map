from django.contrib import admin
from django.utils.html import format_html

# from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from .models import Region, City, Category, NKO, NKOVersion


# Register your models here.
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "region"]
    list_filter = ["region"]
    search_fields = ["name", "region__name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon"]
    search_fields = ["name"]
    list_per_page = 20


@admin.register(NKO)
class NKOAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "get_categories",
        "city",
        "owner",
        "is_approved",
        "created_at",
    ]
    list_filter = [
        "is_approved",
        "categories",
        "city",
        "created_at",
    ]
    search_fields = ["name", "description"]
    list_editable = ["is_approved"]
    filter_horizontal = ["categories"]
    list_per_page = 20
    actions = ["approve_nko", "disapprove_nko"]

    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])

    get_categories.short_description = "Категории"

    def approve_nko(self, request, queryset):
        queryset.update(is_approved=True)

    approve_nko.short_description = "Одобрить выбранные НКО"

    def disapprove_nko(self, request, queryset):
        queryset.update(is_approved=False)

    disapprove_nko.short_description = "Снять одобрение с выбранных НКО"


@admin.register(NKOVersion)
class NKOVersionAdmin(admin.ModelAdmin):
    list_display = [
        "nko",
        "created_by",
        "new_owner",
        "is_approved",
        "is_current",
        "created_at",
        "change_description_preview",
    ]
    list_filter = ["is_approved", "is_current", "created_at"]
    search_fields = ["nko__name", "created_by__username", "new_owner__username"]
    list_editable = ["is_approved"]
    list_per_page = 20
    actions = ["approve_versions", "reject_versions"]
    filter_horizontal = ["categories"]

    def change_description_preview(self, obj):
        return (
            obj.change_description[:50] + "..."
            if len(obj.change_description) > 50
            else obj.change_description
        )

    change_description_preview.short_description = "Описание изменений"

    def approve_versions(self, request, queryset):
        for version in queryset:
            version.is_approved = True
            version.save()
            if version.apply_changes():
                self.message_user(request, f"Версия {version} одобрена и применена")
            else:
                self.message_user(
                    request, f"Ошибка при применении версии {version}", level="error"
                )

    approve_versions.short_description = "Одобрить и применить выбранные версии"

    def reject_versions(self, request, queryset):
        for version in queryset:
            version.delete()
        self.message_user(request, f"{queryset.count()} версий отклонено и удалено")

    reject_versions.short_description = "Отклонить и удалить выбранные версии"

    def save_model(self, request, obj, form, change):
        prev = None
        if change:
            try:
                prev = NKOVersion.objects.get(pk=obj.pk)
            except NKOVersion.DoesNotExist:
                prev = None

        super().save_model(request, obj, form, change)

        if obj.is_approved and (not prev or not prev.is_approved):
            if obj.apply_changes():
                self.message_user(request, f"Версия {obj} одобрена и применена")
            else:
                self.message_user(
                    request, f"Ошибка при применении версии {obj}", level="error"
                )
