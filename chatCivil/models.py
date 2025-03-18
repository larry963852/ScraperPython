from django.db import models

from django.db import models

class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    precio = models.CharField(max_length=50)  # Guardamos como texto por variaciones
    enlace = models.URLField(max_length=500)
    sku = models.CharField(max_length=100, null=True, blank=True)
    imagen = models.URLField(max_length=500, null=True, blank=True)
    fecha_adicion = models.DateTimeField(auto_now_add=True)  # Fecha de consulta

    def __str__(self):
        return self.nombre

