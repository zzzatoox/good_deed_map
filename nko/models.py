from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import RegexValidator
import re


# Валидатор для российского номера телефона
phone_regex = RegexValidator(
    regex=r"^\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$",
    message="Неверный формат номера телефона. Используйте российский номер: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX",
)


# Create your models here.
class Region(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название региона")

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название города")
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name="Регион")

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"

    def __str__(self):
        return f"{self.name}, {self.region}"


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Иконка")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class NKO(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название НКО")
    categories = models.ManyToManyField(
        Category, verbose_name="Направления деятельности"
    )
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город")

    description = models.TextField(verbose_name="Краткое описание деятельности")
    volunteer_functions = models.TextField(
        blank=True, verbose_name="Функционал волонтеров"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Контактный телефон",
        validators=[phone_regex],
        help_text="Формат: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX",
    )
    address = models.TextField(blank=True, verbose_name="Адрес")

    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")

    logo = models.ImageField(
        upload_to="nko_logos/", blank=True, null=True, verbose_name="Логотип"
    )

    website = models.URLField(blank=True, verbose_name="Сайт")
    vk_link = models.URLField(blank=True, verbose_name="ВКонтакте")
    telegram_link = models.URLField(blank=True, verbose_name="Telegram")
    other_social = models.URLField(blank=True, verbose_name="Другие соцсети")

    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_approved = models.BooleanField(default=False, verbose_name="Прошло модерацию")
    has_pending_changes = models.BooleanField(
        default=False, verbose_name="Есть ожидающие изменения"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "НКО"
        verbose_name_plural = "НКО"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("nko_detail", kwargs={"pk": self.pk})

    @property
    def region(self):
        return self.city.region

    def get_categories_list(self):
        return ", ".join([category.name for category in self.categories.all()])

    def get_pending_version(self):
        """Получить ожидающую модерации версию (не отклоненную)"""
        return self.versions.filter(is_approved=False, is_rejected=False).first()


class NKOVersion(models.Model):
    nko = models.ForeignKey(
        NKO, on_delete=models.CASCADE, related_name="versions", verbose_name="НКО"
    )

    name = models.CharField(max_length=200, verbose_name="Название НКО")
    categories = models.ManyToManyField(
        Category, verbose_name="Направления деятельности"
    )
    description = models.TextField(verbose_name="Краткое описание деятельности")
    volunteer_functions = models.TextField(
        blank=True, verbose_name="Функционал волонтеров"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Контактный телефон",
        validators=[phone_regex],
        help_text="Формат: +7 (XXX) XXX-XX-XX или 8 (XXX) XXX-XX-XX",
    )
    address = models.TextField(blank=True, verbose_name="Адрес")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")
    logo = models.ImageField(
        upload_to="nko_logos/versions/", blank=True, null=True, verbose_name="Логотип"
    )
    website = models.URLField(blank=True, verbose_name="Сайт")
    vk_link = models.URLField(blank=True, verbose_name="ВКонтакте")
    telegram_link = models.URLField(blank=True, verbose_name="Telegram")
    other_social = models.URLField(blank=True, verbose_name="Другие соцсети")

    new_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Новый владелец",
        related_name="nko_transfers",
    )

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Автор изменений"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания версии"
    )
    is_approved = models.BooleanField(default=False, verbose_name="Версия одобрена")
    is_rejected = models.BooleanField(default=False, verbose_name="Версия отклонена")
    rejection_reason = models.TextField(blank=True, verbose_name="Причина отказа")
    is_current = models.BooleanField(default=False, verbose_name="Текущая версия")
    change_description = models.TextField(blank=True, verbose_name="Описание изменений")

    class Meta:
        verbose_name = "Версия НКО"
        verbose_name_plural = "Версии НКО"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Версия {self.nko.name} от {self.created_at}"

    def apply_changes(self):
        """Применить одобренные изменения к основной записи НКО"""
        if not self.is_approved:
            return False

        nko = self.nko

        # Проверка при передаче прав: новый владелец не должен иметь других НКО
        if self.new_owner:
            existing_nko = (
                NKO.objects.filter(owner=self.new_owner).exclude(pk=nko.pk).first()
            )
            if existing_nko:
                # Отменяем применение изменений
                raise ValueError(
                    f"Невозможно передать права: пользователь {self.new_owner.get_full_name() or self.new_owner.username} "
                    f"уже является владельцем НКО '{existing_nko.name}'. "
                    f"Один пользователь может владеть только одним НКО."
                )

        nko.name = self.name
        nko.description = self.description
        nko.volunteer_functions = self.volunteer_functions
        nko.phone = self.phone
        nko.address = self.address
        nko.latitude = self.latitude
        nko.longitude = self.longitude
        nko.website = self.website
        nko.vk_link = self.vk_link
        nko.telegram_link = self.telegram_link
        nko.other_social = self.other_social

        if self.logo:
            nko.logo = self.logo

        if self.new_owner:
            nko.owner = self.new_owner

        nko.categories.set(self.categories.all())

        nko.has_pending_changes = False
        nko.save()

        self.is_current = True
        self.save()

        NKOVersion.objects.filter(nko=nko).exclude(pk=self.pk).update(is_current=False)

        return True

    def reject_changes(self, reason=""):
        """Отклонить заявку с указанием причины"""
        # Используем update для более надежного обновления
        NKOVersion.objects.filter(pk=self.pk).update(
            is_rejected=True, is_approved=False, rejection_reason=reason
        )

        # Перезагружаем объект из БД
        self.refresh_from_db()

        # Проверяем, что изменения действительно сохранились
        if not self.is_rejected or self.is_approved:
            return False

        # Снимаем флаг ожидающих изменений с основной записи НКО
        # только если больше нет других ожидающих версий
        nko = self.nko
        pending_versions = NKOVersion.objects.filter(
            nko=nko, is_approved=False, is_rejected=False
        ).exclude(pk=self.pk)

        if not pending_versions.exists():
            NKO.objects.filter(pk=nko.pk).update(has_pending_changes=False)

        return True
