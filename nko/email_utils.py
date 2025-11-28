"""
Утилиты для отправки email-уведомлений
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.html import strip_tags


def send_new_application_notification(nko_version):
    """
    Отправить уведомление администраторам о новой заявке НКО

    Args:
        nko_version: объект NKOVersion - новая заявка на создание/изменение НКО
    """
    print(
        f"[DEBUG send_new_application_notification] Called for NKO: {nko_version.nko.name}"
    )

    # Получаем всех администраторов, которые хотят получать уведомления
    admin_users = User.objects.filter(
        is_staff=True, is_active=True, profile__receive_nko_notifications=True
    ).exclude(email="")

    print(
        f"[DEBUG send_new_application_notification] Found {admin_users.count()} admin users with notifications enabled"
    )
    for admin in admin_users:
        print(
            f"  - {admin.username} ({admin.email}), is_staff={admin.is_staff}, receive_nko_notifications={admin.profile.receive_nko_notifications}"
        )

    # Определяем тип заявки
    is_new_nko = not nko_version.nko.is_approved
    is_transfer = nko_version.new_owner is not None

    if is_transfer:
        application_type = "передачу прав владения НКО"
    elif is_new_nko:
        application_type = "создание нового НКО"
    else:
        application_type = "изменение данных НКО"

    # Формируем контекст для письма
    context = {
        "nko_version": nko_version,
        "nko": nko_version.nko,
        "application_type": application_type,
        "is_new_nko": is_new_nko,
        "is_transfer": is_transfer,
        "author": nko_version.created_by,
        "admin_url": f"{settings.SITE_URL}/admin/nko/nkoversion/{nko_version.id}/change/",
    }

    # Рендерим HTML-шаблон
    html_message = render_to_string(
        "nko/email/new_application_notification.html", context
    )
    plain_message = strip_tags(html_message)

    subject = f"Новая заявка: {application_type} - {nko_version.nko.name}"

    # Формируем список получателей. Если нет админов с включёнными уведомлениями,
    # пытаемся отправить суперюзерам или использовать settings.ADMINS как запасной вариант.
    recipient_list = [user.email for user in admin_users]

    if not recipient_list:
        # Попробуем суперпользователей
        super_users = User.objects.filter(is_superuser=True, is_active=True).exclude(
            email=""
        )
        recipient_list = [u.email for u in super_users]

    if not recipient_list and getattr(settings, "ADMINS", None):
        try:
            recipient_list = [
                a[1] for a in settings.ADMINS if a and len(a) > 1 and a[1]
            ]
        except Exception:
            recipient_list = []

    if not recipient_list:
        # Нечего отправлять — логируем и выходим
        print(
            "send_new_application_notification: no recipients found for new application notification"
        )
        return

    # Логируем получателей для диагностики
    try:
        print(f"send_new_application_notification: sending to: {recipient_list}")
    except Exception:
        pass

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        print(
            f"send_new_application_notification: email sent successfully to {len(recipient_list)} recipients"
        )
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка отправки email администраторам: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")


def send_application_decision_notification(nko_version, approved=True):
    """
    Отправить уведомление пользователю о решении по заявке

    Args:
        nko_version: объект NKOVersion - заявка
        approved: bool - одобрена (True) или отклонена (False)
    """
    # Получаем автора заявки
    user = nko_version.created_by

    if not user.email:
        return

    # Определяем тип заявки
    is_new_nko = not nko_version.nko.is_approved
    is_transfer = nko_version.new_owner is not None

    if is_transfer:
        application_type = "передачу прав владения НКО"
    elif is_new_nko:
        application_type = "создание нового НКО"
    else:
        application_type = "изменение данных НКО"

    # Формируем контекст для письма
    context = {
        "nko_version": nko_version,
        "nko": nko_version.nko,
        "application_type": application_type,
        "is_new_nko": is_new_nko,
        "is_transfer": is_transfer,
        "approved": approved,
        "user": user,
        "rejection_reason": nko_version.rejection_reason if not approved else None,
    }

    # Выбираем шаблон в зависимости от решения
    template_name = (
        "nko/email/application_approved.html"
        if approved
        else "nko/email/application_rejected.html"
    )

    # Рендерим HTML-шаблон
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    # Формируем тему письма
    status = "одобрена" if approved else "отклонена"
    subject = f"Ваша заявка {status}: {application_type} - {nko_version.nko.name}"

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка отправки email пользователю {user.email}: {e}")


def send_transfer_notification_to_new_owner(nko_version):
    """
    Отправить уведомление новому владельцу о передаче прав

    Args:
        nko_version: объект NKOVersion с заполненным полем new_owner
    """
    if not nko_version.new_owner or not nko_version.new_owner.email:
        return

    # Формируем контекст для письма
    context = {
        "nko_version": nko_version,
        "nko": nko_version.nko,
        "new_owner": nko_version.new_owner,
        "previous_owner": nko_version.nko.owner,
    }

    # Рендерим HTML-шаблон
    html_message = render_to_string("nko/email/transfer_notification.html", context)
    plain_message = strip_tags(html_message)

    subject = f"Вам переданы права на НКО: {nko_version.nko.name}"

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[nko_version.new_owner.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(
            f"Ошибка отправки email новому владельцу {nko_version.new_owner.email}: {e}"
        )
