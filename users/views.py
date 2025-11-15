from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseNotAllowed
from .forms import UserRegisterForm


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            raw_password = form.cleaned_data.get("password1")
            # Authenticate using the project's authentication backends (email-only)
            auth_user = authenticate(request, username=user.email, password=raw_password)
            if auth_user is None:
                # Fallback: set backend dynamically from settings to avoid hardcoding
                from django.conf import settings

                backend_path = settings.AUTHENTICATION_BACKENDS[0]
                user.backend = backend_path
                auth_user = user

            login(request, auth_user)

            messages.success(
                request,
                f"Аккаунт для {user.get_full_name()} успешно создан! "
                f"Теперь вы можете добавить свою НКО на карту.",
            )
            return redirect("index")
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = UserRegisterForm()

    return render(request, "registration/register.html", {"form": form})


def logout_view(request):
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect(getattr(settings, "LOGOUT_REDIRECT_URL", "/"))
