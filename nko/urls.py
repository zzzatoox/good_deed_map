from django.urls import path
from . import views
from .suggest_proxy import suggest_proxy

urlpatterns = [
    path("add/", views.add_nko, name="add_nko"),
    path("edit/<int:pk>/", views.edit_nko, name="edit_nko"),
    path("transfer/<int:pk>/", views.transfer_ownership, name="transfer_ownership"),
    path("transfer-tsx/", views.transfer_ownership_tsx, name="transfer_ownership_tsx"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("my-requests/tsx/", views.my_requests_tsx, name="my_requests_tsx"),
    path("api/nko-list/", views.nko_list_api, name="nko_list_api"),
    path("api/categories/", views.categories_api, name="categories_api"),
    path("api/suggest/", suggest_proxy, name="suggest_proxy"),
]
