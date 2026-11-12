from django.urls import path
from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("catalogo/", views.lista, name="lista"),
    path("reportes/categorias/", views.reporte_categorias, name="reporte_categorias"),
    path("reportes/stock-critico/", views.reporte_stock_critico, name="reporte_stock_critico"),
    path("producto/<int:id>/imagen.svg", views.imagen_producto, name="imagen_producto"),
    path("producto/<int:id>/", views.detalle, name="detalle"),
    path("administrar/agregar/", views.agregar_producto, name="agregar_producto"),
    path("administrar/stock/<int:id>/", views.agregar_stock, name="agregar_stock"),
    path("administrar/editar/<int:id>/", views.editar_producto, name="editar_producto"),
    path("administrar/eliminar/<int:id>/", views.eliminar_producto, name="eliminar_producto"),
    path("carrito/", views.ver_carrito, name="ver_carrito"),
    path("carrito/agregar/<int:id>/", views.agregar_al_carrito, name="agregar_al_carrito"),
    path("carrito/actualizar/<int:id>/", views.actualizar_carrito, name="actualizar_carrito"),
    path("carrito/quitar/<int:id>/", views.quitar_del_carrito, name="quitar_del_carrito"),
    path("carrito/vaciar/", views.vaciar_carrito, name="vaciar_carrito"),
    path("carrito/confirmar/", views.confirmar_carrito, name="confirmar_carrito"),
]
