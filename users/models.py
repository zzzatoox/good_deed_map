from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import timedelta


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    email_confirmed = models.BooleanField(
        default=False, verbose_name="Email подтвержден"
    )
    patronymic = models.CharField(max_length=150, blank=True, verbose_name="Отчество")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"Профиль {self.full_name or self.user.username}"

    @property
    def full_name(self):
        """Возвращает полное имя пользователя"""
        parts = []
        if self.user.last_name:
            parts.append(self.user.last_name)
        if self.user.first_name:
            parts.append(self.user.first_name)
        if self.patronymic:
            parts.append(self.patronymic)
        full = " ".join(parts).strip()
        return full if full else None


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()


class EmailConfirmationToken(models.Model):
    """Токен для подтверждения email при регистрации"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    token = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, verbose_name="Токен"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Токен подтверждения email"
        verbose_name_plural = "Токены подтверждения email"

    def __str__(self):
        return f"Токен для {self.user.username}"

    def is_valid(self):
        """Проверка, что токен еще действителен (24 часа)"""
        expiration_time = self.created_at + timedelta(hours=24)
        return timezone.now() < expiration_time
