from django.urls import path
from . import views

urlpatterns = [
    path("add/", views.add_nko, name="add_nko"),
    path("edit/<int:pk>/", views.edit_nko, name="edit_nko"),
    path("transfer/<int:pk>/", views.transfer_ownership, name="transfer_ownership"),
    path("api/nko-list/", views.nko_list_api, name="nko_list_api"),
]
