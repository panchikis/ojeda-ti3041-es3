from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Producto


class CatalogoViewsTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Herramientas manuales")
        self.producto = Producto.objects.create(
            nombre="Martillo carpintero 16 oz",
            stock=5,
            precio=8990,
            categoria=self.categoria,
            imagen="/static/img/productos/martillo_carpintero_16oz.webp",
        )

    def guardar_sesion(self, **valores):
        session = self.client.session
        session.update(valores)
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

    def test_inicio_y_lista_muestran_productos_de_la_base_de_datos(self):
        Producto.objects.create(
            nombre="Martillo agotado",
            stock=0,
            precio=5000,
            categoria=self.categoria,
        )

        inicio = self.client.get(reverse("catalogo:inicio"))
        lista = self.client.get(reverse("catalogo:lista"))

        self.assertEqual(inicio.status_code, 200)
        self.assertEqual(inicio.context["total"], 2)
        self.assertEqual(inicio.context["disponibles"], 1)
        self.assertContains(inicio, "Martillo carpintero 16 oz")
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, "/static/img/productos/martillo_carpintero_16oz.webp")
        self.assertContains(lista, "Martillo agotado")

    def test_reporte_categorias_calcula_cantidad_promedio_y_stock(self):
        self.guardar_sesion(rol="admin")
        Producto.objects.create(
            nombre="Destornillador",
            stock=7,
            precio=11000,
            categoria=self.categoria,
        )

        respuesta = self.client.get(reverse("catalogo:reporte_categorias"))

        self.assertEqual(respuesta.status_code, 200)
        resumen = respuesta.context["categorias"].get()
        self.assertEqual(resumen.cantidad_productos, 2)
        self.assertEqual(resumen.precio_promedio, 9995)
        self.assertEqual(resumen.stock_total, 12)
        self.assertContains(respuesta, "Herramientas manuales")
        self.assertContains(respuesta, "Precio promedio")

    def test_reporte_stock_filtra_ordena_y_muestra_enlaces_de_navegacion(self):
        self.guardar_sesion(rol="admin")
        Producto.objects.create(
            nombre="Nivel",
            stock=2,
            precio=5000,
            categoria=self.categoria,
        )
        Producto.objects.create(
            nombre="Alicate",
            stock=2,
            precio=6000,
            categoria=self.categoria,
        )

        respuesta = self.client.get(
            reverse("catalogo:reporte_stock_critico"),
            {"umbral": "2"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            list(respuesta.context["productos"].values_list("nombre", flat=True)),
            ["Alicate", "Nivel"],
        )
        self.assertContains(respuesta, "Stock crítico")
        self.assertContains(respuesta, reverse("catalogo:reporte_categorias"))
        self.assertContains(respuesta, reverse("catalogo:reporte_stock_critico"))

    def test_reporte_stock_usa_umbral_predeterminado_si_el_ingresado_no_es_valido(self):
        self.guardar_sesion(rol="admin")
        respuesta = self.client.get(
            reverse("catalogo:reporte_stock_critico"),
            {"umbral": "-1"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["umbral"], 10)
        self.assertContains(respuesta, "Ingresa un umbral válido")

    def test_reportes_solo_son_accesibles_para_admin(self):
        for reporte in ("reporte_categorias", "reporte_stock_critico"):
            with self.subTest(reporte=reporte):
                respuesta = self.client.get(reverse(f"catalogo:{reporte}"))
                self.assertRedirects(
                    respuesta,
                    reverse("cuentas:ingresar"),
                    fetch_redirect_response=False,
                )

        self.guardar_sesion(rol="cliente")
        for reporte in ("reporte_categorias", "reporte_stock_critico"):
            with self.subTest(reporte=reporte, rol="cliente"):
                respuesta = self.client.get(reverse(f"catalogo:{reporte}"))
                self.assertRedirects(
                    respuesta,
                    reverse("cuentas:ingresar"),
                    fetch_redirect_response=False,
                )

    def test_enlaces_de_reportes_solo_aparecen_para_admin(self):
        respuesta_cliente = self.client.get(reverse("catalogo:inicio"))
        self.assertNotContains(respuesta_cliente, "Reporte por categoría")
        self.assertNotContains(respuesta_cliente, "Stock crítico")

        self.guardar_sesion(rol="admin")
        respuesta_admin = self.client.get(reverse("catalogo:inicio"))
        self.assertContains(respuesta_admin, "Reporte por categoría")
        self.assertContains(respuesta_admin, "Stock crítico")

    def test_paginas_cargan_css_desde_ruta_estatica_absoluta(self):
        self.guardar_sesion(rol="admin")

        respuesta = self.client.get(reverse("catalogo:reporte_stock_critico"))

        self.assertContains(respuesta, 'href="/static/css/style.css?v=2"')
        self.assertContains(respuesta, 'class="reporte-tabla"')

    def test_detalle_y_imagen_svg_cargan_producto_de_la_base_de_datos(self):
        detalle = self.client.get(
            reverse("catalogo:detalle", args=[self.producto.pk])
        )
        imagen = self.client.get(
            reverse("catalogo:imagen_producto", args=[self.producto.pk])
        )

        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, self.categoria.nombre)
        self.assertEqual(imagen.status_code, 200)
        self.assertEqual(imagen["Content-Type"], "image/svg+xml")
        self.assertContains(imagen, self.producto.nombre)

    def test_detalle_admin_muestra_botones_de_editar_y_eliminar_sin_agregar_stock(self):
        self.guardar_sesion(rol="admin")

        respuesta = self.client.get(
            reverse("catalogo:detalle", args=[self.producto.pk])
        )

        self.assertContains(respuesta, 'class="boton boton-claro"')
        self.assertContains(respuesta, 'class="boton boton-peligro"')
        self.assertContains(respuesta, "Editar producto")
        self.assertContains(respuesta, "Eliminar producto")
        self.assertNotContains(respuesta, "Agregar stock")
        self.assertNotContains(respuesta, "Sumar stock")

    def test_confirmar_carrito_actualiza_stock_y_rechaza_unidades_excedentes(self):
        self.guardar_sesion(usuario="cliente")
        agregar_url = reverse("catalogo:agregar_al_carrito", args=[self.producto.pk])
        confirmar_url = reverse("catalogo:confirmar_carrito")

        self.client.post(agregar_url, {"cantidad": "2"})
        compra = self.client.post(confirmar_url)

        self.assertEqual(compra.status_code, 200)
        self.assertContains(compra, "Martillo carpintero 16 oz")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

        self.client.post(agregar_url, {"cantidad": "4"})
        compra_excedente = self.client.post(confirmar_url)

        self.assertContains(compra_excedente, "pediste 4 y quedan 3")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

    def test_admin_puede_agregar_stock_persistido(self):
        self.guardar_sesion(rol="admin")

        respuesta = self.client.post(
            reverse("catalogo:agregar_stock", args=[self.producto.pk]),
            {"cantidad": "7"},
        )

        self.assertRedirects(
            respuesta,
            reverse("catalogo:detalle", args=[self.producto.pk]),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 12)

    def test_admin_puede_crear_producto_y_categoria_en_la_base_de_datos(self):
        self.guardar_sesion(rol="admin")

        respuesta = self.client.post(
            reverse("catalogo:agregar_producto"),
            {
                "nombre": "Pintura blanca",
                "categoria": "Pinturas",
                "precio": "12000",
                "stock": "8",
                "imagen_url": "",
            },
        )

        producto = Producto.objects.get(nombre="Pintura blanca")
        self.assertRedirects(
            respuesta,
            reverse("catalogo:lista"),
        )
        self.assertEqual(producto.categoria.nombre, "Pinturas")
        self.assertEqual(producto.imagen, reverse(
            "catalogo:imagen_producto",
            args=[producto.pk],
        ))
        self.assertEqual(Categoria.objects.filter(nombre="Pinturas").count(), 1)

    def test_admin_puede_editar_producto_desde_el_sitio(self):
        self.guardar_sesion(rol="admin")

        respuesta = self.client.post(
            reverse("catalogo:editar_producto", args=[self.producto.pk]),
            {
                "nombre": "Martillo actualizado",
                "categoria": self.categoria.nombre,
                "precio": "9990",
                "stock": "8",
                "imagen": "/static/img/martillo.webp",
            },
        )

        self.assertRedirects(respuesta, reverse("catalogo:lista"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Martillo actualizado")
        self.assertEqual(self.producto.precio, 9990)
        self.assertEqual(self.producto.stock, 8)

    def test_admin_puede_eliminar_producto_con_confirmacion(self):
        self.guardar_sesion(rol="admin")
        url = reverse("catalogo:eliminar_producto", args=[self.producto.pk])

        confirmacion = self.client.get(url)
        self.assertContains(confirmacion, "¿Eliminar este producto?")

        respuesta = self.client.post(url)

        self.assertRedirects(respuesta, reverse("catalogo:lista"))
        self.assertFalse(Producto.objects.filter(pk=self.producto.pk).exists())


class CatalogoAdminTests(TestCase):
    def test_admin_puede_abrir_listas_de_categorias_y_productos(self):
        admin = get_user_model().objects.create_superuser(
            username="admincatalogo",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin)

        for url_name in (
            "admin:catalogo_categoria_changelist",
            "admin:catalogo_producto_changelist",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
