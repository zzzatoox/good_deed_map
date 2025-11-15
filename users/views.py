from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, views as auth_views
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseNotAllowed
from .forms import UserRegisterForm, CustomAuthenticationForm


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            raw_password = form.cleaned_data.get("password1")
            auth_user = authenticate(
                request, username=user.email, password=raw_password
            )
            if auth_user is None:
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


def login_view(request, *args, **kwargs):
    view = auth_views.LoginView.as_view(
        template_name="registration/login.html",
        authentication_form=CustomAuthenticationForm,
    )
    return view(request, *args, **kwargs)


def logout_view(request):
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    logout(request)
    return redirect(getattr(settings, "LOGOUT_REDIRECT_URL", "/"))
