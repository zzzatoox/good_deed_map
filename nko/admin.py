from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms

# from unfold.admin import ModelAdmin
from .models import Region, City, Category, NKO, NKOVersion
from .email_utils import (
    send_application_decision_notification,
    send_transfer_notification_to_new_owner,
)


class ColorPickerWidget(forms.TextInput):
    """Виджет с color picker и текстовым полем для HEX"""

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = "#6CACE4"

        # ID для синхронизации picker и текстового поля
        color_picker_id = f"id_{name}_picker"
        text_input_id = f"id_{name}"

        html = f'''
        <div style="display: flex; align-items: center; gap: 10px;">
            <input type="color" 
                   id="{color_picker_id}" 
                   value="{value}" 
                   style="width: 60px; height: 40px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px;"
                   onchange="document.getElementById('{text_input_id}').value = this.value.toUpperCase()">
            <input type="text" 
                   name="{name}" 
                   id="{text_input_id}" 
                   value="{value}" 
                   maxlength="7" 
                   pattern="^#[0-9A-Fa-f]{{6}}$"
                   style="width: 100px; padding: 8px; font-family: monospace; text-transform: uppercase;"
                   placeholder="#RRGGBB"
                   oninput="this.value = this.value.toUpperCase(); if(/^#[0-9A-F]{{6}}$/.test(this.value)) document.getElementById('{color_picker_id}').value = this.value;">
            <span style="color: #666; font-size: 12px;">Выберите цвет или введите HEX-код</span>
        </div>
        '''
        return mark_safe(html)


class CategoryAdminForm(forms.ModelForm):
    """Форма для Category с color picker"""

    class Meta:
        model = Category
        fields = "__all__"
        widgets = {
            "color": ColorPickerWidget(),
        }


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
    form = CategoryAdminForm
    list_display = ["name", "icon", "color_preview", "color"]
    search_fields = ["name"]
    list_per_page = 20

    def color_preview(self, obj):
        """Показываем превью цвета в списке"""
        return format_html(
            '<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc; border-radius: 4px;"></div>',
            obj.color,
        )

    color_preview.short_description = "Превью"


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
        count_success = 0
        count_error = 0

        for nko in queryset:
            # Проверяем, нет ли у владельца уже другого НКО
            existing_nko = (
                NKO.objects.filter(owner=nko.owner).exclude(pk=nko.pk).first()
            )
            if existing_nko:
                self.message_user(
                    request,
                    f"Невозможно одобрить НКО '{nko.name}': пользователь {nko.owner.get_full_name() or nko.owner.username} "
                    f"уже владеет НКО '{existing_nko.name}'",
                    level="error",
                )
                count_error += 1
                continue

            # Проверяем, нет ли ожидающих заявок на передачу прав этому пользователю
            pending_transfer = NKOVersion.objects.filter(
                new_owner=nko.owner, is_approved=False, is_rejected=False
            ).first()

            if pending_transfer:
                self.message_user(
                    request,
                    f"Внимание: У пользователя {nko.owner.get_full_name() or nko.owner.username} есть ожидающая заявка "
                    f"на передачу прав на НКО '{pending_transfer.nko.name}'. "
                    f"Одобрите или отклоните её перед одобрением нового НКО.",
                    level="warning",
                )
                count_error += 1
                continue

            nko.is_approved = True
            nko.save()
            count_success += 1

        if count_success > 0:
            self.message_user(request, f"Одобрено НКО: {count_success}")
        if count_error > 0:
            self.message_user(
                request, f"Ошибок при одобрении: {count_error}", level="error"
            )

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
        from django.urls import reverse

        # Фильтруем только неодобренные НКО
        unapproved_nko = queryset.filter(is_approved=False)
        if not unapproved_nko.exists():
            self.message_user(
                request, "Можно отклонять только неодобренные НКО", level="warning"
            )
            changelist_url = reverse("admin:nko_nko_changelist")
            return HttpResponseRedirect(changelist_url)

        # Если форма была отправлена
        if request.POST.get("post") == "yes":
            form = RejectVersionForm(request.POST)
            if form.is_valid():
                # Получаем ID выбранных НКО из скрытых полей
                selected_ids = request.POST.getlist("selected_ids")

                if not selected_ids:
                    self.message_user(
                        request, "Ошибка: не выбраны НКО для отклонения", level="error"
                    )
                    changelist_url = reverse("admin:nko_nko_changelist")
                    return HttpResponseRedirect(changelist_url)

                # Получаем заново queryset по ID
                nko_to_delete = NKO.objects.filter(
                    id__in=selected_ids, is_approved=False
                )
                count = nko_to_delete.count()

                # Можно отправить уведомление владельцам НКО о причине отказа
                # Пока просто удаляем
                nko_to_delete.delete()

                self.message_user(request, f"Отклонено и удалено НКО: {count}")
                changelist_url = reverse("admin:nko_nko_changelist")
                return HttpResponseRedirect(changelist_url)
            else:
                # Форма невалидна
                selected_ids = request.POST.getlist("selected_ids")
                nko_list = NKO.objects.filter(id__in=selected_ids, is_approved=False)
                context = {
                    "form": form,
                    "nko_list": nko_list,
                    "selected_ids": selected_ids,
                    "action_name": "reject_nko_action",
                    "opts": self.model._meta,
                    "title": "Укажите причину отказа в создании НКО",
                }
                return render(request, "admin/reject_nko_form.html", context)

        # Показываем форму для ввода причины
        form = RejectVersionForm()
        # Сохраняем ID выбранных НКО
        selected_ids = list(unapproved_nko.values_list("id", flat=True))
        context = {
            "form": form,
            "nko_list": unapproved_nko,
            "selected_ids": selected_ids,
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
        "city_display",
        "status_display",
        "is_current",
        "created_at",
        "change_description_preview",
    ]
    list_filter = ["is_approved", "is_rejected", "is_current", "created_at"]
    search_fields = [
        "nko__name",
        "created_by__username",
        "new_owner__username",
        "city_name",
        "region_name",
    ]
    list_per_page = 20
    actions = ["approve_versions", "reject_versions_action"]
    filter_horizontal = ["categories"]
    readonly_fields = ["rejection_reason_display"]

    def city_display(self, obj):
        """Отображение города (новый или существующий)"""
        if obj.city_name:
            region_text = (
                f", {obj.region_name}" if obj.region_name else " (регион не указан)"
            )
            return format_html(
                '<span style="color: #0066cc;">🏙️ {}{} (новый)</span>',
                obj.city_name,
                region_text,
            )
        elif obj.nko and obj.nko.city:
            return obj.nko.city.name
        return "—"

    city_display.short_description = "Город"

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

            try:
                if version.apply_changes():
                    count_success += 1

                    # Отправляем уведомление автору заявки об одобрении
                    send_application_decision_notification(version, approved=True)

                    # Если это передача прав, отправляем уведомление новому владельцу
                    if version.new_owner:
                        send_transfer_notification_to_new_owner(version)
                else:
                    count_error += 1
            except ValueError as e:
                # Откатываем одобрение если возникла ошибка
                version.is_approved = False
                version.save()
                self.message_user(
                    request,
                    f"Ошибка при одобрении версии {version}: {str(e)}",
                    level="error",
                )
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
        from django.shortcuts import render
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from django.db import transaction

        # Проверяем, была ли отправлена форма с причиной отказа
        if request.POST.get("post") == "yes":
            form = RejectVersionForm(request.POST)

            if not form.is_valid():
                # Форма невалидна, показываем ошибки
                selected_ids = request.POST.getlist("selected_ids")
                versions = NKOVersion.objects.filter(id__in=selected_ids)
                context = {
                    "form": form,
                    "versions": versions,
                    "selected_ids": selected_ids,
                    "action_name": "reject_versions_action",
                    "opts": self.model._meta,
                    "title": "Укажите причину отказа",
                }
                return render(request, "admin/reject_versions_form.html", context)

            if form.is_valid():
                # Получаем ID выбранных версий из скрытых полей
                selected_ids = request.POST.getlist("selected_ids")
                reason = form.cleaned_data["rejection_reason"]

                if not selected_ids:
                    self.message_user(
                        request,
                        "Ошибка: не выбраны версии для отклонения",
                        level="error",
                    )
                    changelist_url = reverse("admin:nko_nkoversion_changelist")
                    return HttpResponseRedirect(changelist_url)

                count = 0
                errors = []

                # Получаем заново queryset по ID
                versions_to_reject = NKOVersion.objects.filter(id__in=selected_ids)

                # Используем транзакцию для атомарности операции
                with transaction.atomic():
                    for version in versions_to_reject:
                        if version.is_approved:
                            self.message_user(
                                request,
                                f"Версия {version} уже была одобрена и не может быть отклонена",
                                level="warning",
                            )
                            continue

                        try:
                            if version.reject_changes(reason):
                                count += 1

                                # Отправляем уведомление автору заявки об отклонении
                                send_application_decision_notification(
                                    version, approved=False
                                )
                            else:
                                errors.append(f"Не удалось отклонить {version}")
                        except Exception as e:
                            errors.append(f"Ошибка при отклонении {version}: {str(e)}")

                if count > 0:
                    self.message_user(request, f"Отклонено заявок: {count}")

                if errors:
                    for error in errors:
                        self.message_user(request, error, level="error")

                # Редирект на список версий
                changelist_url = reverse("admin:nko_nkoversion_changelist")
                return HttpResponseRedirect(changelist_url)

        # Показываем форму для ввода причины
        form = RejectVersionForm()
        # Сохраняем ID выбранных версий
        selected_ids = list(queryset.values_list("id", flat=True))
        context = {
            "form": form,
            "versions": queryset,
            "selected_ids": selected_ids,
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
            try:
                if obj.apply_changes():
                    self.message_user(request, f"Версия {obj} одобрена и применена")
                else:
                    self.message_user(
                        request, f"Ошибка при применении версии {obj}", level="error"
                    )
            except ValueError as e:
                # Откатываем одобрение
                obj.is_approved = False
                obj.save()
                self.message_user(request, f"Ошибка: {str(e)}", level="error")

        # Если версия была отклонена
        if obj.is_rejected and (not prev or not prev.is_rejected):
            obj.is_approved = False
            # Проверяем наличие причины отказа
            if not obj.rejection_reason:
                self.message_user(
                    request, "Ошибка: необходимо указать причину отказа", level="error"
                )
                obj.is_rejected = False
                obj.save()
                return

            # Снимаем флаг ожидающих изменений только если больше нет других ожидающих версий
            nko = obj.nko
            pending_versions = NKOVersion.objects.filter(
                nko=nko, is_approved=False, is_rejected=False
            ).exclude(pk=obj.pk)

            if not pending_versions.exists():
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
            (
                "Статус",
                {
                    "fields": (
                        "is_approved",
                        "is_rejected",
                        "is_current",
                        "rejection_reason",
                    )
                },
            ),
            (
                "Данные НКО",
                {
                    "fields": (
                        "name",
                        "categories",
                        "city_name",
                        "region_name",
                        "description",
                        "volunteer_functions",
                        "phone",
                        "address",
                        "latitude",
                        "longitude",
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
        # Если версия одобрена, блокируем изменение статуса отклонения
        if obj and obj.is_approved:
            readonly.extend(["is_rejected", "rejection_reason"])
        return readonly
