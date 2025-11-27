"""
URL configuration for good_deed_map project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from nko import views as nko_views
from users import views as users_views
from users.forms import CustomPasswordResetForm, CustomPasswordResetTsxForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", nko_views.index_tsx, name="index"),
    path("old/", nko_views.index, name="index_old"),
    path("nko/", include("nko.urls")),
    path("users/", include("users.urls")),
    path("captcha/", include("captcha.urls")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login_tsx.html",
        ),
        name="login",
    ),
    path("accounts/login_old/", users_views.login_view, name="login_old"),
    path("accounts/register/", users_views.register_tsx, name="register"),
    path("accounts/register_old/", users_views.register, name="register_old"),
    path("accounts/logout/", users_views.logout_view, name="logout"),
    path(
        "accounts/confirm-email/<uuid:token>/",
        users_views.confirm_email,
        name="confirm_email",
    ),
    path(
        "accounts/resend-confirmation/",
        users_views.resend_confirmation,
        name="resend_confirmation",
    ),
    # Password reset URLs with custom templates (TSX versions as default)
    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_tsx.html",
            form_class=CustomPasswordResetTsxForm,
            success_url="/accounts/password_reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done_tsx.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm_tsx.html",
            success_url="/accounts/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete_tsx.html"
        ),
        name="password_reset_complete",
    ),
    # Old password reset URLs (for backwards compatibility)
    path(
        "accounts/password_reset_old/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html",
            form_class=CustomPasswordResetForm,
        ),
        name="password_reset_old",
    ),
    path(
        "accounts/password_reset_old/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done_old",
    ),
    path(
        "accounts/reset_old/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm_old",
    ),
    path(
        "accounts/reset_old/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete_old",
    ),
    # Закомментировано, так как используем собственные URL
    # path("accounts/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
