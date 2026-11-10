from django.urls import path
from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("catalogo/", views.lista, name="lista"),
    path("producto/<int:id>/imagen.svg", views.imagen_producto, name="imagen_producto"),
    path("producto/<int:id>/", views.detalle, name="detalle"),
    path("comprar/<int:id>/", views.comprar, name="comprar"),
    path("administrar/agregar/", views.agregar_producto, name="agregar_producto"),
    path("administrar/stock/<int:id>/", views.agregar_stock, name="agregar_stock"),
    path("carrito/", views.ver_carrito, name="ver_carrito"),
    path("carrito/agregar/<int:id>/", views.agregar_al_carrito, name="agregar_al_carrito"),
    path("carrito/actualizar/<int:id>/", views.actualizar_carrito, name="actualizar_carrito"),
    path("carrito/quitar/<int:id>/", views.quitar_del_carrito, name="quitar_del_carrito"),
    path("carrito/vaciar/", views.vaciar_carrito, name="vaciar_carrito"),
    path("carrito/confirmar/", views.confirmar_carrito, name="confirmar_carrito"),
]
