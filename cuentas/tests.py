from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class IngresarTests(TestCase):
    def test_cliente_puede_iniciar_sesion_y_se_guarda_en_sesion_de_app(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="clientedemo",
            password="demo1234",
            first_name="Cliente Demo",
        )

        respuesta = self.client.post(
            reverse("cuentas:ingresar"),
            {"usuario": "clientedemo", "password": "demo1234"},
        )

        self.assertRedirects(respuesta, reverse("catalogo:lista"))
        self.assertEqual(self.client.session["usuario"], "clientedemo")
        self.assertEqual(self.client.session["nombre"], "Cliente Demo")
        self.assertEqual(self.client.session["rol"], "cliente")

    def test_administrador_inicia_sesion_con_rol_admin(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="admin",
            password="alvarito2026",
            is_staff=True,
        )

        respuesta = self.client.post(
            reverse("cuentas:ingresar"),
            {"usuario": "admin", "password": "alvarito2026"},
        )

        self.assertRedirects(respuesta, reverse("catalogo:lista"))
        self.assertEqual(self.client.session["usuario"], "admin")
        self.assertEqual(self.client.session["rol"], "admin")

    def test_credenciales_incorrectas_no_inician_sesion(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="clientedemo",
            password="demo1234",
        )

        respuesta = self.client.post(
            reverse("cuentas:ingresar"),
            {"usuario": "clientedemo", "password": "incorrecta"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Usuario o contraseña incorrectos.")
        self.assertNotIn("usuario", self.client.session)


class SalirTests(TestCase):
    def test_salir_cierra_sesion_y_redirige_al_inicio(self):
        session = self.client.session
        session.update(
            {
                "usuario": "cliente",
                "nombre": "Cliente",
                "rol": "admin",
            }
        )
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        respuesta = self.client.post(reverse("cuentas:salir"))

        self.assertRedirects(respuesta, reverse("catalogo:inicio"))
        sesion_cerrada = self.client.session
        self.assertNotIn("usuario", sesion_cerrada)
        self.assertNotIn("nombre", sesion_cerrada)
        self.assertNotIn("rol", sesion_cerrada)

    def test_boton_salir_envia_post_con_token_csrf(self):
        session = self.client.session
        session.update({"usuario": "cliente", "nombre": "Cliente"})
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        respuesta = self.client.get(reverse("catalogo:inicio"))

        self.assertContains(
            respuesta,
            f'<form class="form-salir" method="post" action="{reverse("cuentas:salir")}">',
        )
        self.assertContains(respuesta, 'name="csrfmiddlewaretoken"')
        self.assertContains(respuesta, '<button class="icono-accion accion-salir" type="submit">Salir</button>')
