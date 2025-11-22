from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, views as auth_views
from django.conf import settings
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from .forms import UserRegisterForm, CustomAuthenticationForm, ResendConfirmationForm
from .models import EmailConfirmationToken


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Деактивируем пользователя до подтверждения email
            user.save()

            # Создаем токен подтверждения
            token = EmailConfirmationToken.objects.create(user=user)

            # Формируем ссылку подтверждения
            confirmation_url = request.build_absolute_uri(
                reverse("confirm_email", kwargs={"token": token.token})
            )

            # Отправляем письмо
            try:
                send_mail(
                    subject="Подтверждение регистрации на Карте добрых дел",
                    message=f"""Здравствуйте, {user.get_full_name() or user.username}!

Спасибо за регистрацию на сайте "Карта добрых дел".

Для завершения регистрации и активации аккаунта, пожалуйста, перейдите по ссылке:
{confirmation_url}

Ссылка действительна в течение 24 часов.

Если вы не регистрировались на нашем сайте, просто проигнорируйте это письмо.

С уважением,
Команда "Карта добрых дел"
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f"На адрес {user.email} отправлено письмо с подтверждением. "
                    f"Пожалуйста, проверьте почту и перейдите по ссылке для активации аккаунта.",
                )
            except Exception as e:
                messages.error(
                    request,
                    "Ошибка при отправке письма подтверждения. Пожалуйста, обратитесь к администратору.",
                )
                # Можно добавить логирование ошибки
                print(f"Email sending error: {e}")

            return render(
                request,
                "registration/email_confirmation_sent.html",
                {"email": user.email},
            )
    else:
        form = UserRegisterForm()

    return render(request, "registration/register.html", {"form": form})


def confirm_email(request, token):
    """Подтверждение email по токену"""
    token_obj = get_object_or_404(EmailConfirmationToken, token=token)

    if not token_obj.is_valid():
        messages.error(
            request,
            "Ссылка подтверждения истекла. Пожалуйста, зарегистрируйтесь заново.",
        )
        return redirect("register")

    user = token_obj.user
    user.is_active = True
    user.save()

    # Обновляем профиль
    if hasattr(user, "profile"):
        user.profile.email_confirmed = True
        user.profile.save()

    # Удаляем использованный токен
    token_obj.delete()

    return render(request, "registration/email_confirmed.html")


def login_view(request, *args, **kwargs):
    view = auth_views.LoginView.as_view(
        template_name="registration/login.html",
        authentication_form=CustomAuthenticationForm,
    )
    return view(request, *args, **kwargs)


@require_http_methods(["GET", "POST"])
def resend_confirmation(request):
    """Повторная отправка письма подтверждения"""
    if request.method == "POST":
        form = ResendConfirmationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            try:
                user = User.objects.get(email=email, is_active=False)

                # Удаляем старые токены для этого пользователя
                EmailConfirmationToken.objects.filter(user=user).delete()

                # Создаем новый токен
                token = EmailConfirmationToken.objects.create(user=user)

                # Формируем ссылку подтверждения
                confirmation_url = request.build_absolute_uri(
                    reverse("confirm_email", kwargs={"token": token.token})
                )

                # Отправляем письмо
                try:
                    send_mail(
                        subject="Повторное подтверждение регистрации на Карте добрых дел",
                        message=f"""Здравствуйте, {user.get_full_name() or user.username}!

Вы запросили повторную отправку письма подтверждения регистрации.

Для завершения регистрации и активации аккаунта, пожалуйста, перейдите по ссылке:
{confirmation_url}

Ссылка действительна в течение 24 часов.

Если вы не запрашивали повторную отправку, просто проигнорируйте это письмо.

С уважением,
Команда "Карта добрых дел"
""",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    return render(
                        request,
                        "registration/email_confirmation_sent.html",
                        {"email": user.email},
                    )
                except Exception as e:
                    messages.error(
                        request,
                        "Ошибка при отправке письма подтверждения. Пожалуйста, обратитесь к администратору.",
                    )
                    print(f"Email sending error: {e}")

            except User.DoesNotExist:
                # Не сообщаем, что пользователь не найден (безопасность)
                pass

            # В любом случае показываем страницу "письмо отправлено"
            return render(
                request, "registration/email_confirmation_sent.html", {"email": email}
            )
    else:
        form = ResendConfirmationForm()

    return render(request, "registration/resend_confirmation.html", {"form": form})


def logout_view(request):
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    logout(request)
    return redirect(getattr(settings, "LOGOUT_REDIRECT_URL", "/"))
