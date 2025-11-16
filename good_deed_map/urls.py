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

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", nko_views.index, name="index"),
    path("nko/", include("nko.urls")),
    path("users/", include("users.urls")),
    path("accounts/login/", users_views.login_view, name="login"),
    path("accounts/register/", users_views.register, name="register"),
    path("accounts/logout/", users_views.logout_view, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
