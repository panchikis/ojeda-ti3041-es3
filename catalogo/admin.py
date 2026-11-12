from django.contrib import admin

from .models import Categoria, ConsultaCliente, Producto


class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')


class ProductoAdmin(admin.ModelAdmin):
    exclude = ('creado_en',)
    list_display = ('id', 'nombre', 'categoria', 'precio', 'stock', 'creado_en')
    search_fields = ('nombre',)
    list_filter = ('categoria',)


admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Producto, ProductoAdmin)


@admin.register(ConsultaCliente)
class ConsultaClienteAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "correo", "producto", "fecha", "estado")
    list_filter = ("estado", "fecha")
    list_editable = ("estado",)
    search_fields = ("nombre", "correo", "mensaje")
    readonly_fields = ("fecha",)