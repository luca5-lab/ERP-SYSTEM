from django.db import models
from django.contrib.auth.models import User
from clientes.models import Cliente 


class Perfil(models.Model):

    TIPO_CHOICES = [
        ('taller', 'Taller'),
        ('diseno', 'Diseño'),
        ('administracion', 'Administracion')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_CHOICES)

    def __str__(self):
        return self.user.username

class Proceso(models.Model):
    ESTADOS_PROCESO = [
        ('diseno', 'En Diseño (Pauta/Correcciones)'),
        ('taller', 'En Taller (Producción)'),
        ('finalizado', 'Finalizado (Pendiente Admin)'),
        ('cerrado', 'Cerrado/Entregado'),
    ]

    # --- INFORMACIÓN BASE Y CONTROL DE RUTA ---
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='procesos')
    estado = models.CharField(max_length=20, choices=ESTADOS_PROCESO, default='diseno')
    creado = models.DateTimeField(auto_now_add=True)
    responsable_proyecto = models.CharField(max_length=100, blank=True, null=True)

    # Estos campos definen el flujo que el Admin configuró
    pasa_por_diseno = models.BooleanField(default=True, verbose_name="¿Requiere Diseño?")
    pasa_por_taller = models.BooleanField(default=True, verbose_name="¿Requiere Taller?")

    # --- ETAPA 1: DISEÑO ---
    reunion = models.BooleanField(default=False)
    pauta = models.BooleanField(default=False)
    enviado_correccion = models.BooleanField(default=False)
    correccion_1 = models.BooleanField(default=False)
    correccion_2 = models.BooleanField(default=False)
    correccion_3 = models.BooleanField(default=False)
    aprobacion_final = models.BooleanField(default=False) 

    # --- ETAPA 2: TALLER (Materiales y Fabricación) ---
    acrilico = models.BooleanField(default=False)
    sintra = models.BooleanField(default=False)
    ojetillo = models.BooleanField(default=False)
    ad_prom = models.BooleanField(default=False)
    ad_vehicular = models.BooleanField(default=False)
    empavonado = models.BooleanField(default=False)
    microperf = models.BooleanField(default=False)
    sellado = models.BooleanField(default=False)
    tela_pvc = models.BooleanField(default=False)

    # Producción Taller
    impresion = models.BooleanField(default=False)
    corte = models.BooleanField(default=False)
    aprobacion_taller = models.BooleanField(default=False)
    terminaciones = models.TextField(blank=True, null=True)

    # --- LÓGICA DE PROGRESO INTELIGENTE ---
    @property
    def calcular_porcentaje(self):
        """Calcula el progreso adaptándose a la ruta elegida por el Admin."""
        if self.estado == 'cerrado':
            return 100
        if self.estado == 'finalizado':
            return 90
        
        porcentaje = 0
        
        # --- CÁLCULO EN ETAPA DE DISEÑO ---
        if self.estado == 'diseno':
            porcentaje = 10 # Base por inicio
            hitos_diseno = [
                self.reunion, self.pauta, self.enviado_correccion, 
                self.correccion_1, self.correccion_2, self.correccion_3, 
                self.aprobacion_final
            ]
            completados = sum(1 for hito in hitos_diseno if hito)
            
            # Si el proyecto NO pasará por taller, cada hito de diseño vale más
            # para que al terminar diseño ya esté cerca del 90%
            factor = 11 if not self.pasa_por_taller else 7
            porcentaje += (completados * factor)
            
        # --- CÁLCULO EN ETAPA DE TALLER ---
        elif self.estado == 'taller':
            # Si se saltó diseño, el progreso parte de un piso más bajo (20%)
            # Si viene de diseño, parte del 60%
            porcentaje = 60 if self.pasa_por_diseno else 20
            
            hitos_taller = [
                self.impresion, 
                self.corte, 
                bool(self.terminaciones),
                self.aprobacion_taller
            ]
            completados = sum(1 for hito in hitos_taller if hito)
            
            # Si se saltó diseño, los hitos de taller valen más (23% c/u)
            # para cubrir el rango 20% -> 90%
            factor_taller = 10 if self.pasa_por_diseno else 23
            porcentaje += (completados * factor_taller)
            
        return min(porcentaje, 90)

    def __str__(self):
        return f"{self.cliente.razon_social} - {self.get_estado_display()}"

class MaterialStock(models.Model):
    CATEGORIAS = [
        ('ADH', 'Adhesivos'),
        ('TEL', 'Telas'),
        ('RIG', 'Materiales Rígidos'),
        ('TIN', 'Tintas Plotter Xenons DX5'),
        ('LIM', 'Limpieza'),
        ('REP', 'Repuestos Taller'),
    ]

    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=3, choices=CATEGORIAS)
    variedad = models.CharField(max_length=50, blank=True, help_text="Ej: Mate, Brillante, 3mm")
    nivel_actual = models.IntegerField(default=100) # De 0 a 100
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Lógica de alerta al bajar del 30%
        if self.nivel_actual <= 30:
            self.enviar_alerta_stock()
        super().save(*args, **kwargs)

    def enviar_alerta_stock(self):
        # Aquí enviamos el correo al superusuario
        subject = f'⚠️ ALERTA DE STOCK CRÍTICO: {self.nombre}'
        message = f'El material {self.nombre} ({self.variedad}) ha bajado al {self.nivel_actual}%.'
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [admin[1] for admin in settings.ADMINS] # O el correo del superuser
        
        try:
            send_mail(subject, message, email_from, recipient_list)
        except:
            pass # Para evitar que el sistema caiga si falla el envío

    def __str__(self):
        return f"{self.nombre} - {self.nivel_actual}%"

class Articulo(models.Model):

    FAMILIAS_CHOICES = [
        ('Adhesivos', 'Adhesivos'),
        ('Merchandising', 'Merchandising'),
        ('Tecnologia', 'Tecnología'),
    ]

    codigo = models.CharField(max_length=10, unique=True, editable=False)
    familia = models.CharField(max_length=50, choices=FAMILIAS_CHOICES, default='Tecnologia')
    descripcion = models.TextField()
    costo_compra = models.DecimalField(max_digits=10, decimal_places=2)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=19.0)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    margen_ganancia = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.codigo: 
            ultimo_articulo = Articulo.objects.order_by('id').last()
            if not ultimo_articulo:
                nuevo_id = 1
            else:
                try:
                    ultimo_codigo = ultimo_articulo.codigo
                    numero_str = ultimo_codigo.replace("AR-", "")
                    nuevo_id = int(numero_str) + 1
                except (ValueError, AttributeError):
                    nuevo_id = ultimo_articulo.id + 1
            
            self.codigo = f"AR-{str(nuevo_id).zfill(4)}"
        
        super().save(*args, **kwargs)

    @property
    def precio_con_iva(self):
        return self.precio_unitario * (1 + (self.iva_porcentaje / 100))

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

class Servicio(models.Model):
    FAMILIAS_SERVICIOS = [
        ('Letreros', 'Letreros'),
        ('Creacion Diseño', 'Creación Diseño'),
        ('Adhesivo Vehicular', 'Adhesivo Vehicular'),
        ('Tecnologia Instalaciones', 'Tecnología Instalaciones'),
        ('Tecnologia Desarrollo', 'Tecnología Desarrollo'),
        ('Marketing Web', 'Marketing Web'),
        ('Marketing RRSS', 'Marketing RRSS'),
    ]

    codigo = models.CharField(max_length=10, unique=True, editable=False)
    familia = models.CharField(max_length=50, choices=FAMILIAS_SERVICIOS)
    descripcion = models.TextField()
    costo_m2 = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.codigo:
            total_servicios = Servicio.objects.count()
            nuevo_numero = total_servicios + 1
            
            while Servicio.objects.filter(codigo=f'SE-{nuevo_numero:04d}').exists():
                nuevo_numero += 1
                
            self.codigo = f'SE-{nuevo_numero:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

class CotizacionServicio(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    cantidad_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    valor_unitario_m2 = models.DecimalField(max_digits=12, decimal_places=2) # Se guarda el valor del momento
    total_neto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Cálculo automático: Total = m2 * valor_m2
        self.total_neto = self.cantidad_m2 * self.valor_unitario_m2
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cotización {self.id} - {self.cliente.razon_social}"

class CotizacionArticulo(models.Model):
    n_presupuesto = models.AutoField(primary_key=True)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total_final = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class DetalleCotizacionArticulo(models.Model):
    cotizacion = models.ForeignKey(CotizacionArticulo, related_name='detalles', on_delete=models.CASCADE)
    articulo = models.ForeignKey('usuarios.Articulo', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class AccionHistorial(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    accion = models.CharField(max_length=255) # Ejemplo: "Finalizó proceso de Cliente X"
    fecha = models.DateTimeField(auto_now_add=True)
    detalles = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha'] # Lo más nuevo primero