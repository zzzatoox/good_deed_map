from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


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
    category = models.ManyToManyField(Category, verbose_name="Направления деятельности")
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город")

    description = models.TextField(verbose_name="Краткое описание деятельности")
    volunteer_functions = models.TextField(verbose_name="Функционал волонтеров")

    phone = models.CharField(
        max_length=20, blank=True, verbose_name="Контактный телефон"
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
        """Возвращает список категорий для удобного отображения"""
        return ", ".join([category.name for category in self.categories.all()])


class NKOVersion(models.Model):
    """Модель для хранения версий НКО (ожидающих модерации)"""

    nko = models.ForeignKey(
        NKO, on_delete=models.CASCADE, related_name="versions", verbose_name="НКО"
    )

    name = models.CharField(max_length=200, verbose_name="Название НКО")
    categories = models.ManyToManyField(
        Category, verbose_name="Направления деятельности"
    )
    description = models.TextField(verbose_name="Краткое описание деятельности")
    volunteer_functions = models.TextField(verbose_name="Функционал волонтеров")
    phone = models.CharField(
        max_length=20, blank=True, verbose_name="Контактный телефон"
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
    is_current = models.BooleanField(default=False, verbose_name="Текущая версия")
    change_description = models.TextField(blank=True, verbose_name="Описание изменений")

    class Meta:
        verbose_name = "Версия НКО"
        verbose_name_plural = "Версии НКО"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Версия {self.nko.name} от {self.created_at}"

    def apply_changes(self):
        """Применяет изменения из этой версии к основному НКО"""
        if not self.is_approved:
            return False

        nko = self.nko

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
