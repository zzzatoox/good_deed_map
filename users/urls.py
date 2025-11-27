from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm

app_name = "users"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=CustomAuthenticationForm,
        ),
        name="login",
    ),
    path(
        "login_tsx/",
        auth_views.LoginView.as_view(
            template_name="registration/login_tsx.html",
            authentication_form=CustomAuthenticationForm,
        ),
        name="login_tsx",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
