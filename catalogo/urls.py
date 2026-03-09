from django.urls import path
from . import views

urlpatterns = [
    path('', views.catalogo_lista, name='catalogo_lista'),
]