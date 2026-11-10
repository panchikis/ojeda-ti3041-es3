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