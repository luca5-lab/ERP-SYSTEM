from django.db import models


class Cliente(models.Model):
    
    CONDICIONES_PAGO = [
        ('60', '60 días'),
        ('30', '30 días'),
        ('15', '15 días'),
        ('0', 'Contado'),
    ]

    razon_social = models.CharField(max_length=150)
    giro = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=200)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    condiciones_pago = models.CharField(
        max_length=2,
        choices=CONDICIONES_PAGO,
        default='0'
    )

    def __str__(self):
        return self.razon_social


class Proveedor(models.Model):

    CONDICIONES_PAGO = [
        ('60', '60 días'),
        ('30', '30 días'),
        ('15', '15 días'),
        ('0', 'Contado'),
    ]

    razon_social = models.CharField(max_length=150)
    giro = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=200)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    condiciones_pago = models.CharField(
        max_length=2,
        choices=CONDICIONES_PAGO,
        default='0'
    )

    def __str__(self):
        return self.razon_social