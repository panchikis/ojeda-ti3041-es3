from django.urls import path

from . import views


app_name = "cuentas"

urlpatterns = [
    path("ingresar/", views.ingresar, name="ingresar"),
    path("salir/", views.salir, name="salir"),
]