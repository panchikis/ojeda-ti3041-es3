from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    stock = models.IntegerField()
    precio = models.IntegerField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    imagen = models.CharField(max_length=300, blank=True)
    creado_en = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre


class ConsultaCliente(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "En revisión"
        RESPONDIDA = "respondida", "Respondida"
        CERRADA = "cerrada", "Cerrada"

    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    mensaje = models.TextField()
    producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    def __str__(self):
        return f"{self.nombre} - {self.fecha}"