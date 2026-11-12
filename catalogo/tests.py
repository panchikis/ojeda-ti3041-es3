from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Categoria, ConsultaCliente, Producto


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

        self.assertContains(respuesta, 'href="/static/css/style.css?v=4"')
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

    def test_detalle_guarda_los_ultimos_tres_productos_visitados_en_sesion(self):
        productos = [self.producto]
        for nombre in ("Nivel", "Alicate", "Sierra"):
            productos.append(
                Producto.objects.create(
                    nombre=nombre,
                    stock=4,
                    precio=3000,
                    categoria=self.categoria,
                )
            )

        for producto in productos:
            respuesta = self.client.get(
                reverse("catalogo:detalle", args=[producto.pk])
            )

        self.assertEqual(
            self.client.session["productos_visitados"],
            [productos[3].pk, productos[2].pk, productos[1].pk],
        )
        self.assertEqual(
            [producto.pk for producto in respuesta.context["productos_recientes"]],
            [productos[3].pk, productos[2].pk, productos[1].pk],
        )
        self.assertContains(respuesta, "Vistos recientemente")
        self.assertContains(respuesta, f'src="{productos[3].imagen}"')

    def test_detalle_muestra_producto_visitado_desde_la_primera_visita(self):
        respuesta = self.client.get(
            reverse("catalogo:detalle", args=[self.producto.pk])
        )

        self.assertContains(respuesta, "Vistos recientemente")
        self.assertContains(respuesta, self.producto.nombre)
        self.assertEqual(
            self.client.session["productos_visitados"],
            [self.producto.pk],
        )

    def test_inicio_muestra_productos_recientes_con_imagenes_de_la_sesion(self):
        self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))

        respuesta = self.client.get(reverse("catalogo:inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [producto.pk for producto in respuesta.context["productos_recientes"]],
            [self.producto.pk],
        )
        self.assertContains(respuesta, "Vistos recientemente")
        self.assertContains(respuesta, f'src="{self.producto.imagen}"')

    def test_contacto_muestra_formulario_con_csrf(self):
        respuesta = self.client.get(reverse("catalogo:contacto"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'name="csrfmiddlewaretoken"')
        self.assertContains(respuesta, 'name="correo"')
        self.assertContains(respuesta, 'name="producto"')
        self.assertContains(
            respuesta,
            "Déjanos tu mensaje y te responderemos al correo que nos indiques a la brevedad posible.",
        )
        self.assertContains(respuesta, 'class="formulario formulario-contacto"')

    def test_contacto_rechaza_campos_vacios_correo_invalido_y_texto_corto(self):
        casos_invalidos = (
            ({}, {"nombre", "correo", "mensaje"}),
            (
                {"nombre": "Ana María", "correo": "esto-no-es-correo", "mensaje": "Necesito ayuda con mi pedido"},
                {"correo"},
            ),
            (
                {"nombre": "Al", "correo": "ana@example.com", "mensaje": "Necesito ayuda con mi pedido"},
                {"nombre"},
            ),
            (
                {"nombre": "Ana María", "correo": "ana@example.com", "mensaje": "Ayuda"},
                {"mensaje"},
            ),
        )

        for datos, campos_esperados in casos_invalidos:
            with self.subTest(datos=datos):
                respuesta = self.client.post(reverse("catalogo:contacto"), datos)
                self.assertEqual(respuesta.status_code, 200)
                formulario = respuesta.context["formulario"]
                self.assertFalse(formulario.is_valid())
                self.assertTrue(campos_esperados.issubset(formulario.errors))

        self.assertEqual(ConsultaCliente.objects.count(), 0)

    def test_contacto_guarda_consulta_con_producto_opcional_y_muestra_referencia(self):
        respuesta = self.client.post(
            reverse("catalogo:contacto"),
            {
                "nombre": "  Ana María  ",
                "correo": "ana@example.com",
                "mensaje": "  Necesito ayuda con un producto.  ",
            },
        )

        consulta = ConsultaCliente.objects.get()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(consulta.nombre, "Ana María")
        self.assertEqual(consulta.mensaje, "Necesito ayuda con un producto.")
        self.assertIsNone(consulta.producto)
        self.assertContains(respuesta, f"#{consulta.pk}")

    def test_admin_puede_ver_consultas_desde_la_sesion_del_sitio(self):
        self.guardar_sesion(rol="admin")
        consulta = ConsultaCliente.objects.create(
            nombre="Ana María",
            correo="ana@example.com",
            mensaje="Necesito ayuda con este producto.",
            producto=self.producto,
        )

        respuesta = self.client.get(reverse("catalogo:consultas_clientes"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, consulta.nombre)
        self.assertContains(respuesta, consulta.correo)
        self.assertContains(respuesta, consulta.mensaje)
        self.assertContains(respuesta, self.producto.nombre)
        self.assertContains(respuesta, "Consultas")
        self.assertContains(respuesta, 'class="reporte-tabla-contenedor consultas-tabla"')

    def test_admin_puede_cambiar_consulta_a_cualquiera_de_los_estados(self):
        self.guardar_sesion(rol="admin")
        consulta = ConsultaCliente.objects.create(
            nombre="Ana María",
            correo="ana@example.com",
            mensaje="Necesito ayuda con este producto.",
        )
        estados = (
            ConsultaCliente.Estado.EN_REVISION,
            ConsultaCliente.Estado.RESPONDIDA,
            ConsultaCliente.Estado.CERRADA,
            ConsultaCliente.Estado.PENDIENTE,
        )

        for estado in estados:
            with self.subTest(estado=estado):
                respuesta = self.client.post(
                    reverse(
                        "catalogo:actualizar_estado_consulta",
                        args=[consulta.pk],
                    ),
                    {"estado": estado},
                )
                self.assertRedirects(
                    respuesta,
                    reverse("catalogo:consultas_clientes"),
                )
                consulta.refresh_from_db()
                self.assertEqual(consulta.estado, estado)

    def test_cambiar_estado_rechaza_opciones_invalidas_y_usuarios_no_admin(self):
        consulta = ConsultaCliente.objects.create(
            nombre="Ana María",
            correo="ana@example.com",
            mensaje="Necesito ayuda con este producto.",
        )
        url = reverse(
            "catalogo:actualizar_estado_consulta",
            args=[consulta.pk],
        )

        self.guardar_sesion(rol="admin")
        respuesta_invalida = self.client.post(url, {"estado": "desconocido"})
        self.assertEqual(respuesta_invalida.status_code, 400)
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, ConsultaCliente.Estado.PENDIENTE)

        self.guardar_sesion(rol="cliente")
        respuesta_cliente = self.client.post(
            url,
            {"estado": ConsultaCliente.Estado.CERRADA},
        )
        self.assertRedirects(
            respuesta_cliente,
            reverse("cuentas:ingresar"),
            fetch_redirect_response=False,
        )
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, ConsultaCliente.Estado.PENDIENTE)

    def test_consultas_solo_son_accesibles_para_admin(self):
        url = reverse("catalogo:consultas_clientes")

        respuesta_anonimo = self.client.get(url)
        self.assertRedirects(
            respuesta_anonimo,
            reverse("cuentas:ingresar"),
            fetch_redirect_response=False,
        )

        self.guardar_sesion(rol="cliente")
        respuesta_cliente = self.client.get(url)
        self.assertRedirects(
            respuesta_cliente,
            reverse("cuentas:ingresar"),
            fetch_redirect_response=False,
        )

    def test_consulta_conserva_datos_si_se_elimina_el_producto(self):
        consulta = ConsultaCliente.objects.create(
            nombre="Ana María",
            correo="ana@example.com",
            mensaje="Necesito ayuda con este producto.",
            producto=self.producto,
        )

        self.producto.delete()
        consulta.refresh_from_db()

        self.assertIsNone(consulta.producto)

    def test_contacto_rechaza_post_sin_token_csrf(self):
        cliente_csrf = Client(enforce_csrf_checks=True)
        url = reverse("catalogo:contacto")
        cliente_csrf.get(url)

        respuesta = cliente_csrf.post(
            url,
            {
                "nombre": "Ana María",
                "correo": "ana@example.com",
                "mensaje": "Necesito ayuda con un producto.",
            },
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(ConsultaCliente.objects.count(), 0)

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
            "admin:catalogo_consultacliente_changelist",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
