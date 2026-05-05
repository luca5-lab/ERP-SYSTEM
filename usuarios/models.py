from django.db import models
from django.contrib.auth.models import User
from clientes.models import Cliente, Proveedor
from datetime import timedelta
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
import json

class Perfil(models.Model):

    TIPO_CHOICES = [
        ('taller', 'Taller'),
        ('diseno', 'Diseño'),
        ('administracion', 'Administracion'),
        ('vendedor', 'Vendedor'),
    ]

    user = models.OneToOneField(User, on_delete=models.PROTECT)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_CHOICES)
    codigo_vendedor = models.CharField(max_length=10, blank=True, null=True, unique=True)

    def __str__(self):
        return self.user.username

class Proceso(models.Model):
    FAMILIAS_SERVICIOS = [
        ('Letreros', 'Letreros'),
        ('Creacion Diseño', 'Creación Diseño'),
        ('Adhesivo Vehicular', 'Adhesivo Vehicular'),
        ('Tecnologia Instalaciones', 'Tecnología Instalaciones'),
        ('Tecnologia Desarrollo', 'Tecnología Desarrollo'),
        ('Marketing Web', 'Marketing Web'),
        ('Marketing RRSS', 'Marketing RRSS'),
        ('Audiovisual', 'Audiovisual'),
        ('Adhesivos (stickers)', 'Adhesivos (stickers)')
    ]
    
    ESTADOS_PROCESO = [
        ('diseno', 'En Diseño (Pauta/Correcciones)'),
        ('taller', 'En Taller (Producción)'),
        ('finalizado', 'Finalizado (Pendiente Admin)'),
        ('cerrado', 'Cerrado/Entregado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='procesos')
    estado = models.CharField(max_length=20, choices=ESTADOS_PROCESO, default='diseno')
    creado = models.DateTimeField(auto_now_add=True)
    instrucciones_admin = models.TextField(blank=True, null=True, verbose_name="Instrucciones de Administración")
    observaciones_terreno = models.TextField(blank=True, null=True)
    mediciones_json = models.TextField(blank=True, null=True, default="[]")
    mediciones_taller_json = models.TextField(blank=True, null=True, default="[]", verbose_name="Mediciones Taller") 
    responsable_diseno = models.CharField(max_length=100, blank=True, null=True)
    responsable_taller = models.CharField(max_length=100, blank=True, null=True)
    familia = models.CharField(max_length=50, choices=FAMILIAS_SERVICIOS, default='Letreros')
    fecha_entrega = models.DateField(verbose_name="Fecha de Entrega", blank=True, null=True)
    pasa_por_diseno = models.BooleanField(default=True, verbose_name="¿Requiere Diseño?")
    pasa_por_taller = models.BooleanField(default=True, verbose_name="¿Requiere Taller?")

    # diseño
    reunion = models.BooleanField(default=False)
    pauta = models.BooleanField(default=False)
    enviado_correccion = models.BooleanField(default=False)
    correccion_1 = models.BooleanField(default=False)
    correccion_2 = models.BooleanField(default=False)
    correccion_3 = models.BooleanField(default=False)
    aprobacion_final = models.BooleanField(default=False) 

    # materiales taller
    acrilico = models.BooleanField(default=False)
    sintra = models.BooleanField(default=False)
    ojetillo = models.BooleanField(default=False)
    ad_prom = models.BooleanField(default=False)
    ad_vehicular = models.BooleanField(default=False)
    empavonado = models.BooleanField(default=False)
    microperf = models.BooleanField(default=False)
    sellado = models.BooleanField(default=False)
    tela_pvc = models.BooleanField(default=False)
    otros_materiales = models.CharField(max_length=255, blank=True, null=True)

    # Produccion Taller
    impresion = models.BooleanField(default=False)
    corte = models.BooleanField(default=False)
    aprobacion_taller = models.BooleanField(default=False)
    terminaciones = models.TextField(blank=True, null=True)

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
            
            factor_taller = 10 if self.pasa_por_diseno else 23
            porcentaje += (completados * factor_taller)
            
        return min(porcentaje, 90)

    def get_mediciones_list(self):
        if self.mediciones_json:
            try:
                return json.loads(self.mediciones_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def get_mediciones_taller_list(self):
        """Convierte el JSON de mediciones de taller en una lista legible para el template"""
        if self.mediciones_taller_json:
            try:
                return json.loads(self.mediciones_taller_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def detectar_cambios(self):
        """Compara el estado actual con el de la base de datos antes de guardar"""
        if not self.pk:
            return "Creación inicial del proceso."

        # Traemos la versión "vieja" de la base de datos
        original = Proceso.objects.get(pk=self.pk)
        cambios = []
        
        campos = [
            'reunion', 'pauta', 'enviado_correccion', 'correccion_1', 'correccion_2', 
            'correccion_3', 'aprobacion_final', 'acrilico', 'sintra', 'ojetillo', 
            'ad_prom', 'ad_vehicular', 'empavonado', 'microperf', 'sellado', 
            'tela_pvc', 'impresion', 'corte', 'aprobacion_taller'
        ]

        for campo in campos:
            valor_original = getattr(original, campo)
            valor_nuevo = getattr(self, campo)
            
            if valor_original != valor_nuevo:
                # Traducción visual
                estado = " MARCADO" if valor_nuevo else " DESMARCADO"
                nombre_humano = campo.replace('_', ' ').capitalize()
                cambios.append(f"• {nombre_humano}: {estado}")

        if not cambios:
            return "Se guardó la ficha sin alterar checkboxes."
        
        return "\n".join(cambios)

    
    def esta_atrasado(self):
        from django.utils import timezone
        if self.fecha_entrega and not self.aprobacion_final:
            return self.fecha_entrega < timezone.now().date()
        return False

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
        if self.nivel_actual < 0:
            self.nivel_actual = 0
        if self.nivel_actual > 100:
            self.nivel_actual = 100
        

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
        ('Audiovisual', 'Audiovisual'),
        ('Adhesivos (stickers)', 'Adhesivos (stickers)'),
    ]

    codigo = models.CharField(max_length=10, unique=True, editable=False)
    familia = models.CharField(max_length=50, choices=FAMILIAS_SERVICIOS)
    descripcion = models.TextField()
    costo_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    margen_ganancia = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.codigo:
            total_servicios = Servicio.objects.count()
            nuevo_numero = total_servicios + 1
            
            while Servicio.objects.filter(codigo=f'SE-{nuevo_numero:04d}').exists():
                nuevo_numero += 1
                
            self.codigo = f'SE-{nuevo_numero:04d}'
        super().save(*args, **kwargs)

    @property
    def precio_venta(self):
        return self.costo_m2 * (Decimal('1') + (self.margen_ganancia / Decimal('100')))

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

class ContadorGlobal(models.Model):
    ultimo_id = models.PositiveIntegerField(default=0)

    @classmethod
    def obtener_siguiente(cls):
        
        obj, created = cls.objects.get_or_create(id=1)
        obj.ultimo_id += 1
        obj.save()
        return obj.ultimo_id

    class Meta:
        verbose_name = "Contador Global de Cotizaciones"

class CotizacionServicio(models.Model):
    n_seguimiento = models.PositiveIntegerField(unique=True, editable=False, null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    # Quitamos servicio, cantidad y valor_unitario de aquí porque ahora irán en el Detalle
    total_neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.n_seguimiento:
            self.n_seguimiento = ContadorGlobal.obtener_siguiente()
        super().save(*args, **kwargs)

    def get_numero_formateado(self):
        return str(self.n_seguimiento).zfill(5)

# NUEVA CLASE PARA SOPORTAR MUCHOS SERVICIOS
class DetalleCotizacionServicio(models.Model):
    cotizacion = models.ForeignKey(CotizacionServicio, related_name='detalles', on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)
    cantidad_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    valor_unitario_m2 = models.DecimalField(max_digits=12, decimal_places=2)

class CotizacionArticulo(models.Model):
    n_seguimiento = models.PositiveIntegerField(unique=True, editable=False, null=True)
    n_presupuesto = models.AutoField(primary_key=True)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    total_final = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si es nueva, pedimos el siguiente número al contador
        if not self.n_seguimiento:
            self.n_seguimiento = ContadorGlobal.obtener_siguiente()
        super().save(*args, **kwargs)

    def get_numero_formateado(self):
        """Retorna el ID con ceros a la izquierda (ej: 00006)"""
        return str(self.n_seguimiento).zfill(5)

    def __str__(self):
        return f"Presupuesto {self.get_numero_formateado()} - {self.cliente.razon_social}"

class DetalleCotizacionArticulo(models.Model):
    cotizacion = models.ForeignKey(CotizacionArticulo, related_name='detalles', on_delete=models.PROTECT)
    articulo = models.ForeignKey('usuarios.Articulo', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class AccionHistorial(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    accion = models.CharField(max_length=255) 
    fecha = models.DateTimeField(auto_now_add=True)
    detalles = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha'] 

class Factura(models.Model):
    TIPO_ORIGEN = [('servicio', 'Servicio'), ('articulo', 'Artículo')]
    
    ESTADO_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('abonado', 'Abonado'),
    ]

    # Campos base
    n_factura = models.CharField(max_length=50, verbose_name="Número de Factura")
    proceso_asociado = models.ForeignKey('Proceso', on_delete=models.SET_NULL, null=True, blank=True, related_name='facturas')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='facturas')
    archivo_pdf = models.FileField(upload_to='facturas/pdfs/')
    tipo = models.CharField(max_length=10, choices=TIPO_ORIGEN, null=True, blank=True)
    origen_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Campos financieros
    fecha_facturacion = models.DateField()
    total_facturado = models.DecimalField(max_digits=12, decimal_places=2) # Sin decimales para CLP
    iva = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    # Gestión de pago
    estado_pago = models.CharField(max_length=15, choices=ESTADO_PAGO, default='pendiente')
    valor_abonado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.iva = self.total_facturado * Decimal('0.19')
        super().save(*args, **kwargs)

    @property
    def saldo_pendiente(self):
        return self.total_facturado - self.valor_abonado

    @property
    def fecha_vencimiento(self):
        if not self.fecha_facturacion or not self.cliente:
            return None
        
        # Convertimos '60', '30', etc. a un número entero
        dias_credito = int(self.cliente.condiciones_pago)
        return self.fecha_facturacion + timedelta(days=dias_credito)

    @property
    def estado_vencimiento(self):
        # Si ya está pagada, no hay deuda que cobrar
        if self.estado_pago == 'pagado':
            return 'al_dia'
        
        vencimiento = self.fecha_vencimiento
        if vencimiento and timezone.now().date() > vencimiento:
            return 'atrasada'
        
        return 'pendiente'

class Venta(models.Model):
    n_factura = models.CharField(max_length=50, verbose_name="Número de Factura")
    factura = models.OneToOneField(Factura, on_delete=models.CASCADE, related_name='venta_asociada', null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas_registradas')
    
    # Valores contables
    monto_neto = models.DecimalField(max_digits=12, decimal_places=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=0)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Venta Fec: {self.fecha_registro.strftime('%d/%m/%Y')} - Factura: {self.n_factura}"

class Compra(models.Model):
    ESTADO_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('abonado', 'Abonado'),
    ]

    n_factura = models.CharField(max_length=50, verbose_name="Número de Factura/Boleta", null=True, blank=True)
    proveedor = models.ForeignKey('clientes.Proveedor', on_delete=models.PROTECT, related_name='compras_registradas')
    archivo_compra = models.FileField(upload_to='compras/respaldos/')
    fecha_registro = models.DateField() # Quitamos el auto_now_add para que sea editable
    
    # Campos financieros (Copia de la lógica de Factura pero para egresos)
    total_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_pago = models.CharField(max_length=15, choices=ESTADO_PAGO, default='pendiente')
    valor_abonado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def saldo_pendiente(self):
        return self.total_compra - self.valor_abonado

    def __str__(self):
        return f"Compra {self.n_factura} - {self.proveedor.razon_social}"
    @property
    def fecha_vencimiento_calculada(self):
        # Tomamos los días de la condición de pago del proveedor
        dias_credito = int(self.proveedor.condiciones_pago)
        return self.fecha_registro + timedelta(days=dias_credito)

    @property
    def estado_vencimiento(self):
        if self.estado_pago == 'pagado':
            return 'finalizado'
        
        hoy = timezone.now().date()
        vencimiento = self.fecha_vencimiento_calculada
        
        if hoy > vencimiento:
            return 'atrasada'
        return 'en_plazo'



class OrdenCompra(models.Model):
    n_orden = models.CharField(max_length=50, unique=True, verbose_name="N° Orden")
    fecha_ingreso = models.DateField(auto_now_add=True)
    proveedor = models.ForeignKey('clientes.Proveedor', on_delete=models.PROTECT, related_name='ordenes')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
    archivo_pdf = models.FileField(upload_to='compras/ordenes_pdf/', null=True, blank=True)

    def __str__(self):
        return f"OC {self.n_orden} - {self.proveedor.razon_social}"

class DetalleOrdenCompra(models.Model):
    orden = models.ForeignKey(OrdenCompra, related_name='detalles', on_delete=models.CASCADE)
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

# Agrega esto a tu models.py
class FotoTerreno(models.Model):
    proceso = models.ForeignKey(Proceso, related_name='fotos_terreno', on_delete=models.CASCADE)
    imagen = models.FileField(upload_to='terreno/%Y/%m/')
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto para {self.proceso.cliente.razon_social}"

class ArchivoProceso(models.Model):
    proceso = models.ForeignKey(Proceso, related_name='archivos', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='aprobaciones/%Y/%m/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Archivo para {self.proceso.cliente.razon_social}"


class LevantamientoTerreno(models.Model):
    proceso = models.OneToOneField(Proceso, on_delete=models.CASCADE, related_name='levantamiento')
    
    # --- UBICACIÓN Y ACCESO ---
    ubicacion = models.CharField(max_length=10, blank=True) # interior / exterior
    altura_instalacion = models.FloatField(default=0.0)
    acceso_escalera = models.BooleanField(default=False)
    acceso_andamio = models.BooleanField(default=False)
    acceso_grua = models.BooleanField(default=False)
    restricciones_acceso = models.TextField(blank=True, null=True)

    # --- MEDIDAS (Agregué ancho y alto que faltaban) ---
    ancho = models.FloatField(default=0.0)
    alto = models.FloatField(default=0.0)
    profundidad_letrero = models.FloatField(default=0.0)

    # --- SOPORTE ---
    soporte_muro = models.BooleanField(default=False)
    soporte_metal = models.BooleanField(default=False)
    soporte_vidrio = models.BooleanField(default=False)
    soporte_panel_compuesto = models.BooleanField(default=False)
    soporte_otro = models.CharField(max_length=100, blank=True, null=True)

    # --- ELÉCTRICO ---
    punto_cercano = models.BooleanField(default=False)
    tablero_accesible = models.BooleanField(default=False) # Agregué este
    voltaje = models.CharField(max_length=50, blank=True, null=True)

    # --- MATERIALES (Cambié nombres para match con HTML) ---
    mat_pvc = models.BooleanField(default=False)
    mat_pvc_lum = models.BooleanField(default=False)
    mat_acrilico = models.BooleanField(default=False)
    mat_adh_nor = models.BooleanField(default=False)
    mat_adh_trans = models.BooleanField(default=False)
    
    # --- TERMINACIÓN ---
    term_ojetillos = models.BooleanField(default=False)
    term_bolsillo = models.BooleanField(default=False)
    term_tubo = models.BooleanField(default=False) # Agregué este
    term_bastidor = models.BooleanField(default=False)
    term_laminado = models.BooleanField(default=False)
    term_troquel = models.BooleanField(default=False)

    # --- RIESGOS (Simplifiqué nombres para match con HTML) ---
    riesgo_altura = models.BooleanField(default=False)
    riesgo_transito = models.BooleanField(default=False)
    riesgo_permiso = models.BooleanField(default=False)
    riesgo_energia = models.BooleanField(default=False)
    tiempo_estimado_instalacion = models.CharField(max_length=100, blank=True)

    # --- FIRMAS ---
    firma_tecnico = models.ImageField(upload_to='firmas/%Y/%m/', blank=True, null=True)
    firma_cliente = models.ImageField(upload_to='firmas/%Y/%m/', blank=True, null=True)
    nombre_cliente_firma = models.CharField(max_length=100, blank=True)

    def detectar_cambios_terreno(self):
        """Compara el estado actual del terreno con la base de datos"""
        if not self.pk:
            return "Primer registro de terreno."

        # Traemos la versión guardada en la BD
        original = LevantamientoTerreno.objects.get(pk=self.pk)
        cambios = []
        
        # Lista de campos que quieres monitorear en terreno
        campos_texto = ['ubicacion', 'voltaje', 'restricciones_acceso', 'soporte_otro']
        campos_bool = [
            'acceso_escalera', 'acceso_andamio', 'acceso_grua', 
            'punto_cercano', 'tablero_accesible', 'soporte_muro',
            'soporte_metal', 'riesgo_altura', 'riesgo_energia'
        ]
        campos_num = ['altura_instalacion', 'ancho', 'alto', 'profundidad_letrero']

        # 1. Comparar Booleans (Checkboxes)
        for campo in campos_bool:
            if getattr(original, campo) != getattr(self, campo):
                estado = "MARCADO" if getattr(self, campo) else "DESMARCADO"
                nombre = campo.replace('_', ' ').capitalize()
                cambios.append(f"• {nombre}: {estado}")

        # 2. Comparar Textos
        for campo in campos_texto:
            v_orig = getattr(original, campo)
            v_nuevo = getattr(self, campo)
            if v_orig != v_nuevo:
                cambios.append(f"• {campo.capitalize()}: {v_orig} -> {v_nuevo}")

        # 3. Comparar Números (Medidas)
        for campo in campos_num:
            if float(getattr(original, campo) or 0) != float(getattr(self, campo) or 0):
                cambios.append(f"• {campo.capitalize()}: {getattr(original, campo)} -> {getattr(self, campo)}")

        if not cambios:
            return "Sin cambios específicos en datos de terreno."
        
        return "\n".join(cambios)

    def __str__(self):
        return f"Levantamiento: {self.proceso.cliente.razon_social}"


@receiver(post_save, sender=Proceso)    
def crear_levantamiento_terreno(sender, instance, created, **kwargs):
        if created:
            LevantamientoTerreno.objects.create(proceso=instance)