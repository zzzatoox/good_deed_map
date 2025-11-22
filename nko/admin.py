from django.contrib import admin
from django.utils.html import format_html
from django import forms

# from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from .models import Region, City, Category, NKO, NKOVersion


class RejectVersionForm(forms.Form):
    """Форма для указания причины отказа"""

    rejection_reason = forms.CharField(
        label="Причина отказа",
        widget=forms.Textarea(attrs={"rows": 4, "cols": 60}),
        required=True,
        help_text="Укажите причину отказа. Эта информация будет доступна владельцу НКО.",
    )


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
        "has_pending_changes",
        "created_at",
    ]
    list_filter = [
        "is_approved",
        "has_pending_changes",
        "categories",
        "city",
        "created_at",
    ]
    search_fields = ["name", "description"]
    list_editable = ["is_approved"]
    filter_horizontal = ["categories"]
    list_per_page = 20
    actions = ["approve_nko", "disapprove_nko", "reject_nko_action"]

    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])

    get_categories.short_description = "Категории"

    def approve_nko(self, request, queryset):
        """Одобрить выбранные НКО"""
        count = queryset.update(is_approved=True)
        self.message_user(request, f"Одобрено НКО: {count}")

    approve_nko.short_description = "✓ Одобрить выбранные НКО"

    def disapprove_nko(self, request, queryset):
        """Снять одобрение с выбранных НКО (не удаляет)"""
        count = queryset.update(is_approved=False)
        self.message_user(request, f"Снято одобрение с НКО: {count}")

    disapprove_nko.short_description = "⏸ Снять одобрение с выбранных НКО"

    def reject_nko_action(self, request, queryset):
        """Отклонить и удалить неодобренные НКО"""
        from django.shortcuts import render
        from django.http import HttpResponseRedirect

        # Фильтруем только неодобренные НКО
        unapproved_nko = queryset.filter(is_approved=False)
        if not unapproved_nko.exists():
            self.message_user(
                request, "Можно отклонять только неодобренные НКО", level="warning"
            )
            return HttpResponseRedirect(request.get_full_path())

        # Если форма была отправлена
        if "apply" in request.POST:
            form = RejectVersionForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data["rejection_reason"]
                count = unapproved_nko.count()

                # Можно отправить уведомление владельцам НКО о причине отказа
                # Пока просто удаляем
                unapproved_nko.delete()

                self.message_user(request, f"Отклонено и удалено НКО: {count}")
                return HttpResponseRedirect(request.get_full_path())

        # Показываем форму для ввода причины
        form = RejectVersionForm()
        context = {
            "form": form,
            "nko_list": unapproved_nko,
            "action_name": "reject_nko_action",
            "opts": self.model._meta,
            "title": "Укажите причину отказа в создании НКО",
        }
        return render(request, "admin/reject_nko_form.html", context)

    reject_nko_action.short_description = "✗ Отклонить и удалить неодобренные НКО"


@admin.register(NKOVersion)
class NKOVersionAdmin(admin.ModelAdmin):
    list_display = [
        "nko",
        "created_by",
        "new_owner",
        "status_display",
        "is_current",
        "created_at",
        "change_description_preview",
    ]
    list_filter = ["is_approved", "is_rejected", "is_current", "created_at"]
    search_fields = ["nko__name", "created_by__username", "new_owner__username"]
    list_per_page = 20
    actions = ["approve_versions", "reject_versions_action"]
    filter_horizontal = ["categories"]
    readonly_fields = ["rejection_reason_display"]

    def status_display(self, obj):
        """Отображение статуса заявки"""
        if obj.is_approved:
            return format_html('<span style="color: green;">✓ Одобрено</span>')
        elif obj.is_rejected:
            return format_html('<span style="color: red;">✗ Отклонено</span>')
        else:
            return format_html('<span style="color: orange;">⏳ На модерации</span>')

    status_display.short_description = "Статус"

    def rejection_reason_display(self, obj):
        """Отображение причины отказа"""
        if obj.rejection_reason:
            return format_html(
                '<div style="background: #fff3cd; padding: 10px; border-radius: 5px;">{}</div>',
                obj.rejection_reason,
            )
        return "—"

    rejection_reason_display.short_description = "Причина отказа"

    def change_description_preview(self, obj):
        return (
            obj.change_description[:50] + "..."
            if len(obj.change_description) > 50
            else obj.change_description
        )

    change_description_preview.short_description = "Описание изменений"

    def approve_versions(self, request, queryset):
        """Одобрить и применить выбранные версии"""
        count_success = 0
        count_error = 0

        for version in queryset:
            if version.is_rejected:
                self.message_user(
                    request,
                    f"Версия {version} уже была отклонена и не может быть одобрена",
                    level="warning",
                )
                continue

            version.is_approved = True
            version.is_rejected = False
            version.rejection_reason = ""
            version.save()

            if version.apply_changes():
                count_success += 1
            else:
                count_error += 1

        if count_success > 0:
            self.message_user(request, f"Успешно одобрено и применено: {count_success}")
        if count_error > 0:
            self.message_user(
                request, f"Ошибок при применении: {count_error}", level="error"
            )

    approve_versions.short_description = "✓ Одобрить и применить выбранные версии"

    def reject_versions_action(self, request, queryset):
        """Отклонить выбранные версии с указанием причины"""
        from django.shortcuts import render, redirect
        from django.urls import path, reverse
        from django.http import HttpResponseRedirect

        # Если форма была отправлена
        if "apply" in request.POST:
            form = RejectVersionForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data["rejection_reason"]
                count = 0

                for version in queryset:
                    if version.is_approved:
                        self.message_user(
                            request,
                            f"Версия {version} уже была одобрена и не может быть отклонена",
                            level="warning",
                        )
                        continue

                    if version.reject_changes(reason):
                        count += 1

                self.message_user(request, f"Отклонено заявок: {count}")
                return HttpResponseRedirect(request.get_full_path())

        # Показываем форму для ввода причины
        form = RejectVersionForm()
        context = {
            "form": form,
            "versions": queryset,
            "action_name": "reject_versions_action",
            "opts": self.model._meta,
            "title": "Укажите причину отказа",
        }
        return render(request, "admin/reject_versions_form.html", context)

    reject_versions_action.short_description = "✗ Отклонить выбранные версии"

    def save_model(self, request, obj, form, change):
        """Обработка сохранения модели в админке"""
        prev = None
        if change:
            try:
                prev = NKOVersion.objects.get(pk=obj.pk)
            except NKOVersion.DoesNotExist:
                prev = None

        super().save_model(request, obj, form, change)

        # Если версия была одобрена
        if obj.is_approved and (not prev or not prev.is_approved):
            obj.is_rejected = False
            obj.rejection_reason = ""
            if obj.apply_changes():
                self.message_user(request, f"Версия {obj} одобрена и применена")
            else:
                self.message_user(
                    request, f"Ошибка при применении версии {obj}", level="error"
                )

        # Если версия была отклонена
        if obj.is_rejected and (not prev or not prev.is_rejected):
            obj.is_approved = False
            nko = obj.nko
            nko.has_pending_changes = False
            nko.save()
            self.message_user(request, f"Версия {obj} отклонена")

    def get_fieldsets(self, request, obj=None):
        """Настройка группировки полей в форме редактирования"""
        fieldsets = [
            (
                "Основная информация",
                {"fields": ("nko", "created_by", "created_at", "change_description")},
            ),
            ("Статус", {"fields": ("is_approved", "is_rejected", "is_current")}),
            (
                "Данные НКО",
                {
                    "fields": (
                        "name",
                        "categories",
                        "description",
                        "volunteer_functions",
                        "phone",
                        "address",
                        "latitude",
                        "longitude",
                        "logo",
                    )
                },
            ),
            (
                "Контакты и соцсети",
                {"fields": ("website", "vk_link", "telegram_link", "other_social")},
            ),
            ("Передача прав", {"fields": ("new_owner",)}),
        ]

        if obj and obj.is_rejected:
            fieldsets.insert(
                2, ("Причина отказа", {"fields": ("rejection_reason_display",)})
            )

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        """Поля только для чтения"""
        readonly = ["created_at", "created_by", "nko"]
        if obj and obj.is_rejected:
            readonly.append("rejection_reason_display")
        return readonly
