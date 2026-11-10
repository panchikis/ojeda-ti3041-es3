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

    def test_compra_actualiza_stock_y_rechaza_unidades_excedentes(self):
        self.guardar_sesion(usuario="cliente")
        url = reverse("catalogo:comprar", args=[self.producto.pk])

        compra = self.client.post(url, {"cantidad": "2"})

        self.assertEqual(compra.status_code, 200)
        self.assertContains(compra, "3 unidades")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

        compra_excedente = self.client.post(url, {"cantidad": "4"})

        self.assertContains(compra_excedente, "Solo quedan 3 unidades disponibles.")
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
            reverse("catalogo:detalle", args=[producto.pk]),
        )
        self.assertEqual(producto.categoria.nombre, "Pinturas")
        self.assertEqual(producto.imagen, reverse(
            "catalogo:imagen_producto",
            args=[producto.pk],
        ))
        self.assertEqual(Categoria.objects.filter(nombre="Pinturas").count(), 1)


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
