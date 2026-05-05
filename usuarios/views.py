from decimal import Decimal
from django.db.models.functions import Cast
from django.shortcuts import render, redirect
from reportlab.lib.utils import ImageReader
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.template.loader import get_template
from django.db import transaction
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm, AuthenticationForm
from .forms import UsuarioForm, EditarUsuarioForm, ProcesoForm, ArticuloForm, ServicioForm, DisenoForm, TallerForm, FacturaForm, CompraForm
from clientes.models import Cliente, Proveedor
from .models import Perfil, Proceso, MaterialStock, Articulo, Servicio, CotizacionArticulo, DetalleCotizacionArticulo,CotizacionServicio, AccionHistorial, Factura, Venta, Compra, OrdenCompra, DetalleOrdenCompra, FotoTerreno, ArchivoProceso, DetalleCotizacionServicio, LevantamientoTerreno
from django.contrib.auth import authenticate, login
from django.db.models import ProtectedError, Max, IntegerField
from .decorators import usuario_tipo_requerido
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os  
from django.conf import settings 
from reportlab.lib.units import cm
from django.contrib.staticfiles import finders
from django.utils import timezone
from datetime import datetime

@login_required
def generar_pdf_cotizacion(request, pk):

    cotizacion = get_object_or_404(CotizacionArticulo, n_presupuesto=pk)
    detalles = cotizacion.detalles.all()
    cliente = cotizacion.cliente
    



    codigo_id = cotizacion.get_numero_formateado()
    
    solo_numero = cotizacion.get_numero_formateado().replace("COT_", "")


    codigo_full = f"COT_ART_{solo_numero}"


    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{codigo_full}.pdf"'

    p = canvas.Canvas(response, pagesize=LETTER)
    p.setTitle(codigo_full)

    width, height = LETTER




    logo_path = finders.find('images/logo.png')
    if logo_path:
        logo = ImageReader(logo_path)
        p.drawImage(logo, 30, height-95, width=175, height=100, preserveAspectRatio=True, mask='auto')




    x_empresa = width - 300
    y_empresa = height - 40
    p.setFont("Helvetica-Bold", 11)
    p.drawString(x_empresa, y_empresa, "USBTECH SPA")
    p.setFont("Helvetica", 9)
    p.drawString(x_empresa, y_empresa-15, "Camino a Montahue #55, San Pedro de La Paz.")
    p.drawString(x_empresa, y_empresa-30, "contacto@usbtech.cl | +56 9 9653 3834")
    p.drawString(x_empresa, y_empresa-45, "Rut: 77.859.775-6")
    p.drawString(x_empresa, y_empresa-60, "Giro: OTRAS ACTIVIDADES ESPECIALIZADAS DE DISEÑO N.C.P")
    p.drawString(x_empresa, y_empresa-75, "www.usbtech.cl")




    p.line(40, height-135, width-40, height-135)
    y_info = height-160

    # --- CONFIGURACIÓN DE ESTILOS PARA TEXTO DINÁMICO ---
    styles = getSampleStyleSheet()
    style_rs = ParagraphStyle(
        'RazonSocialStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
    )

    # Bloque Izquierdo: Datos del Cliente (DINÁMICO)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_info, "Cliente:")
    
    # Razón Social con Paragraph para evitar choques
    razon_social_html = f"Razón Social: {cliente.razon_social.upper()}"
    p_rs = Paragraph(razon_social_html, style_rs)
    w_rs, h_rs = p_rs.wrap(300, height) # Ancho de 300 para no tocar la columna derecha
    p_rs.drawOn(p, 40, y_info - 15 - (h_rs - 9))

    # El siguiente campo (RUT) se calcula según cuánto ocupó la Razón Social
    y_campos_debajo = y_info - 15 - h_rs - 5 

    p.setFont("Helvetica", 9)
    p.drawString(40, y_campos_debajo, f"RUT: {cliente.rut}")
    p.drawString(40, y_campos_debajo - 15, f"Dirección: {cliente.direccion}")
    p.drawString(40, y_campos_debajo - 30, f"Correo: {cliente.correo}")
    p.drawString(40, y_campos_debajo - 45, f"Teléfono: {cliente.telefono}")

    # Bloque Derecho: Datos de la Cotización (FIJO)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-230, y_info, f"Presupuesto: {solo_numero}") 
    
    p.setFont("Helvetica", 9)
    p.drawString(width-230, y_info-15, f"Fecha: {cotizacion.fecha.strftime('%d-%m-%Y')}")

    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-230, y_info-30, "Cond. Pago:")
    p.setFont("Helvetica", 9)
    condiciones = cliente.get_condiciones_pago_display() if hasattr(cliente, 'get_condiciones_pago_display') else "N/A"
    p.drawString(width-170, y_info-30, condiciones)

    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-230, y_info-45, "Vendedor:")
    
    p.setFont("Helvetica", 9)
    vendedor_codigo = "N/A"
    if cotizacion.usuario and hasattr(cotizacion.usuario, 'perfil'):
        vendedor_codigo = cotizacion.usuario.perfil.codigo_vendedor or "Sin código"
    
    p.drawString(width-170, y_info-45, str(vendedor_codigo))

    # Calculamos el separador para que siempre esté debajo de todo el encabezado
    # y_info - 90 era tu valor original para bloques de una sola línea
    y_final_izq = y_campos_debajo - 60
    y_final_der = y_info - 90
    y_separador = min(y_final_izq, y_final_der)

    p.line(40, y_separador, width-40, y_separador)

    # Tabla de artículos
    y = y_separador - 25 
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Descripción del articulo")
    p.drawString(330, y, "Cantidad")
    p.drawString(420, y, "Precio Unitario")
    p.drawString(520, y, "Total")
    p.line(40, y-5, width-40, y-5)

    y -= 25
    p.setFont("Helvetica", 9)
    neto = Decimal("0.00")

    for item in detalles:

        precio_final = item.precio_unitario if (item.precio_unitario and item.precio_unitario > 0) else item.articulo.precio_unitario
        subtotal = item.cantidad * precio_final
        neto += subtotal


        descripcion = item.articulo.descripcion[:60]
        p.drawString(40, y, descripcion)
        p.drawRightString(360, y, f"{item.cantidad:,.0f}")
        p.drawRightString(470, y, f"$ {precio_final:,.2f}")
        p.drawRightString(560, y, f"$ {subtotal:,.2f}")

        y -= 18


        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 9)





    if y < 180:
        p.showPage()
        y = height - 50

    y_final = y - 40 


    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_final-40, "DATOS BANCARIOS")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_final-55, "USBTECH SPA | Rut: 77.859.775-6")
    p.drawString(40, y_final-70, "Banco Santander | Cuenta Corriente: 98308091")
    p.drawString(40, y_final-85, "contacto@usbtech.cl")


    iva = neto * Decimal("0.19")
    total = neto + iva

    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, y_final, "Subtotal")
    p.drawRightString(560, y_final, f"$ {neto:,.2f}")
    p.drawString(400, y_final-18, "IVA (19)%")
    p.drawRightString(560, y_final-18, f"$ {iva:,.2f}")
    
    p.line(390, y_final-30, width-40, y_final-30)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(400, y_final-45, "Total")
    p.drawRightString(560, y_final-45, f"$ {total:,.2f}")

    p.showPage()
    p.save()
    return response
    
@require_POST
@login_required
def actualizar_stock_ajax(request):
    material_id = request.POST.get('id')
    accion = request.POST.get('accion')
    material = get_object_or_404(MaterialStock, id=material_id)

    nivel_anterior = material.nivel_actual

    if accion == 'up':
        material.nivel_actual += 5
    elif accion == 'down':
        material.nivel_actual -= 5
    
    material.save()
    


    umbrales_criticos = [30, 20, 10, 0]
    enviar_alerta = False

    for umbral in umbrales_criticos:


        if material.nivel_actual <= umbral and nivel_anterior > umbral:
            enviar_alerta = True
            break 

    if enviar_alerta:
        try:

            estado_texto = "AGOTADO" if material.nivel_actual == 0 else f"al {material.nivel_actual}%"
            
            cuerpo_mensaje = (
                f"⚠️ ALERTA DE STOCK CRÍTICO ⚠️\n\n"
                f"El material '{material.nombre}' ({material.variedad}) está {estado_texto}.\n\n"
                f"Nivel actual: {material.nivel_actual}%\n"
                f"RECOMENDACIÓN: Por favor, gestione la compra de reposición de inmediato.\n\n"
                f"--- Mensaje automático del Sistema de Inventario de USBTECH ---"
            )

            send_mail(
                subject=f'⚠️ STOCK CRÍTICO ({material.nivel_actual}%): {material.nombre}',
                message=cuerpo_mensaje,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=['correo@example.cl'],
                fail_silently=False,
            )
            print(f"Alerta enviada: {material.nombre} al {material.nivel_actual}%")
        except Exception as e:
            print(f"Error al enviar alerta: {e}")

    return JsonResponse({
        'nuevo_nivel': material.nivel_actual,
        'status': 'success'
    })

@login_required
def login_redirect(request):
    user = request.user
    
    if user.is_superuser:
        return redirect('dashboard')

    tipo = getattr(user.perfil, 'tipo_usuario', None)

    if tipo == 'taller':
        return redirect('dashboard_taller')

    elif tipo == 'vendedor':
        return redirect('menu_cotizaciones')
    
    elif tipo in ['diseno', 'diseño']:
        return redirect('dashboard_diseno')
    
    elif tipo in ['admin', 'administrador', 'administracion']: 
        return redirect('dashboard')
    

    return redirect('dashboard')


def login_usuario(request):
    """Vista personalizada de login que redirige según tipo de usuario."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')


        user = authenticate(request, username=username, password=password)

        if user is not None:

            if not user.is_active:
                messages.error(request, "Usuario desactivado. Contacte al administrador.")
                return redirect('login')


            login(request, user)


            

            if user.is_superuser:
                return redirect('dashboard')


            try:
                tipo = user.perfil.tipo_usuario
            except AttributeError:
                tipo = None


            if tipo == 'taller':
                return redirect('dashboard_taller')
            
            elif tipo in ['diseno', 'diseño']:
                return redirect('dashboard_diseno')
            
            elif tipo in ['admin', 'administrador', 'administracion']:
                return redirect('dashboard')


            return redirect('dashboard')

        else:
            messages.error(request, "Usuario o contraseña incorrecta")

    return render(request, 'usuarios/login.html')

PASSWORD_TRANSLATIONS = {
    "This password is too short. It must contain at least 8 characters.": 
        "La contraseña debe tener al menos 8 caracteres.",

    "This password is too common.": 
        "La contraseña es demasiado común.",

    "This password is entirely numeric.": 
        "La contraseña no puede ser solo números.",

    "The two password fields didn’t match.": 
        "Las contraseñas no coinciden.",

    "This password is too similar to the username.": 
        "La contraseña es muy parecida al nombre de usuario.",

    "This password is too similar to the email address.": 
        "La contraseña es muy parecida al correo electrónico.",
}





@login_required
def dashboard_taller(request):

    procesos = Proceso.objects.filter(
        estado='taller', 
        responsable_taller=request.user.username
    ).order_by('-creado')
    
    if request.method == 'POST':
        proceso_id = request.POST.get('proceso_id')
        proceso = get_object_or_404(Proceso, id=proceso_id)
        

        if proceso.responsable_taller != request.user.username:
            messages.error(request, "No tienes permiso para editar este proceso.")
            return redirect('dashboard_taller')


        form = TallerForm(request.POST, instance=proceso)
        
        if form.is_valid():
            form.save()
            messages.success(request, f"Avance de producción guardado para Proceso {proceso.id}.")
            
            AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"MODIFICÓ datos técnicos del proceso ID {proceso.id} (Taller)"
            )
            return redirect('dashboard_taller')
    else:



        proceso_id = request.GET.get('edit_id')
        if proceso_id:
            proceso_editar = get_object_or_404(Proceso, id=proceso_id)
            form = TallerForm(instance=proceso_editar)
        else:
            form = TallerForm()

    return render(request, 'usuarios/dashboard_taller.html', {
        'form': form, 
        'procesos': procesos
    })

@login_required
def lista_articulos(request):
    articulos = Articulo.objects.all().order_by('-id')

    busqueda_codigo = request.GET.get('codigo')
    busqueda_familia = request.GET.get('familia')

    if busqueda_codigo:
        articulos = articulos.filter(codigo__icontains=busqueda_codigo)

    if busqueda_familia:
        articulos = articulos.filter(familia=busqueda_familia)

    paginator = Paginator(articulos, 5)  
    page_number = request.GET.get('page')
    articulos = paginator.get_page(page_number)

    familias = Articulo.FAMILIAS_CHOICES

    return render(request, 'usuarios/lista_articulos.html', {
        'articulos': articulos,
        'familias': familias,
        'busqueda_codigo': busqueda_codigo,
        'busqueda_familia': busqueda_familia
    })
@login_required
def lista_servicios(request):
    servicios = Servicio.objects.all().order_by('-id')

    busqueda_codigo = request.GET.get('codigo')
    busqueda_familia = request.GET.get('familia')

    if busqueda_codigo:
        servicios = servicios.filter(codigo__icontains=busqueda_codigo)

    if busqueda_familia:
        servicios = servicios.filter(familia=busqueda_familia)


    paginator = Paginator(servicios, 5)  
    page_number = request.GET.get('page')
    servicios = paginator.get_page(page_number)

    familias_opciones = Servicio.FAMILIAS_SERVICIOS 

    return render(request, 'usuarios/lista_servicios.html', {
        'servicios': servicios,
        'familias': familias_opciones,
        'busqueda_codigo': busqueda_codigo,
        'busqueda_familia': busqueda_familia
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def crear_articulo(request):
    if request.method == 'POST':
        form = ArticuloForm(request.POST)
        if form.is_valid():
            articulo = form.save()
            
         
            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"CATÁLOGO: Creó Artículo {articulo.codigo}",
                detalles=(
                    f"Descripción: {articulo.descripcion}\n"
                    f"Familia: {articulo.familia}\n"
                    f"Costo Compra: ${articulo.costo_compra:,}\n".replace(",", ".") +
                    f"Precio Unitario: ${articulo.precio_unitario:,}\n".replace(",", ".") +
                    f"Margen de Ganancia: {articulo.margen_ganancia}%" 
                )
            )

            messages.success(request, f"Artículo {articulo.codigo} creado correctamente.")
            return redirect('lista_articulos')
        else:
            messages.error(request, "Error al crear el artículo. Revisa los datos.")
    else:
        form = ArticuloForm()
    return render(request, 'usuarios/crear_articulo.html', {'form': form, 'editando': False})


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_articulo(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    

    precio_ant = articulo.precio_unitario
    costo_ant = articulo.costo_compra
    margen_ant = articulo.margen_ganancia
    desc_ant = articulo.descripcion

    if request.method == 'POST':
        form = ArticuloForm(request.POST, instance=articulo)
        if form.is_valid():
            articulo_editado = form.save()
            

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"CATÁLOGO: Editó Artículo {articulo_editado.codigo}",
                detalles=(
                    f"Cambios detectados en la ficha:\n"
                    f"• Descripción: {desc_ant} -> {articulo_editado.descripcion}\n"
                    f"• Costo: ${costo_ant:,} -> ${articulo_editado.costo_compra:,}\n".replace(",", ".") +
                    f"• Precio: ${precio_ant:,} -> ${articulo_editado.precio_unitario:,}\n".replace(",", ".") +
                    f"• Margen de Ganancia: {margen_ant}% -> {articulo_editado.margen_ganancia}%"
                )
            )

            messages.success(request, f"Artículo {articulo.codigo} actualizado.")
            return redirect('lista_articulos')
    else:
        form = ArticuloForm(instance=articulo)
    
    return render(request, 'usuarios/crear_articulo.html', {
        'form': form, 
        'editando': True
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_articulo(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    codigo_articulo = articulo.codigo
    info_respaldo = f"Desc: {articulo.descripcion} | Familia: {articulo.familia}"
    
    try:

        AccionHistorial.objects.create(
            usuario=request.user,
            accion=f"CATÁLOGO: Eliminó Artículo {codigo_articulo}",
            detalles=f"Datos del artículo eliminado:\n{info_respaldo}"
        )
        
        articulo.delete()
        messages.success(request, f"Artículo {codigo_articulo} eliminado correctamente.")
        
    except ProtectedError:

        AccionHistorial.objects.create(
            usuario=request.user,
            accion=f"SEGURIDAD: Intento fallido eliminar {codigo_articulo}",
            detalles=f"El sistema bloqueó la eliminación porque el artículo tiene facturas o cotizaciones asociadas."
        )
        messages.error(request, f"No se puede eliminar el artículo {codigo_articulo} porque tiene historial de movimientos.")
    
    return redirect('lista_articulos')
    


@login_required
@usuario_tipo_requerido('admin', 'administracion', 'taller')
def stock_view(request):
    materiales = MaterialStock.objects.all().order_by('categoria')

    context = {
        'materiales': materiales,
    }
    
    return render(request, 'usuarios/stock.html', context)

@login_required
def editar_proceso(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)

    levantamiento, _ = LevantamientoTerreno.objects.get_or_create(proceso=proceso) 
    cliente_original = proceso.cliente 

    if request.method == 'POST':
        form_taller = TallerForm(request.POST, instance=proceso)
        
        if form_taller.is_valid():

            proceso_editado = form_taller.save(commit=False)
            proceso_editado.cliente = cliente_original
            proceso_editado.mediciones_taller_json = request.POST.get('mediciones_taller_json')
            proceso_editado.save()


            def limpiar_float(val):
                if not val: return 0.0
                try: return float(str(val).replace(',', '.'))
                except: return 0.0


            levantamiento.ubicacion = request.POST.get('terreno_ubicacion')
            levantamiento.altura_instalacion = limpiar_float(request.POST.get('terreno_altura_m'))
            levantamiento.ancho = limpiar_float(request.POST.get('medida_ancho'))
            levantamiento.alto = limpiar_float(request.POST.get('medida_alto'))
            levantamiento.profundidad_letrero = limpiar_float(request.POST.get('medida_profundidad'))
            

            levantamiento.acceso_escalera = 'acc_escalera' in request.POST
            levantamiento.acceso_andamio = 'acc_andamio' in request.POST
            levantamiento.acceso_grua = 'acc_grua' in request.POST
            levantamiento.restricciones_acceso = request.POST.get('acc_restricciones')


            levantamiento.punto_cercano = 'elec_punto' in request.POST
            levantamiento.tablero_accesible = 'elec_tablero' in request.POST
            levantamiento.voltaje = request.POST.get('elec_voltaje')


            levantamiento.soporte_muro = 'sup_muro' in request.POST
            levantamiento.soporte_metal = 'sup_metal' in request.POST
            levantamiento.soporte_panel_compuesto = 'sup_panel' in request.POST
            levantamiento.soporte_vidrio = 'sup_vidrio' in request.POST
            levantamiento.soporte_otro = request.POST.get('sup_otro')


            levantamiento.mat_pvc = 'mat_pvc' in request.POST
            levantamiento.mat_pvc_lum = 'mat_pvc_lum' in request.POST
            levantamiento.mat_acrilico = 'mat_acrilico' in request.POST
            levantamiento.mat_adh_nor = 'mat_adh_nor' in request.POST
            levantamiento.mat_adh_trans = 'mat_adh_trans' in request.POST


            levantamiento.term_ojetillos = 'term_ojetillos' in request.POST
            levantamiento.term_bolsillo = 'term_bolsillo' in request.POST
            levantamiento.term_tubo = 'term_tubo' in request.POST
            levantamiento.term_bastidor = 'term_bastidor' in request.POST
            levantamiento.term_laminado = 'term_laminado' in request.POST
            levantamiento.term_troquel = 'term_troquel' in request.POST


            levantamiento.riesgo_altura = 'r_altura' in request.POST
            levantamiento.riesgo_transito = 'r_transito' in request.POST
            levantamiento.riesgo_permiso = 'r_permiso' in request.POST
            levantamiento.riesgo_energia = 'r_energia' in request.POST
            levantamiento.tiempo_estimado_instalacion = request.POST.get('r_tiempo_estimado')

            levantamiento.save() 




            cambios = []


            cambios.append(f"ORDEN DE PROCESO: #{proceso.id}")
            cambios.append(f"CLIENTE: {proceso_editado.cliente.razon_social}")
            cambios.append(f"ESTADO TALLER: {proceso_editado.get_estado_display()}")

            insumos_seleccionados = []
            campos_insumos = ["acrilico", "sintra", "ojetillo", "ad_prom", "ad_vehicular", "empavonado", "microperf", "sellado", "tela_pvc"]
            for campo in campos_insumos:
                if form_taller.cleaned_data.get(campo):

                    insumos_seleccionados.append(form_taller.fields[campo].label)

            cambios.append(f"\n--- INSUMOS Y MATERIALES ---")
            cambios.append(f"Seleccionados: {', '.join(insumos_seleccionados) if insumos_seleccionados else 'Ninguno'}")


            prod = []
            if form_taller.cleaned_data.get('impresion'): prod.append("Impresión")
            if form_taller.cleaned_data.get('corte'): prod.append("Corte")
            cambios.append(f"Producción: {', '.join(prod) if prod else 'No especificado'}")


            mediciones_raw = request.POST.get('mediciones_taller_json', '[]')
            try:
                mediciones_lista = json.loads(mediciones_raw)
                if mediciones_lista:
                    cambios.append(f"\n--- MEDICIONES DE VEHÍCULO ---")
                    for item in mediciones_lista:

                        cambios.append(f"• {item.get('categoria')}: {item.get('nombre')} ({item.get('medida')} cm)")
            except:
                cambios.append(f"\n[Error al leer mediciones de vehículo]")


            cambios.append(f"\n--- LEVANTAMIENTO DE TERRENO ---")
            cambios.append(f"Ubicación: {levantamiento.ubicacion}")
            cambios.append(f"Medidas: {levantamiento.ancho}x{levantamiento.alto}x{levantamiento.profundidad_letrero} cm")
            cambios.append(f"Altura de Instalación: {levantamiento.altura_instalacion}m")


            accesos = []
            if levantamiento.acceso_escalera: accesos.append("Escalera")
            if levantamiento.acceso_andamio: accesos.append("Andamio")
            if levantamiento.acceso_grua: accesos.append("Grúa")
            cambios.append(f"Accesos: {', '.join(accesos) if accesos else 'No especificado'}")

            if levantamiento.restricciones_acceso:
                cambios.append(f"Restricciones: {levantamiento.restricciones_acceso}")


            sops = []
            if levantamiento.soporte_muro: sops.append("Muro")
            if levantamiento.soporte_metal: sops.append("Estructura Metal")
            if levantamiento.soporte_panel_compuesto: sops.append("Panel Compuesto")
            if levantamiento.soporte_vidrio: sops.append("Vidrio")
            if levantamiento.soporte_otro: sops.append(f"Otro ({levantamiento.soporte_otro})")
            cambios.append(f"Soportes: {', '.join(sops) if sops else 'Sin definir'}")


            mats = []
            if levantamiento.mat_pvc: mats.append("PVC")
            if levantamiento.mat_pvc_lum: mats.append("PVC Lumínico")
            if levantamiento.mat_acrilico: mats.append("Acrílico")
            if levantamiento.mat_adh_nor: mats.append("Adhesivo Normal")
            if levantamiento.mat_adh_trans: mats.append("Adhesivo Transparente")
            cambios.append(f"Materiales: {', '.join(mats) if mats else 'Sin definir'}")


            terms = []
            if levantamiento.term_ojetillos: terms.append("Ojetillos")
            if levantamiento.term_bolsillo: terms.append("Bolsillo")
            if levantamiento.term_tubo: terms.append("Tubo")
            if levantamiento.term_bastidor: terms.append("Bastidor")
            if levantamiento.term_laminado: terms.append("Laminado")
            if levantamiento.term_troquel: terms.append("Troquelado")
            cambios.append(f"Terminaciones: {', '.join(terms) if terms else 'Sin terminaciones'}")


            riesgos_list = []
            if levantamiento.riesgo_altura: riesgos_list.append("Riesgo Altura")
            if levantamiento.riesgo_transito: riesgos_list.append("Riesgo Transito")
            if levantamiento.riesgo_permiso: riesgos_list.append("Requiere Permiso")
            if levantamiento.riesgo_energia: riesgos_list.append("Riesgo Energia")
            cambios.append(f"Riesgos: {', '.join(riesgos_list) if riesgos_list else 'Sin riesgos críticos'}")

            cambios.append(f"Tiempo Estimado Instalación: {levantamiento.tiempo_estimado_instalacion}")


            detalle_final = "\n".join(cambios)


            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"FICHA TÉCNICA: Actualizó datos de {proceso_editado.cliente.razon_social}",
                detalles=detalle_final
            )


            messages.success(request, "¡Ficha técnica y de taller actualizada con éxito!")
            return redirect('dashboard_taller')
            
    else:

        form_taller = TallerForm(instance=proceso)
    
    return render(request, 'usuarios/editar_proceso.html', {
        'form': form_taller,
        'proceso': proceso,
        'levantamiento': levantamiento
    })


@require_POST
@login_required
@usuario_tipo_requerido('admin', 'administracion', 'taller')
def editar_material_nombre_ajax(request):

    material_id = request.POST.get('id')
    nuevo_nombre = request.POST.get('nombre')
    nueva_variedad = request.POST.get('variedad')
    
    try:
        material = MaterialStock.objects.get(id=material_id)
        material.nombre = nuevo_nombre
        material.variedad = nueva_variedad
        material.save()
        return JsonResponse({'status': 'success'})
    except MaterialStock.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Material no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@usuario_tipo_requerido('admin','administracion')
def toggle_usuario(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    if request.user == user_obj:
        messages.error(request, "No puedes desactivar tu propio usuario.")
        return redirect('lista_usuarios')


    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    if user_obj.is_active:
        messages.success(request, f"Usuario {user_obj.username} activado correctamente.")
    else:
        messages.success(request, f"Usuario {user_obj.username} desactivado correctamente.")

    return redirect('lista_usuarios')

@login_required
@usuario_tipo_requerido ('admin', 'administracion')
def dashboard(request):
    user = request.user

    try:

        tipo = user.perfil.tipo_usuario
    except (AttributeError, User.perfil.RelatedObjectDoesNotExist):

        tipo = 'administracion' if user.is_superuser else None


    if not user.is_superuser and tipo != 'administracion':
        if tipo in ['diseno', 'diseño']:
            return redirect('dashboard_diseno')
        elif tipo == 'taller':
            return redirect('dashboard_taller')
        elif tipo == 'vendedor':
            return redirect('menu_cotizaciones')


    en_diseno_count = Proceso.objects.filter(estado='diseno').count()
    en_taller_count = Proceso.objects.filter(estado='taller').count()
    pendientes_cierre = Proceso.objects.filter(estado='finalizado').count()
    

    procesos = Proceso.objects.all().order_by('-creado')[:20] 


    clientes = Cliente.objects.all().order_by('razon_social')
    facturas_list = Factura.objects.all().order_by('-n_factura')
    

    familias_servicios = Servicio.FAMILIAS_SERVICIOS
    


    usuarios_diseno = User.objects.filter(
        perfil__tipo_usuario__in=['diseno', 'diseño']
    ).distinct()
    
    usuarios_taller = User.objects.filter(
        perfil__tipo_usuario='taller'
    ).distinct()


    context = {

        'en_diseno_count': en_diseno_count,
        'en_taller_count': en_taller_count,
        'pendientes_cierre': pendientes_cierre,
        

        'procesos': procesos, 
        

        'clientes': clientes,
        'familias_servicios': familias_servicios, 
        'usuarios_diseno': usuarios_diseno,
        'usuarios_taller': usuarios_taller,
        'facturas_list': facturas_list,
        

        'clientes_count': clientes.count(),
        'hoy': timezone.now(),
    }

    return render(request, 'usuarios/dashboard.html', context)

@login_required
@usuario_tipo_requerido('admin','administracion')
def lista_usuarios(request):

    usuarios = User.objects.select_related('perfil').all().order_by('username')


    usuario = request.GET.get('usuario', '')
    email = request.GET.get('email', '')
    rol = request.GET.get('rol', '')

    if usuario:
        usuarios = usuarios.filter(username__icontains=usuario)

    if email:
        usuarios = usuarios.filter(email__icontains=email)

    if rol:
        usuarios = usuarios.filter(perfil__tipo_usuario=rol)


    paginator = Paginator(usuarios, 5)   # 5 usuarios por página
    page_number = request.GET.get('page')
    usuarios = paginator.get_page(page_number)

    context = {
        'usuarios': usuarios,
        'usuario': usuario,
        'email': email,
        'rol': rol,
    }

    return render(request, 'usuarios/lista_usuarios.html', context)


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def registrar_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            tipo = form.cleaned_data['tipo_usuario']
            codigo = form.cleaned_data.get('codigo_vendedor')
            
            Perfil.objects.create(
                user=user,
                tipo_usuario=tipo,
                codigo_vendedor=codigo
            )



            nombre_para_historial = f"{user.first_name} {user.last_name}".strip()
            if not nombre_para_historial:
                nombre_para_historial = user.username

            AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"USUARIOS: Creó nuevo usuario - {user.username}",
                detalles=(
                    f"Nombre : {nombre_para_historial}\n"
                    f"Email: {user.email}\n"
                    f"Rol asignado: {tipo}"
                )
            )

            messages.success(request, "Usuario creado correctamente")
            return redirect('lista_usuarios')

        else:
            for errors in form.errors.values():
                for error in errors:
                    mensaje = PASSWORD_TRANSLATIONS.get(error, error)
                    messages.error(request, mensaje)
    else:
        form = UsuarioForm()
    return render(request, 'usuarios/registrar_usuario.html', {'form': form})


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    

    rol_anterior = usuario.perfil.get_tipo_usuario_display() if hasattr(usuario, 'perfil') else "Sin Rol"

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():

            user_editado = form.save()
            

            nuevo_rol_cod = form.cleaned_data.get('tipo_usuario')
            nuevo_codigo_vendedor = form.cleaned_data.get('codigo_vendedor')
            perfil, created = Perfil.objects.update_or_create(
                user=user_editado,
                defaults={'tipo_usuario': nuevo_rol_cod,
                'codigo_vendedor': nuevo_codigo_vendedor}
            )
            

            nombre_completo = f"{user_editado.first_name} {user_editado.last_name}".strip()
            identificador = nombre_completo if nombre_completo else user_editado.username


            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"USUARIOS: Editó datos de {user_editado.username}",
                detalles=(
                    f"Nombre en Sistema: {identificador}\n"
                    f"Email: {user_editado.email}\n"
                    f"Rol: {rol_anterior} -> {perfil.get_tipo_usuario_display()}"
                )
            )
            
            messages.success(request, "Usuario y Rol actualizados correctamente")
            return redirect('lista_usuarios')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = EditarUsuarioForm(instance=usuario)

    return render(request, 'usuarios/editar_usuario.html', {
        'form': form,
        'usuario': usuario
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)

    if request.user == usuario:
        messages.error(request, "Operación cancelada: No puedes eliminar tu propia cuenta.")
        return redirect('lista_usuarios')

    if usuario.is_superuser:
        messages.error(request, "Acceso denegado: No se pueden eliminar superusuarios.")
        return redirect('lista_usuarios')

    if request.method == 'POST':
        try:
            nombre_u = usuario.username
            rol_u = usuario.perfil.tipo_usuario if hasattr(usuario, 'perfil') else "N/A"
            

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"USUARIOS: ELIMINÓ USUARIO - {nombre_u}",
                detalles=f"El usuario con rol '{rol_u}' fue borrado permanentemente del sistema."
            )

            usuario.delete()
            messages.success(request, f"El usuario '{nombre_u}' ha sido eliminado.")
            return redirect('lista_usuarios')
            
        except ProtectedError:

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"SEGURIDAD: Intento de eliminar usuario vinculado - {usuario.username}",
                detalles="El sistema bloqueó el borrado porque el usuario tiene registros asociados (ventas, procesos, etc)."
            )
            messages.error(request, "No se puede eliminar: El usuario tiene registros vinculados.")
            return redirect('lista_usuarios')

    return render(request, 'usuarios/confirmar_eliminar_usuario.html', {'usuario': usuario})


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def crear_servicio(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            servicio = form.save()
            

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"SERVICIOS: Creó nuevo servicio {servicio.codigo}",
                detalles=(
                    f"Descripción: {servicio.descripcion}\n"
                    f"Familia: {servicio.familia}\n"
                    f"Costo por m²: ${servicio.costo_m2:,}".replace(",", ".")
                )
            )

            messages.success(request, f"Servicio {servicio.codigo} creado correctamente.")
            return redirect('lista_servicios')
    else:
        form = ServicioForm()
    return render(request, 'usuarios/crear_servicio.html', {'form': form, 'editando': False})

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    

    costo_ant = servicio.costo_m2
    desc_ant = servicio.descripcion

    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            servicio_editado = form.save()
            

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"SERVICIOS: Editó servicio {servicio_editado.codigo}",
                detalles=(
                    f"Cambios realizados:\n"
                    f"• Descripción: {desc_ant} -> {servicio_editado.descripcion}\n"
                    f"• Costo por m²: ${costo_ant:,} -> ${servicio_editado.costo_m2:,}".replace(",", ".")
                )
            )

            messages.success(request, f"Servicio {servicio.codigo} actualizado.")
            return redirect('lista_servicios')
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'usuarios/crear_servicio.html', {'form': form, 'editando': True})

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    codigo_eliminado = servicio.codigo
    info_respaldo = f"Desc: {servicio.descripcion} | Familia: {servicio.familia}"
    
    try:

        AccionHistorial.objects.create(
            usuario=request.user,
            accion=f"SERVICIOS: Eliminó servicio {codigo_eliminado}",
            detalles=f"Respaldo de datos eliminados:\n{info_respaldo}"
        )
        
        servicio.delete()
        messages.success(request, f"Servicio {codigo_eliminado} eliminado con éxito.")
        
    except ProtectedError:

        AccionHistorial.objects.create(
            usuario=request.user,
            accion=f"SEGURIDAD: Bloqueó eliminación de {codigo_eliminado}",
            detalles="El servicio no pudo ser borrado porque está referenciado en cotizaciones activas."
        )
        messages.error(request, f"No se puede eliminar el servicio {codigo_eliminado} porque ya está vinculado a documentos existentes.")
    
    return redirect('lista_servicios')

@login_required
def menu_cotizaciones(request):
    return render(request, 'usuarios/menu_cotizaciones.html')

@login_required
def cotizar_servicio_nuevo(request):
    context = {
        'clientes': Cliente.objects.all().order_by('razon_social'),
        'servicios': Servicio.objects.all().order_by('codigo'),
    }
    return render(request, 'usuarios/cotizar_servicio.html', context)



@login_required
@require_POST
def guardar_cotizacion_servicio(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cliente_id = data.get('cliente_id')
            items = data.get('items')

            cotizacion_id = data.get('cotizacion_id')

            if not items:
                return JsonResponse({'status': 'error', 'message': 'No hay servicios en la lista'})


            if cotizacion_id and cotizacion_id != "null":
                cotizacion = get_object_or_404(CotizacionServicio, id=cotizacion_id)

                cotizacion.detalles.all().delete()

                cotizacion.cliente_id = cliente_id
            else:
                cotizacion = CotizacionServicio(cliente_id=cliente_id, usuario=request.user)
            
            cotizacion.save()


            total_neto = 0
            for item in items:

                servicio_instancia = get_object_or_404(Servicio, id=item['id'])
                
                cantidad = Decimal(str(item['cantidad']))
                precio = Decimal(str(item['precio_unitario']))
                subtotal = cantidad * precio
                total_neto += subtotal

                DetalleCotizacionServicio.objects.create(
                    cotizacion=cotizacion,
                    servicio=servicio_instancia,
                    cantidad_m2=cantidad,
                    valor_unitario_m2=precio
                )


            cotizacion.total_neto = total_neto
            cotizacion.save()

            return JsonResponse({'status': 'success', 'message': 'Cotización guardada correctamente'})

        except Servicio.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Uno de los servicios seleccionados ya no existe en el catálogo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

@login_required
def cotizar_articulos_nuevo(request):
    if request.method == "POST":
        with transaction.atomic():

            max_serv = CotizacionServicio.objects.aggregate(Max('n_seguimiento'))['n_seguimiento__max'] or 0
            

            max_art = CotizacionArticulo.objects.aggregate(Max('n_seguimiento'))['n_seguimiento__max'] or 0
            


            nuevo_n = max(max_serv, max_art) + 1

            cliente_id = request.POST.get('cliente')
            cliente_obj = get_object_or_404(Cliente, id=cliente_id)
            

            nueva_cotiz = CotizacionArticulo.objects.create(
                n_seguimiento=nuevo_n,
                cliente=cliente_obj,

            )
            
            messages.success(request, f"Cotización #{nueva_cotiz.get_numero_formateado()} creada con éxito")
            return redirect('lista_cotizaciones_articulos')


    articulos = Articulo.objects.all().order_by('descripcion')
    clientes = Cliente.objects.all().order_by('razon_social')

    return render(request, 'usuarios/cotizar_articulo.html', {
        'articulos': articulos,
        'clientes': clientes
    })

@login_required
def editar_cotizacion_articulo(request, pk):
    cotizacion = get_object_or_404(CotizacionArticulo, n_presupuesto=pk)

    detalles_existentes = []
    for d in cotizacion.detalles.all():
        detalles_existentes.append({
            'id': d.articulo.id,
            'codigo': d.articulo.codigo,
            'descripcion': d.articulo.descripcion,
            'cantidad': float(d.cantidad),
            'precio': float(d.precio_unitario),
            'subtotal': float(d.cantidad * d.precio_unitario)
        })

    context = {
        'cotizacion': cotizacion,
        'clientes': Cliente.objects.all(),
        'articulos': Articulo.objects.all(),
        'detalles_json': json.dumps(detalles_existentes), # Pasamos los datos listos para JS
        'es_edicion': True
    }
    return render(request, 'usuarios/cotizar_articulo.html', context)

@login_required
def lista_cotizaciones_articulos(request):

    cotizaciones = CotizacionArticulo.objects.all().order_by('-fecha')


    n_presupuesto = request.GET.get('n_presupuesto')
    if n_presupuesto and n_presupuesto.isdigit():
        cotizaciones = cotizaciones.filter(n_presupuesto=n_presupuesto)


    cliente_query = request.GET.get('cliente')
    if cliente_query:
        cotizaciones = cotizaciones.filter(cliente__razon_social__icontains=cliente_query)


    paginator = Paginator(cotizaciones, 5)  
    page_number = request.GET.get('page')
    cotizaciones = paginator.get_page(page_number)

    return render(request, 'usuarios/lista_cotizaciones_articulos.html', {
        'cotizaciones': cotizaciones,
        'n_presupuesto': n_presupuesto,
        'cliente': cliente_query
    })

@login_required
@require_POST
def guardar_cotizacion_articulo(request):
    try:
        data = json.loads(request.body)

        cliente_id = data.get('cliente_id')
        items = data.get('items')
        total_final = data.get('total_final')

        cotizacion_id = data.get('cotizacion_id') 


        if not items:
            return JsonResponse({
                'status': 'error',
                'message': 'No hay artículos en la lista'
            }, status=400)


        with transaction.atomic():
            cliente = Cliente.objects.get(id=cliente_id)

            if cotizacion_id and str(cotizacion_id).strip() != "":


                cotizacion = CotizacionArticulo.objects.get(n_presupuesto=cotizacion_id)
                
                cotizacion.cliente = cliente
                cotizacion.total_final = Decimal(str(total_final))
                cotizacion.usuario = request.user
                cotizacion.save()
                

                cotizacion.detalles.all().delete()
                tipo_accion_txt = "Editó"
            else:


                cotizacion = CotizacionArticulo.objects.create(
                    cliente=cliente,
                    total_final=Decimal(str(total_final)),
                    usuario=request.user
                )
                tipo_accion_txt = "Generó"


            n_formateado = cotizacion.get_numero_formateado()


            total_f = f"${int(total_final):,}".replace(",", ".")
            detalles_historial = [
                f"Número de Seguimiento: {n_formateado}",
                f"Cliente: {cliente.razon_social}",
                f"Total Cotizado: {total_f}",
                "\nARTÍCULOS COTIZADOS:"
            ]


            for item in items:
                articulo = Articulo.objects.get(id=item['id'])
                precio = Decimal(str(item['precio_unitario']))
                cantidad = int(item['cantidad'])

                DetalleCotizacionArticulo.objects.create(
                    cotizacion=cotizacion,
                    articulo=articulo,
                    cantidad=cantidad,
                    precio_unitario=precio
                )
                
                precio_f = f"${int(precio):,}".replace(",", ".")
                detalles_historial.append(f"• {articulo.descripcion} | Cant: {cantidad} | Unit: {precio_f}")


            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"VENTAS: {tipo_accion_txt} Cotización Artículos #{n_formateado}",
                detalles="\n".join(detalles_historial)
            )


        messages.success(request, f"¡Cotización #{n_formateado} guardada con éxito!")


        return JsonResponse({
            'status': 'success',
            'n_presupuesto': n_formateado
        })

    except Cliente.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Cliente no encontrado'}, status=404)
    except Articulo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Uno de los artículos no existe'}, status=404)
    except Exception as e:
        print("Error al guardar cotización:", e)
        return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=400)

@login_required
def lista_cotizaciones_servicios(request):


    cotizaciones_query = CotizacionServicio.objects.select_related('cliente')\
        .prefetch_related('detalles__servicio')\
        .order_by('-fecha')


    id_cotizacion = request.GET.get('id_cotizacion')
    if id_cotizacion and id_cotizacion.isdigit():
        cotizaciones_query = cotizaciones_query.filter(n_seguimiento=id_cotizacion)


    cliente_query = request.GET.get('cliente')
    if cliente_query:
        cotizaciones_query = cotizaciones_query.filter(cliente__razon_social__icontains=cliente_query)


    paginator = Paginator(cotizaciones_query, 5)
    page_number = request.GET.get('page')
    cotizaciones_paginadas = paginator.get_page(page_number)

    return render(request, 'usuarios/lista_cotizaciones_servicios.html', {
        'cotizaciones': cotizaciones_paginadas
    })

@login_required
def editar_cotizacion_servicio(request, pk):
    cotizacion = get_object_or_404(CotizacionServicio, id=pk)
    
    detalles_lista = []
    for detalle in cotizacion.detalles.all():
        detalles_lista.append({
            'id': detalle.servicio.id,
            'codigo': detalle.servicio.codigo, 
            'nombre': detalle.servicio.descripcion,
            'cantidad': float(detalle.cantidad_m2),
            'precio': float(detalle.valor_unitario_m2),
            'subtotal': float(detalle.valor_unitario_m2 * detalle.cantidad_m2)
        })

    context = {
        'cotizacion': cotizacion,
        'clientes': Cliente.objects.all(),
        'servicios': Servicio.objects.all(),
        'detalles_json': json.dumps(detalles_lista),
        'editando': True
    }
    return render(request, 'usuarios/cotizar_servicio.html', context)

@login_required
def generar_pdf_cotizacion_servicio(request, pk):
    cotizacion = get_object_or_404(CotizacionServicio, pk=pk)
    cliente = cotizacion.cliente

    detalles = cotizacion.detalles.all() 
    
    codigo_servicio = f"COT_SERV_{str(cotizacion.n_seguimiento).zfill(5)}"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{codigo_servicio}.pdf"'

    p = canvas.Canvas(response, pagesize=LETTER)
    p.setTitle(codigo_servicio)
    width, height = LETTER


    logo_path = finders.find('images/logo.png')
    if logo_path:
        logo = ImageReader(logo_path)
        p.drawImage(logo, 30, height-95, width=175, height=100, preserveAspectRatio=True, mask='auto')

    x_empresa = width - 300
    y_empresa = height - 40
    p.setFont("Helvetica-Bold", 11)
    p.drawString(x_empresa, y_empresa, "USBTECH SPA")
    p.setFont("Helvetica", 9)
    p.drawString(x_empresa, y_empresa-15, "Camino a Montahue #55, San Pedro de La Paz.")
    p.drawString(x_empresa, y_empresa-30, "contacto@usbtech.cl | +56 9 9653 3834")
    p.drawString(x_empresa, y_empresa-45, "Rut: 77.859.775-6")
    p.drawString(x_empresa, y_empresa-60, "Giro: OTRAS ACTIVIDADES ESPECIALIZADAS DE DISEÑO N.C.P")
    p.drawString(x_empresa, y_empresa-75, "www.usbtech.cl")


    p.line(40, height-135, width-40, height-135)
    y_info = height-160

    # --- CONFIGURACIÓN DE ESTILOS PARA TEXTO DINÁMICO ---
    styles = getSampleStyleSheet()
    style_rs = ParagraphStyle(
        'RazonSocialStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,  # Interlineado
    )

    # Bloque Izquierdo: Datos del Cliente
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_info, "Cliente:")
    
    # Razón Social con salto de línea automático
    # El ancho de 300 evita que choque con el bloque de la derecha
    razon_social_html = f"Razón Social: {cliente.razon_social.upper()}"
    p_rs = Paragraph(razon_social_html, style_rs)
    w_rs, h_rs = p_rs.wrap(300, height) 
    p_rs.drawOn(p, 40, y_info - 15 - (h_rs - 9))

    # Calculamos la posición Y para los siguientes campos basados en el alto de la Razón Social
    y_campos_debajo = y_info - 15 - h_rs - 5 

    p.setFont("Helvetica", 9)
    p.drawString(40, y_campos_debajo, f"RUT: {cliente.rut}")
    p.drawString(40, y_campos_debajo - 15, f"Dirección: {cliente.direccion}")
    p.drawString(40, y_campos_debajo - 30, f"Correo: {cliente.correo}")
    p.drawString(40, y_campos_debajo - 45, f"Teléfono: {cliente.telefono}")

    # Bloque Derecho: Información de la Cotización (Posición fija)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-230, y_info, f"Presupuesto: {str(cotizacion.n_seguimiento).zfill(5)}") 
    p.setFont("Helvetica", 9)
    p.drawString(width-230, y_info-15, f"Fecha: {cotizacion.fecha.strftime('%d-%m-%Y')}")
    
    condiciones = cliente.get_condiciones_pago_display() if hasattr(cliente, 'get_condiciones_pago_display') else "N/A"
    p.drawString(width-230, y_info-30, f"Cond. Pago: {condiciones}")

    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-230, y_info-45, "Vendedor:")
    
    p.setFont("Helvetica", 9)
    codigo_v = "N/A"
    if cotizacion.usuario and hasattr(cotizacion.usuario, 'perfil'):
        codigo_v = cotizacion.usuario.perfil.codigo_vendedor or "Sin código"
    
    p.drawString(width-170, y_info-45, str(codigo_v))
    
    # El separador se ajusta según qué tan abajo llegaron los datos del cliente
    # Comparamos si el bloque izquierdo bajó más que el derecho para evitar traslapes
    y_final_bloque_izq = y_campos_debajo - 60
    y_final_bloque_der = y_info - 90
    y_separador = min(y_final_bloque_izq, y_final_bloque_der)

    p.line(40, y_separador, width-40, y_separador)

    y = y_separador - 25
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Descripción del Servicio")
    p.drawRightString(360, y, "Cant")
    p.drawRightString(470, y, "Valor")
    p.drawRightString(560, y, "Subtotal")
    p.line(40, y-5, width-40, y-5)

    y -= 20
    p.setFont("Helvetica", 9)
    
    total_neto = Decimal("0")

    for item in detalles:


        descripcion = item.servicio.descripcion[:60]
        cantidad = item.cantidad_m2
        precio_m2 = item.valor_unitario_m2
        subtotal = cantidad * precio_m2
        total_neto += subtotal

        p.drawString(40, y, descripcion)
        p.drawRightString(360, y, f"{cantidad:,.0f}")
        p.drawRightString(470, y, f"$ {precio_m2:,.2f}")
        p.drawRightString(560, y, f"$ {subtotal:,.2f}")
        
        y -= 15 




    y_final = y - 40 


    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_final, "DATOS BANCARIOS")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_final-15, "USBTECH SPA | Rut: 77.859.775-6")
    p.drawString(40, y_final-30, "Banco Santander | Cuenta Corriente: 98308091")
    p.drawString(40, y_final-45, "contacto@usbtech.cl")


    iva = total_neto * Decimal("0.19")
    total = total_neto + iva

    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, y_final, "Subtotal Neto")
    p.drawRightString(560, y_final, f"$ {total_neto:,.2f}")
    
    p.setFont("Helvetica", 9)
    p.drawString(400, y_final-15, "IVA (19%)")
    p.drawRightString(560, y_final-15, f"$ {iva:,.2f}")
    
    p.line(390, y_final-25, width-40, y_final-25)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(400, y_final-40, "TOTAL")
    p.drawRightString(560, y_final-40, f"$ {total:,.2f}")

    p.showPage()
    p.save()
    return response

@login_required
@usuario_tipo_requerido('admin', 'administracion', 'taller')
def crear_material_ajax(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        categoria = request.POST.get('categoria')
        variedad = request.POST.get('variedad')
        

        nuevo_material = MaterialStock.objects.create(
            nombre=nombre,
            categoria=categoria,
            variedad=variedad,
            nivel_actual=100
        )


        AccionHistorial.objects.create(
            usuario=request.user,
            accion=f"STOCK: Creó nuevo material - {nombre}",
            detalles=(
                f"Categoría: {categoria}\n"
                f"Variedad: {variedad}\n"
                f"Nivel Inicial: 100%"
            )
        )

        messages.success(request, "Material agregado al 100%")
        return redirect('stock_interno')

@login_required
def eliminar_material(request, pk): 
    material = get_object_or_404(MaterialStock, pk=pk) 
    

    nombre_material = material.nombre
    info_detalle = (
        f"Material: {material.nombre}\n"
        f"Categoría: {material.categoria}\n"
        f"Nivel al momento de eliminar: {material.nivel_actual}%"
    )
    

    AccionHistorial.objects.create(
        usuario=request.user,
        accion=f"STOCK: Eliminó material - {nombre_material}",
        detalles=info_detalle
    )
    

    material.delete()
    
    messages.success(request, f"El material '{nombre_material}' ha sido eliminado.")
    return redirect('stock_interno')

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def lista_facturas(request):

    if request.method == "POST":
        factura_id = request.POST.get('factura_id')
        raw_ids = request.POST.getlist('origen_ids')
        ids_seleccionados = [oid for oid in raw_ids if oid.strip()]
        tipo_origen = request.POST.get('tipo') 


        if ids_seleccionados and not tipo_origen:
            primer_id = ids_seleccionados[0]

            if CotizacionServicio.objects.filter(id=primer_id).exists():
                tipo_origen = 'servicio'

            elif CotizacionArticulo.objects.filter(n_presupuesto=primer_id).exists():
                tipo_origen = 'articulo'
        

        origen_id_str = ",".join(ids_seleccionados) if ids_seleccionados else None

        if factura_id:

            factura = get_object_or_404(Factura, id=factura_id)
            
            n_ant = factura.n_factura
            total_ant = f"${int(factura.total_facturado):,}".replace(",", ".")
            cliente_ant = factura.cliente.razon_social
            estado_ant = factura.get_estado_pago_display() 

            form = FacturaForm(request.POST, request.FILES, instance=factura)
            
            if form.is_valid():
                with transaction.atomic():
                    factura_obj = form.save(commit=False)
                    

                    factura_obj.origen_id = origen_id_str
                    factura_obj.tipo = tipo_origen
                    
                    if ids_seleccionados:

                        primer_id = ids_seleccionados[0]
                        if tipo_origen == 'servicio':
                            cotizacion = CotizacionServicio.objects.filter(id=primer_id).first()
                            if cotizacion:
                                factura_obj.cliente = cotizacion.cliente
                                proceso = Proceso.objects.filter(cliente=cotizacion.cliente).order_by('-creado').first()
                                factura_obj.proceso_asociado = proceso
                        elif tipo_origen == 'articulo':
                            cotizacion_art = CotizacionArticulo.objects.filter(n_presupuesto=primer_id).first()
                            if cotizacion_art:
                                factura_obj.cliente = cotizacion_art.cliente
                                factura_obj.proceso_asociado = None
                    else:
                        factura_obj.origen_id = None
                        factura_obj.tipo = None

                    factura_obj.save()
                    

                    if factura_obj.estado_pago == 'pagado':
                        Venta.objects.update_or_create(
                            factura=factura_obj,
                            defaults={
                                'n_factura': factura_obj.n_factura,
                                'cliente': factura_obj.cliente,
                                'monto_neto': int(factura_obj.total_facturado / Decimal('1.19')),
                                'monto_total': factura_obj.total_facturado,
                            }
                        )
                    else:
                        Venta.objects.filter(factura=factura_obj).delete()
                    

                    total_nuevo = f"${int(factura_obj.total_facturado):,}".replace(",", ".")
                    estado_nuevo = factura_obj.get_estado_pago_display()

                    AccionHistorial.objects.create(
                        usuario=request.user,
                        accion=f"FINANZAS: Editó Factura N°{factura_obj.n_factura}",
                        detalles=(
                            f"DETALLE DE MODIFICACIÓN:\n"
                            f"• Cliente: {cliente_ant} -> {factura_obj.cliente.razon_social}\n"
                            f"• N° Factura: {n_ant} -> {factura_obj.n_factura}\n"
                            f"• Total: {total_ant} -> {total_nuevo}\n"
                            f"• ESTADO DE PAGO: {estado_ant} -> {estado_nuevo}"
                        )
                    )
                    messages.success(request, "Factura actualizada correctamente")
                return redirect('lista_facturas')
        else:

            form = FacturaForm(request.POST, request.FILES)
            if form.is_valid():
                n_factura_nuevo = form.cleaned_data.get('n_factura')
                if Factura.objects.filter(n_factura=n_factura_nuevo).exists():
                    messages.error(request, f"¡Error! La factura N°{n_factura_nuevo} ya está registrada.")
                    return redirect('lista_facturas')

                with transaction.atomic():
                    factura_obj = form.save(commit=False)
                    factura_obj.origen_id = origen_id_str
                    factura_obj.tipo = tipo_origen
                    
                    if ids_seleccionados:
                        primer_id = ids_seleccionados[0]
                        if tipo_origen == 'servicio':
                            cotizacion = CotizacionServicio.objects.filter(id=primer_id).first()
                            if cotizacion:
                                factura_obj.cliente = cotizacion.cliente
                                proceso = Proceso.objects.filter(cliente=cotizacion.cliente).order_by('-creado').first()
                                factura_obj.proceso_asociado = proceso
                        elif tipo_origen == 'articulo':
                            cotizacion_art = CotizacionArticulo.objects.filter(n_presupuesto=primer_id).first()
                            if cotizacion_art:
                                factura_obj.cliente = cotizacion_art.cliente
                                factura_obj.proceso_asociado = None

                    factura_obj.save()

                    if factura_obj.estado_pago == 'pagado':
                        Venta.objects.update_or_create(
                            factura=factura_obj,
                            defaults={
                                'n_factura': factura_obj.n_factura,
                                'cliente': factura_obj.cliente,
                                'monto_neto': int(factura_obj.total_facturado / Decimal('1.19')),
                                'monto_total': factura_obj.total_facturado
                            }
                        )

                    total_f = f"${int(factura_obj.total_facturado):,}".replace(",", ".")

                    AccionHistorial.objects.create(
                        usuario=request.user,
                        accion=f"FINANZAS: Registró Factura N°{factura_obj.n_factura}",
                        detalles=(
                            f"Cliente: {factura_obj.cliente.razon_social}\n"
                            f"Total Facturado: {total_f}\n"
                            f"Estado: {factura_obj.get_estado_pago_display()}"
                        )
                    )
                    messages.success(request, "Factura creada correctamente")
                return redirect('lista_facturas')

    else:
        form = FacturaForm()


    facturas_query = Factura.objects.select_related('cliente', 'proceso_asociado').all().order_by('-fecha_creacion')

    n_factura = request.GET.get('n_factura', '')
    fecha = request.GET.get('fecha', '')
    rut = request.GET.get('rut', '')
    total = request.GET.get('total', '')

    if n_factura:
        facturas_query = facturas_query.filter(n_factura__icontains=n_factura)
    if fecha:
        facturas_query = facturas_query.filter(fecha_facturacion=fecha)
    if rut:
        facturas_query = facturas_query.filter(cliente__rut__icontains=rut)
    if total:
        facturas_query = facturas_query.filter(total_facturado=total)

    paginator = Paginator(facturas_query, 5)
    page_number = request.GET.get('page')
    facturas_paginadas = paginator.get_page(page_number)

    context = {
        'facturas': facturas_paginadas,
        'form': form,
        'clientes': Cliente.objects.all(),
        'cotizaciones_servicios': CotizacionServicio.objects.all().order_by('-n_seguimiento'),
        'cotizaciones_articulos': CotizacionArticulo.objects.all().order_by('-n_seguimiento'),
        'n_factura': n_factura,
        'fecha': fecha,
        'rut': rut,
        'total': total,
    }

    return render(request, 'usuarios/facturaciones.html', context)

@login_required
@usuario_tipo_requerido('admin','administracion')
def lista_ventas(request):

    ventas = Venta.objects.all().order_by('-fecha_registro')

    busqueda_factura = request.GET.get('factura')
    busqueda_rut = request.GET.get('rut')

    if busqueda_factura:
        ventas = ventas.filter(n_factura__icontains=busqueda_factura)

    if busqueda_rut:
        ventas = ventas.filter(cliente__rut__icontains=busqueda_rut)

    paginator = Paginator(ventas, 5)
    page_number = request.GET.get('page')
    ventas = paginator.get_page(page_number)

    return render(request, 'usuarios/venta.html', {
        'ventas': ventas,
        'busqueda_factura': busqueda_factura,
        'busqueda_rut': busqueda_rut,
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def lista_ordenes_compra(request):
    if request.method == 'POST':
        orden_id = request.POST.get('orden_id')
        n_orden = request.POST.get('n_orden')
        proveedor_id = request.POST.get('proveedor')
        archivo = request.FILES.get('archivo_pdf')

        articulo_ids = request.POST.getlist('articulo_ids[]')
        cantidades = request.POST.getlist('cantidades[]')
        precios = request.POST.getlist('precios[]')

        # --- 1. FUNCIÓN DE LIMPIEZA ÚNICA Y MEJORADA ---
        def limpiar_monto(valor):
            if not valor: return Decimal('0.00')
            v = str(valor).replace('\xa0', '').replace('$', '').strip()
            
            # Si tiene puntos y comas (ej: 3.094,22), quitamos punto y cambiamos coma
            if '.' in v and ',' in v:
                v = v.replace('.', '').replace(',', '.')
            # Si solo tiene coma (ej: 3094,22), cambiamos a punto
            elif ',' in v:
                v = v.replace(',', '.')
            # Si solo tiene un punto, pero es de miles (ej: 3.094), lo quitamos
            # Solo si hay 3 dígitos después del punto
            elif '.' in v and len(v.split('.')[-1]) == 3:
                v = v.replace('.', '')
                
            try:
                return Decimal(v)
            except:
                return Decimal('0.00')

        # --- 2. CÁLCULO DEL TOTAL ---
        total_calculado = Decimal('0.00')
        for c, p in zip(cantidades, precios):
            cant = limpiar_monto(c)
            prec = limpiar_monto(p)
            total_calculado += (cant * prec)

        total_nuevo_fmt = f"${total_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if orden_id:
            orden = get_object_or_404(OrdenCompra, id=orden_id)
            prov_ant = orden.proveedor.razon_social
            total_ant = f"${orden.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            orden.n_orden = n_orden
            orden.proveedor_id = proveedor_id
            orden.total = total_calculado
            if archivo:
                orden.archivo_pdf = archivo
            orden.save()

            orden.detalles.all().delete()
            for i in range(len(articulo_ids)):
                DetalleOrdenCompra.objects.create(
                    orden=orden,
                    articulo_id=articulo_ids[i],
                    cantidad=limpiar_monto(cantidades[i]),
                    precio_unitario=limpiar_monto(precios[i]) # Usar la misma función
                )

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"COMPRAS: Editó Orden de Compra N°{n_orden}",
                detalles=(
                    f"• Proveedor: {prov_ant} -> {orden.proveedor.razon_social}\n"
                    f"• Total: {total_ant} -> {total_nuevo_fmt}\n"
                    f"• Ítems: {len(articulo_ids)}"
                )
            )
            messages.success(request, f"Orden N°{n_orden} actualizada correctamente.")

        else:
            # --- 3. BLOQUE DE CREACIÓN (CORREGIDO) ---
            nueva_orden = OrdenCompra.objects.create(
                n_orden=n_orden,
                proveedor_id=proveedor_id,
                total=total_calculado,
                archivo_pdf=archivo
            )
            
            for i in range(len(articulo_ids)):
                # Aquí tenías "limpiar_numero", lo cambiamos a "limpiar_monto"
                DetalleOrdenCompra.objects.create(
                    orden=nueva_orden,
                    articulo_id=articulo_ids[i],
                    cantidad=limpiar_monto(cantidades[i]),
                    precio_unitario=limpiar_monto(precios[i])
                )

            AccionHistorial.objects.create(
                usuario=request.user,
                accion=f"COMPRAS: Creó Orden de Compra N°{n_orden}",
                detalles=(
                    f"Proveedor: {nueva_orden.proveedor.razon_social}\n"
                    f"Total: {total_nuevo_fmt}\n"
                    f"Ítems: {len(articulo_ids)}"
                )
            )
            messages.success(request, f"Orden N°{n_orden} creada exitosamente.")

        return redirect('lista_ordenes_compra')

    # ... El resto del código (ordenes, paginator, context) se mantiene igual ...


    ordenes = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles').all().order_by('-fecha_ingreso')
    
    rut = request.GET.get('rut', '')
    n_orden_filtro = request.GET.get('n_orden', '')
    fecha = request.GET.get('fecha', '')

    if rut:
        ordenes = ordenes.filter(proveedor__rut__icontains=rut)
    if n_orden_filtro:
        ordenes = ordenes.filter(n_orden__icontains=n_orden_filtro)
    if fecha:
        ordenes = ordenes.filter(fecha_ingreso=fecha)

    paginator = Paginator(ordenes, 5)
    page_number = request.GET.get('page')
    ordenes_paginadas = paginator.get_page(page_number)

    context = {
        'ordenes': ordenes_paginadas,
        'proveedores': Proveedor.objects.all(),
        'articulos': Articulo.objects.all(),
        'rut': rut,
        'n_orden': n_orden_filtro,
        'fecha': fecha
    }
    return render(request, 'usuarios/ordenes_compra.html', context)

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def crear_orden_compra(request):

    proveedores = Proveedor.objects.all().order_by('razon_social')
    articulos = Articulo.objects.all().order_by('descripcion')
    
    return render(request, 'usuarios/crear_orden_compra.html', {
        'proveedores': proveedores,
        'articulos': articulos
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def guardar_orden_compra(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            proveedor_id = data.get('proveedor_id')
            items = data.get('items')
            total_neto = data.get('total', 0)
            
            if not proveedor_id or not items:
                return JsonResponse({'status': 'error', 'message': 'Datos incompletos.'})

            proveedor = get_object_or_404(Proveedor, id=proveedor_id)

            with transaction.atomic():
                # EL CAMBIO CLAVE:
                # Forzamos a la DB a tratar n_orden como entero para encontrar el MAX real
                res_max = OrdenCompra.objects.annotate(
                    n_int=Cast('n_orden', IntegerField())
                ).aggregate(Max('n_int'))['n_int__max']

                nuevo_n = (res_max + 1) if res_max is not None else 1

                # Creamos la orden convirtiendo el número a string (porque el modelo es CharField)
                nueva_orden = OrdenCompra.objects.create(
                    n_orden=str(nuevo_n), 
                    proveedor=proveedor,
                    total=Decimal(str(total_neto))
                )

                # 3. Formatear para el historial (Aquí estaba el error de concatenación)
                t_float = float(total_neto)
                # Formateo manual para moneda chilena
                total_formateado = f"${t_float:,.0f}".replace(",", ".")
                
                detalles_historial = [
                    f"Proveedor: {proveedor.razon_social}",
                    f"Total Neto: {total_formateado}",
                    "\nARTÍCULOS SOLICITADOS:"
                ]

                for item in items:
                    articulo = get_object_or_404(Articulo, id=item['id'])
                    # Aseguramos que cantidad y precio sean números antes de operar
                    cantidad = int(float(item['cantidad']))
                    precio = float(item['precio']) 
                    
                    DetalleOrdenCompra.objects.create(
                        orden=nueva_orden,
                        articulo=articulo,
                        cantidad=cantidad,
                        precio_unitario=Decimal(str(precio))
                    )

                    p_fmt = f"${precio:,.0f}".replace(",", ".")
                    detalles_historial.append(f"• {articulo.descripcion} | Cant: {cantidad} | Unit: {p_fmt}")

                # 4. Guardar Historial (Usamos f-string para evitar el error de str + int)
                AccionHistorial.objects.create(
                    usuario=request.user,
                    # El uso de f"{nuevo_n}" convierte el número a texto automáticamente
                    accion=f"COMPRAS: Generó Orden de Compra N°{nuevo_n}", 
                    detalles="\n".join(detalles_historial)
                )

            return JsonResponse({
                'status': 'success', 
                'n_orden': nuevo_n,
                'message': f"Orden #{nuevo_n} guardada exitosamente"
            })

        except Exception as e:
            # Esto te dirá exactamente en qué parte del Python falló si vuelve a pasar
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'})

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def generar_pdf_orden_compra(request, pk):

    orden = get_object_or_404(OrdenCompra, pk=pk)
    detalles = orden.detalles.all()
    proveedor = orden.proveedor


    response = HttpResponse(content_type='application/pdf')
    codigo_formateado = f"OC_{str(orden.n_orden).zfill(5)}"
    response['Content-Disposition'] = f'inline; filename="{codigo_formateado}.pdf"'

    p = canvas.Canvas(response, pagesize=LETTER)
    p.setTitle(codigo_formateado)
    
    width, height = LETTER




    logo_path = finders.find('images/logo.png')
    if logo_path:
        logo = ImageReader(logo_path)
        p.drawImage(logo, 30, height-95, width=175, height=100, preserveAspectRatio=True, mask='auto')




    x_empresa = width - 300
    y_empresa = height - 40
    p.setFont("Helvetica-Bold", 11)
    p.drawString(x_empresa, y_empresa, "USBTECH SPA")
    p.setFont("Helvetica", 9)
    p.drawString(x_empresa, y_empresa-15, "Camino a Montahue #55, San Pedro de La Paz.")
    p.drawString(x_empresa, y_empresa-30, "contacto@usbtech.cl | +56 9 9653 3834")
    p.drawString(x_empresa, y_empresa-45, "Rut: 77.859.775-6")
    p.drawString(x_empresa, y_empresa-60, "Giro: OTRAS ACTIVIDADES ESPECIALIZADAS DE DISEÑO N.C.P")
    p.drawString(x_empresa, y_empresa-75, "www.usbtech.cl")

    p.line(40, height-135, width-40, height-135)




    y_info = height-160
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_info, "PROVEEDOR:")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_info-15, f"Razón Social: {proveedor.razon_social.upper()}")
    p.drawString(40, y_info-30, f"RUT: {proveedor.rut}")
    p.drawString(40, y_info-45, f"Dirección: {proveedor.direccion}")
    p.drawString(40, y_info-60, f"Correo: {proveedor.correo}")
    p.drawString(40, y_info-75, f"Teléfono: {proveedor.telefono}")
    

    p.setFont("Helvetica-Bold", 10)
    p.drawString(width-230, y_info, f"ORDEN DE COMPRA: #{str(orden.n_orden).zfill(5)}")
    p.setFont("Helvetica", 9)
    p.drawString(width-230, y_info-15, f"Fecha Emisión: {orden.fecha_ingreso.strftime('%d-%m-%Y')}")
    
    p.setFont("Helvetica-Bold", 9)
    p.drawString(width-230, y_info-30, "Cond. Pago:")
    p.setFont("Helvetica", 9)
    condicion = proveedor.get_condiciones_pago_display() if hasattr(proveedor, 'get_condiciones_pago_display') else "N/A"
    p.drawString(width-170, y_info-30, condicion)
    

    y_separador = y_info - 90
    p.line(40, y_separador, width-40, y_separador)




    y = y_separador - 25
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Descripción del Articulo")
    p.drawString(330, y, "Cant.")
    p.drawString(420, y, "Costo Unit.")
    p.drawString(520, y, "Subtotal")
    p.line(40, y-5, width-40, y-5)




    y -= 25
    p.setFont("Helvetica", 9)
    neto = Decimal("0.00")

    for item in detalles:
        costo = item.precio_unitario
        subtotal = item.cantidad * costo
        neto += subtotal

        p.drawString(40, y, item.articulo.descripcion[:60])
        p.drawRightString(360, y, f"{item.cantidad:,.0f}")
        p.drawRightString(470, y, f"$ {costo:,.2f}")
        p.drawRightString(560, y, f"$ {subtotal:,.2f}")
        
        y -= 18
        

        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 9)




    if y < 150: 
        p.showPage()
        y = height - 50

    iva = neto * Decimal("0.19")
    total = neto + iva

    y_final = y - 40
    p.line(390, y_final+10, width-40, y_final+10)
    
    p.setFont("Helvetica", 9)
    p.drawString(400, y_final, "Neto:")
    p.drawRightString(560, y_final, f"$ {neto:,.2f}")
    
    p.drawString(400, y_final-15, "IVA (19%):")
    p.drawRightString(560, y_final-15, f"$ {iva:,.0f}")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(400, y_final-35, "TOTAL COMPRA:")
    p.drawRightString(560, y_final-35, f"$ {total:,.2f}")



    p.showPage()
    p.save()
    return response

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def lista_compras(request):
    if request.method == 'POST':
        compra_id = request.POST.get('compra_id')
        
        if compra_id:

            instancia = get_object_or_404(Compra, id=compra_id)
            

            prov_ant = instancia.proveedor.razon_social
            n_fact_ant = instancia.n_factura
            total_ant = f"${instancia.total_compra:,.2f}"

            estado_ant = instancia.get_estado_pago_display() if hasattr(instancia, 'get_estado_pago_display') else "N/A"
            
            form = CompraForm(request.POST, request.FILES, instance=instancia)
        else:

            form = CompraForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                compra = form.save()
                

                total_nuevo = f"${compra.total_compra:,.2f}"
                estado_nuevo = compra.get_estado_pago_display() if hasattr(compra, 'get_estado_pago_display') else "N/A"

                if compra_id:

                    AccionHistorial.objects.create(
                        usuario=request.user,
                        accion=f"COMPRAS: Editó respaldo de compra ID {compra.id}",
                        detalles=(
                            f"Cambios realizados en Factura {compra.n_factura}:\n"
                            f"• Proveedor: {prov_ant} -> {compra.proveedor.razon_social}\n"
                            f"• Total: {total_ant} -> {total_nuevo}\n"
                            f"• ESTADO DE PAGO: {estado_ant} -> {estado_nuevo}" # <--- Campo clave añadido
                        )
                    )
                    mensaje = "Compra actualizada correctamente."
                else:

                    AccionHistorial.objects.create(
                        usuario=request.user,
                        accion=f"COMPRAS: Registró nueva compra (Factura {compra.n_factura})",
                        detalles=(
                            f"Proveedor: {compra.proveedor.razon_social}\n"
                            f"Total Compra: {total_nuevo}\n"
                            f"Estado Inicial: {estado_nuevo}\n" 
                            f"Fecha Registro: {compra.fecha_registro}"
                        )
                    )
                    mensaje = "Respaldo de compra guardado correctamente."

            messages.success(request, mensaje)
            return redirect('lista_compras')
        else:
            messages.error(request, f"Error al procesar el formulario: {form.errors.as_text()}")
    

    
    else:
        form = CompraForm()


    compras_list = Compra.objects.select_related('proveedor').all().order_by('-fecha_registro')

    q_rut = request.GET.get('rut') 
    q_fecha = request.GET.get('fecha')
    n_factura = request.GET.get('n_factura')
    total = request.GET.get('total')

    if q_rut:
        compras_list = compras_list.filter(proveedor__rut__icontains=q_rut)
    if q_fecha:
        compras_list = compras_list.filter(fecha_registro=q_fecha)
    if n_factura:
        compras_list = compras_list.filter(n_factura__icontains=n_factura)
    if total:
        compras_list = compras_list.filter(total_compra=total)

    paginator = Paginator(compras_list, 5)
    page_number = request.GET.get('page')
    compras = paginator.get_page(page_number)

    proveedores = Proveedor.objects.all()
    
    return render(request, 'usuarios/compras.html', {
        'form': form,
        'compras': compras,
        'proveedores': proveedores,
        'rut': q_rut,
        'fecha': q_fecha,
        'n_factura': n_factura,
        'total': total
    })

@login_required
def dashboard_diseno(request):
    procesos = Proceso.objects.filter(
        estado='diseno', 
        responsable_diseno=request.user.username 
    ).prefetch_related('fotos_terreno').order_by('-creado')
    
    if request.method == 'POST':
        form = DisenoForm(request.POST)
        if form.is_valid():
            proceso = form.save(commit=False)
            proceso.usuario = request.user
            proceso.estado = 'diseno'
            proceso.responsable_diseno = request.user.username 
            


            mediciones = request.POST.get('mediciones_json')
            if mediciones:
                proceso.mediciones_json = mediciones

            
            proceso.save()
            
            AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"CREÓ orden de trabajo para {proceso.cliente.razon_social} (Auto-asignado a Diseño)"
            )
            return redirect('dashboard_diseno')
    else:
        form = DisenoForm()

    return render(request, 'usuarios/dashboard_diseno.html', {'form': form, 'procesos': procesos})

@login_required
def pasar_a_taller(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)

    cambios_finales = proceso.detectar_cambios()
    
    if not proceso.pasa_por_taller:
        proceso.estado = 'finalizado'
        destino = "ADMIN"
    else:
        proceso.estado = 'taller'
        destino = "TALLER"
    
    proceso.save()
    

    AccionHistorial.objects.create(
        usuario=request.user,
        accion=f"FLUJO: Envío a {destino} - {proceso.cliente.razon_social}",
        detalles=f"Cambios realizados:\n{cambios_finales}"
    )
    
    messages.success(request, f"Proyecto enviado a {destino}")
    return redirect('dashboard_diseno')

@login_required
def pasar_a_admin(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    cambios_finales = proceso.detectar_cambios()
    

    proceso.estado = 'finalizado'
    proceso.save()
    

    AccionHistorial.objects.create(
        usuario=request.user, 
        accion=f"FLUJO: Taller finaliza y envía a Admin - {proceso.cliente.razon_social}",
        detalles=f"Manufactura terminada.\n{cambios_finales}"
    )
    
    messages.success(request, f"Producción de {proceso.cliente.razon_social} terminada. Enviado a Admin.")
    return redirect('dashboard_taller')

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def cerrar_proceso(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    
    factura_id = request.GET.get('factura_id')
    n_factura_str = "Sin factura asociada"

    with transaction.atomic():
        proceso.estado = 'cerrado'
        
        if factura_id:
            try:
                from .models import Factura
                factura_obj = Factura.objects.get(id=factura_id)
                

                proceso.factura_asociada = factura_obj 
                


                factura_obj.proceso_asociado = proceso
                factura_obj.save()

                n_factura_str = f"Factura N°{factura_obj.n_factura}"
            except Exception as e:
                print(f"Error vinculando factura: {e}")
                pass

        proceso.save()
        

        AccionHistorial.objects.create(
            usuario=request.user, 
            accion=f"CIERRE: Archivó el proyecto de {proceso.cliente.razon_social}",
            detalles=(
                f"Estado final al archivar:\n{proceso.escanear_checks()}\n"
                f"Vinculación: {n_factura_str}"
            )
        )

    messages.success(request, f"El proceso de {proceso.cliente.razon_social} ha sido archivado y vinculado a {n_factura_str}.")
    return redirect('dashboard')


@login_required
def editar_proceso_diseno(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    
    if request.method == 'POST':

        try:
            mediciones_viejas = json.loads(proceso.mediciones_json or "[]")
        except:
            mediciones_viejas = []

        form = DisenoForm(request.POST, request.FILES, instance=proceso)
        archivos = request.FILES.getlist('archivos_nuevos')
        nuevas_mediciones_raw = request.POST.get('mediciones_json')

        if form.is_valid():
            
            aprobacion_final = form.cleaned_data.get('aprobacion_final')
            tiene_archivos_previos = proceso.archivos.exists()
            esta_subiendo_archivos = len(archivos) > 0

            if aprobacion_final and not (tiene_archivos_previos or esta_subiendo_archivos):
                messages.error(request, "No puedes marcar Aprobación Final sin subir al menos un archivo de respaldo.")
                return render(request, 'usuarios/editar_proceso_diseno.html', {'form': form, 'proceso': proceso})
            

            try:
                with transaction.atomic():
                    cambios_detectados = proceso.detectar_cambios()
                    proceso = form.save(commit=False)
                    

                    log_mediciones = []
                    nuevas_mediciones_lista = json.loads(nuevas_mediciones_raw or "[]")
                    


                    descripciones_nuevas = [m.get('descripcion') for m in nuevas_mediciones_lista]
                    for mv in mediciones_viejas:
                        if mv.get('descripcion') not in descripciones_nuevas:
                            log_mediciones.append(f" ELIMINADO: {mv.get('descripcion')} "f"({mv.get('ancho')}x{mv.get('largo')}) x{mv.get('cantidad')}")


                    descripciones_viejas = [m.get('descripcion') for m in mediciones_viejas]
                    for mn in nuevas_mediciones_lista:
                        if mn.get('descripcion') not in descripciones_viejas:
                            log_mediciones.append(f" NUEVO: {mn.get('descripcion')} ({mn.get('ancho')}x{mn.get('largo')}) x{mn.get('cantidad')}")
                        else:

                            for mn in nuevas_mediciones_lista:
                                if mn.get('descripcion') in descripciones_viejas:
                                    for mv in mediciones_viejas:
                                        if mv.get('descripcion') == mn.get('descripcion'):

                                            if (mv.get('ancho') != mn.get('ancho') or 
                                                mv.get('largo') != mn.get('largo') or 
                                                mv.get('cantidad') != mn.get('cantidad')):
                                                

                                                log_mediciones.append(
                                                    f" EDITADO: {mn.get('descripcion')} "
                                                    f"(Antes: {mv.get('ancho')}x{mv.get('largo')} x{mv.get('cantidad')} -> "
                                                    f"Ahora: {mn.get('ancho')}x{mn.get('largo')} x{mn.get('cantidad')})"
                                                )


                    proceso.mediciones_json = nuevas_mediciones_raw
                    proceso.save()


                    for f in archivos:
                        ArchivoProceso.objects.create(proceso=proceso, archivo=f)


                    seccion_medidas = "\n\n--- CAMBIOS EN DIMENSIONES ---" if log_mediciones else ""
                    detalle_medidas = "\n".join(log_mediciones)
                    resumen_archivos = f"\n• Archivos subidos: {len(archivos)}" if archivos else ""
                    
                    detalle_final = f"{cambios_detectados}{seccion_medidas}\n{detalle_medidas}{resumen_archivos}"

                    AccionHistorial.objects.create(
                        usuario=request.user,
                        accion=f"DISEÑO: Editó {proceso.cliente.razon_social}",
                        detalles=detalle_final
                    )

                    messages.success(request, "Proceso actualizado con éxito.")
                    return redirect('dashboard_diseno')

            except Exception as e:
                messages.error(request, f"Error en el proceso: {e}")
    
    else:
        form = DisenoForm(instance=proceso)
    
    return render(request, 'usuarios/editar_proceso_diseno.html', {'form': form, 'proceso': proceso})

@login_required
def finalizar_taller(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    

    proceso.estado = 'finalizado'
    proceso.save()
    


    AccionHistorial.objects.create(
        usuario=request.user, 

        accion=f"FLUJO: Taller envió a Administración - {proceso.cliente.razon_social}",

        detalles=f"Manufactura completada. El proceso ID {proceso.id} pasó a revisión final de Admin."
    )
    
    messages.success(request, f"Producción de {proceso.cliente.razon_social} terminada. Enviado a Admin.")
    return redirect('dashboard_taller')
    
def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

@login_required
@usuario_tipo_requerido('administracion')
def editar_proceso_admin(request, pk):
    proceso = Proceso.objects.get(pk=pk)
    clientes = Cliente.objects.all()

    if request.method == "POST":
        proceso.cliente_id = request.POST.get("cliente_id")
        proceso.fecha_entrega = request.POST.get("fecha_entrega") or None

        proceso.familia = request.POST.get('familia', proceso.familia)

        proceso.pasa_por_diseno = request.POST.get('pasa_por_diseno') == 'on'
        proceso.pasa_por_taller = request.POST.get('pasa_por_taller') == 'on'

        proceso.responsable_diseno = request.POST.get('responsable_diseno') if proceso.pasa_por_diseno else None
        proceso.responsable_taller = request.POST.get('responsable_taller') if proceso.pasa_por_taller else None
        
        proceso.mediciones_json = request.POST.get('mediciones_json', '[]')
        proceso.observaciones_terreno = request.POST.get('obs_terreno', '')
        proceso.mediciones_taller_json = request.POST.get('mediciones_taller_json', '[]')

        #taller insumos
        proceso.acrilico = request.POST.get('acrilico') == 'on'
        proceso.sintra = request.POST.get('sintra') == 'on'
        proceso.ojetillo = request.POST.get('ojetillo') == 'on'
        proceso.ad_prom = request.POST.get('ad_prom') == 'on'
        proceso.ad_vehicular = request.POST.get('ad_vehicular') == 'on'
        proceso.empavonado = request.POST.get('empavonado') == 'on'
        proceso.microperf = request.POST.get('microperf') == 'on'
        proceso.sellado = request.POST.get('sellado') == 'on'
        proceso.tela_pvc = request.POST.get('tela_pvc') == 'on'
        proceso.otros_materiales = request.POST.get('otros_materiales', '')
        
        #produccion de Taller
        proceso.impresion = request.POST.get('impresion') == 'on'
        proceso.corte = request.POST.get('corte') == 'on'

        #tallersito
        proceso.instrucciones_admin = request.POST.get('instrucciones_admin', '')
        proceso.terminaciones = request.POST.get('terminaciones_especificas', '')

        #diseñador
        proceso.reunion = request.POST.get('reunion') == 'on'
        proceso.pauta = request.POST.get('pauta') == 'on'
        nuevas_fotos = request.FILES.getlist('fotos_terreno')
        for f in nuevas_fotos:
            FotoTerreno.objects.create(proceso=proceso, imagen=f)

        # levantamiento terreno 
        levantamiento, created = LevantamientoTerreno.objects.get_or_create(proceso=proceso)
        
        # Medidas Básicas
        levantamiento.ancho = to_float(request.POST.get('medida_ancho'))
        levantamiento.alto = to_float(request.POST.get('medida_alto'))
        levantamiento.profundidad_letrero = to_float(request.POST.get('medida_profundidad'))
        levantamiento.ubicacion = request.POST.get('terreno_ubicacion') or 'exterior'
        levantamiento.altura_instalacion = to_float(request.POST.get('terreno_altura_m'))

        # Medios de Acceso
        levantamiento.acceso_escalera = request.POST.get('acc_escalera') == 'on'
        levantamiento.acceso_andamio = request.POST.get('acc_andamio') == 'on'
        levantamiento.acceso_grua = request.POST.get('acc_grua') == 'on'
        levantamiento.restricciones_acceso = request.POST.get('acc_restricciones', '')

        # Soportes
        levantamiento.soporte_muro = request.POST.get('sup_muro') == 'on'
        levantamiento.soporte_metal = request.POST.get('sup_metal') == 'on'
        levantamiento.soporte_vidrio = request.POST.get('sup_vidrio') == 'on'
        levantamiento.soporte_panel_compuesto = request.POST.get('sup_panel') == 'on'
        levantamiento.soporte_otro = request.POST.get('sup_otro', '')

        # Instalación Eléctrica
        levantamiento.punto_cercano = request.POST.get('elec_punto') == 'on'
        levantamiento.tablero_accesible = request.POST.get('elec_tablero') == 'on'
        levantamiento.voltaje = request.POST.get('elec_voltaje', '')

        # Materiales de Terreno
        levantamiento.mat_pvc = request.POST.get('mat_pvc') == 'on'
        levantamiento.mat_pvc_lum = request.POST.get('mat_pvc_lum') == 'on'
        levantamiento.mat_acrilico = request.POST.get('mat_acrilico') == 'on'
        levantamiento.mat_adh_nor = request.POST.get('mat_adh_nor') == 'on'
        levantamiento.mat_adh_trans = request.POST.get('mat_adh_trans') == 'on'

        # Terminaciones de Terreno
        levantamiento.term_ojetillos = request.POST.get('term_ojetillos') == 'on'
        levantamiento.term_bolsillo = request.POST.get('term_bolsillo') == 'on'
        levantamiento.term_tubo = request.POST.get('term_tubo') == 'on'
        levantamiento.term_bastidor = request.POST.get('term_bastidor') == 'on'
        levantamiento.term_laminado = request.POST.get('term_laminado') == 'on'
        levantamiento.term_troquel = request.POST.get('term_troquel') == 'on'

        # Riesgos y Tiempos
        levantamiento.riesgo_altura = request.POST.get('r_altura') == 'on'
        levantamiento.riesgo_transito = request.POST.get('r_transito') == 'on'
        levantamiento.riesgo_permiso = request.POST.get('r_permiso') == 'on'
        levantamiento.riesgo_energia = request.POST.get('r_energia') == 'on'
        levantamiento.tiempo_estimado_instalacion = request.POST.get('r_tiempo_estimado', '')

        # Guardado final del objeto levantamiento
        levantamiento.save()
        
        proceso.save()

        messages.success(request, "Proceso actualizado correctamente")
        return redirect("dashboard")

    context = {
        'proceso': proceso,
        'clientes': clientes,
        'familias_servicios': Proceso.FAMILIAS_SERVICIOS,
        'usuarios_diseno': User.objects.filter(perfil__tipo_usuario='diseno'),
        'usuarios_taller': User.objects.filter(perfil__tipo_usuario='taller'),
        'levantamiento': proceso.levantamiento,
    }

    return render(request, 'usuarios/editar_proceso_admin.html', context)

@login_required
def enviar_a_admin(request, pk):
    """ Taller envía el trabajo terminado a revisión de Admin """
    proceso = get_object_or_404(Proceso, pk=pk)
    proceso.estado = 'finalizado'
    proceso.save()
    

    foto_entrega = proceso.escanear_checks()
    
    AccionHistorial.objects.create(
        usuario=request.user, 
        accion=f"ENTREGA: Taller terminó manufactura - {proceso.cliente.razon_social}",
        detalles=f"Estado final de entrega:\n{foto_entrega}"
    )
    
    messages.success(request, f"Proyecto de {proceso.cliente.razon_social} enviado a Administración.")
    return redirect('dashboard_taller')

@login_required
def cerrar_proceso_final(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    

    if request.user.is_superuser or (hasattr(request.user, 'perfil') and request.user.perfil.tipo_usuario == 'administracion'):
        

        factura_id = request.GET.get('factura_id') 
        detalle_factura = "Sin factura asociada"

        if factura_id:
            try:
                from .models import Factura
                factura_obj = Factura.objects.get(id=factura_id)
                

                factura_obj.proceso_asociado = proceso
                factura_obj.save()
                
                proceso.factura_asociada = factura_obj
                detalle_factura = f"Vinculado a Factura N°{factura_obj.n_factura}"
            except Factura.DoesNotExist:
                messages.warning(request, "El proceso se cerró, pero la factura seleccionada no existe.")



        cambios_finales = proceso.detectar_cambios()
        
        proceso.estado = 'cerrado'
        proceso.save()
        

        AccionHistorial.objects.create(
            usuario=request.user, 
            accion=f"FLUJO: CIERRE DEFINITIVO - Cliente: {proceso.cliente.razon_social}",
            detalles=f"Proyecto finalizado y archivado. {detalle_factura}\n{cambios_finales}"
        )
        
        messages.success(request, f"¡Proyecto de {proceso.cliente.razon_social} finalizado con éxito! ({detalle_factura})")
    else:
        messages.error(request, "No tienes permisos para cerrar este proceso.")
        
    return redirect('dashboard')
    
def error_403(request, exception=None):
    return render(request, '403.html', status=403)

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def lista_acciones(request):

    if not (request.user.is_superuser or request.user.perfil.tipo_usuario == 'administracion'):
        return redirect('dashboard')
    

    q_user = request.GET.get('usuario', '')
    q_fecha = request.GET.get('fecha', '')
    
    acciones_list = AccionHistorial.objects.all().order_by('-fecha') 


    if q_user:
        acciones_list = acciones_list.filter(usuario__username__icontains=q_user)
    
    if q_fecha:
        acciones_list = acciones_list.filter(fecha__date=q_fecha)


    paginator = Paginator(acciones_list, 10)
    page_number = request.GET.get('page')
    acciones = paginator.get_page(page_number)

    context = {
        'acciones': acciones,
        'q_user': q_user,
        'q_fecha': q_fecha,
    }
    
    return render(request, 'usuarios/lista_acciones.html', context)

@login_required
@usuario_tipo_requerido('administracion', 'admin')
def crear_proceso_admin(request):
    if request.method == 'POST':
        proceso_id = request.POST.get('proceso_id')

        cliente_id = request.POST.get('cliente_id')
        familia = request.POST.get('familia', 'Letreros')
        fecha_entrega = request.POST.get('fecha_entrega') or None


        pasa_por_diseno = request.POST.get('pasa_por_diseno') == 'on'
        pasa_por_taller = request.POST.get('pasa_por_taller') == 'on'
        
        if not pasa_por_diseno and pasa_por_taller:
            estado_inicial = 'taller'
        elif not pasa_por_diseno and not pasa_por_taller:
            estado_inicial = 'finalizado'
        else:
            estado_inicial = 'diseno'
            
        responsable_diseno = request.POST.get('responsable_diseno') if pasa_por_diseno else None
        responsable_taller = request.POST.get('responsable_taller') if pasa_por_taller else None

        try:
            with transaction.atomic():

                if proceso_id:
                    nuevo_proceso = Proceso.objects.get(id=proceso_id)
                else:
                    nuevo_proceso = Proceso(usuario=request.user)

                nuevo_proceso.usuario = request.user
                nuevo_proceso.cliente_id = cliente_id
                nuevo_proceso.familia = familia
                nuevo_proceso.estado = estado_inicial
                nuevo_proceso.fecha_entrega = fecha_entrega
                nuevo_proceso.pasa_por_diseno = pasa_por_diseno
                nuevo_proceso.pasa_por_taller = pasa_por_taller
                nuevo_proceso.responsable_diseno = responsable_diseno
                nuevo_proceso.responsable_taller = responsable_taller
                nuevo_proceso.observaciones_terreno = request.POST.get('obs_terreno', '')
                nuevo_proceso.instrucciones_admin = request.POST.get('instrucciones_admin', '')
                nuevo_proceso.mediciones_json = request.POST.get('mediciones_json', '[]')
                nuevo_proceso.mediciones_taller_json = request.POST.get('mediciones_taller_json', '[]')

                nuevo_proceso.reunion = request.POST.get('reunion') == 'on'
                nuevo_proceso.pauta = request.POST.get('pauta') == 'on'
                nuevo_proceso.enviado_correccion = request.POST.get('enviado_correccion') == 'on'
                nuevo_proceso.correccion_1 = request.POST.get('correccion_1') == 'on'
                nuevo_proceso.correccion_2 = request.POST.get('correccion_2') == 'on'
                nuevo_proceso.correccion_3 = request.POST.get('correccion_3') == 'on'
                nuevo_proceso.aprobacion_final = request.POST.get('aprobacion_final') == 'on'

                nuevo_proceso.acrilico = request.POST.get('acrilico') == 'on'
                nuevo_proceso.sintra = request.POST.get('sintra') == 'on'
                nuevo_proceso.ojetillo = request.POST.get('ojetillo') == 'on'
                nuevo_proceso.ad_prom = request.POST.get('ad_prom') == 'on'
                nuevo_proceso.ad_vehicular = request.POST.get('ad_vehicular') == 'on'
                nuevo_proceso.empavonado = request.POST.get('empavonado') == 'on'
                nuevo_proceso.microperf = request.POST.get('microperf') == 'on'
                nuevo_proceso.sellado = request.POST.get('sellado') == 'on'
                nuevo_proceso.tela_pvc = request.POST.get('tela_pvc') == 'on'
                nuevo_proceso.otros_materiales = request.POST.get('otros_materiales', '')
                nuevo_proceso.impresion = request.POST.get('impresion') == 'on'
                nuevo_proceso.corte = request.POST.get('corte') == 'on'
                nuevo_proceso.terminaciones = request.POST.get('terminaciones_especificas', '')

                nuevo_proceso.save()


                levantamiento = LevantamientoTerreno.objects.get(proceso=nuevo_proceso)

                def to_float(val):
                    if not val: return 0.0
                    try: return float(str(val).replace(',', '.'))
                    except: return 0.0


                levantamiento.ancho = to_float(request.POST.get('medida_ancho'))
                levantamiento.alto = to_float(request.POST.get('medida_alto'))
                levantamiento.profundidad_letrero = to_float(request.POST.get('medida_profundidad'))
                levantamiento.ubicacion = request.POST.get('terreno_ubicacion') or 'exterior'
                levantamiento.altura_instalacion = to_float(request.POST.get('terreno_altura_m'))
                

                levantamiento.acceso_escalera = request.POST.get('acc_escalera') == 'on'
                levantamiento.acceso_andamio = request.POST.get('acc_andamio') == 'on'
                levantamiento.acceso_grua = request.POST.get('acc_grua') == 'on'
                levantamiento.restricciones_acceso = request.POST.get('acc_restricciones', '')
                
                levantamiento.soporte_muro = request.POST.get('sup_muro') == 'on'
                levantamiento.soporte_metal = request.POST.get('sup_metal') == 'on'
                levantamiento.soporte_vidrio = request.POST.get('sup_vidrio') == 'on'
                levantamiento.soporte_panel_compuesto = request.POST.get('sup_panel') == 'on'
                levantamiento.soporte_otro = request.POST.get('sup_otro', '')

                levantamiento.punto_cercano = request.POST.get('elec_punto') == 'on'
                levantamiento.tablero_accesible = request.POST.get('elec_tablero') == 'on'
                levantamiento.voltaje = request.POST.get('elec_voltaje', '')

                levantamiento.mat_pvc = request.POST.get('mat_pvc') == 'on'
                levantamiento.mat_pvc_lum = request.POST.get('mat_pvc_lum') == 'on'
                levantamiento.mat_acrilico = request.POST.get('mat_acrilico') == 'on'
                levantamiento.mat_adh_nor = request.POST.get('mat_adh_nor') == 'on'
                levantamiento.mat_adh_trans = request.POST.get('mat_adh_trans') == 'on'


                levantamiento.term_ojetillos = request.POST.get('term_ojetillos') == 'on'
                levantamiento.term_bolsillo = request.POST.get('term_bolsillo') == 'on'
                levantamiento.term_tubo = request.POST.get('term_tubo') == 'on'
                levantamiento.term_bastidor = request.POST.get('term_bastidor') == 'on'
                levantamiento.term_laminado = request.POST.get('term_laminado') == 'on'
                levantamiento.term_troquel = request.POST.get('term_troquel') == 'on'


                levantamiento.riesgo_altura = request.POST.get('r_altura') == 'on'
                levantamiento.riesgo_transito = request.POST.get('r_transito') == 'on'
                levantamiento.riesgo_permiso = request.POST.get('r_permiso') == 'on'
                levantamiento.riesgo_energia = request.POST.get('r_energia') == 'on'
                levantamiento.tiempo_estimado_instalacion = request.POST.get('r_tiempo_estimado', '')

                levantamiento.save()


                fotos = request.FILES.getlist('fotos_terreno')
                for f in fotos:
                    FotoTerreno.objects.create(proceso=nuevo_proceso, imagen=f)




                cambios = []
                cambios.append(f"NUEVA ORDEN CREADA: #{nuevo_proceso.id}")
                cambios.append(f"CLIENTE: {nuevo_proceso.cliente.razon_social}")
                cambios.append(f"ESTADO INICIAL: {nuevo_proceso.get_estado_display()}")


                pasos_diseno = []
                

                if nuevo_proceso.reunion: 
                    pasos_diseno.append("Reunión Agendada")
                
                if nuevo_proceso.pauta: 
                    pasos_diseno.append("Pauta Lista")
                
                if nuevo_proceso.enviado_correccion: 
                    pasos_diseno.append("Enviado a Corrección")
                

                if nuevo_proceso.correccion_1: 
                    pasos_diseno.append("Corrección 1 Realizada")
                
                if nuevo_proceso.correccion_2: 
                    pasos_diseno.append("Corrección 2 Realizada")
                
                if nuevo_proceso.correccion_3: 
                    pasos_diseno.append("Corrección 3 Realizada")
                
                if nuevo_proceso.aprobacion_final: 
                    pasos_diseno.append("Aprobación Final ")

                try:
                    if nuevo_proceso.mediciones_json:
                        mediciones = json.loads(nuevo_proceso.mediciones_json)
                        texto_mediciones = []
                        for m in mediciones:

                            desc = str(m.get('descripcion') or '').strip()
                            largo = str(m.get('largo') or '').strip()
                            ancho = str(m.get('ancho') or '').strip()
                            cant = str(m.get('cantidad') or '').strip()
                            
                            if desc:

                                texto_mediciones.append(f"{desc}: {largo}x{ancho} (Cant: {cant})")
                        
                        if texto_mediciones:
                            pasos_diseno.append(f"Mediciones: [{', '.join(texto_mediciones)}]")
                except Exception as e:
                    pasos_diseno.append(f"Mediciones: Error de formato ({str(e)})")
                
                cambios.append(f"\n--- AVANCE DE DISEÑO ---")
                cambios.append(f"Pasos: {', '.join(pasos_diseno) if pasos_diseno else 'Sin avances'}")


                mats_taller = []
                campos_taller = [
                    (nuevo_proceso.acrilico, "Acrílico"), (nuevo_proceso.sintra, "Sintra"),
                    (nuevo_proceso.ojetillo, "Ojetillo"), (nuevo_proceso.ad_prom, "Adh. Promocional"),
                    (nuevo_proceso.ad_vehicular, "Adh. Vehicular"), (nuevo_proceso.empavonado, "Empavonado"),
                    (nuevo_proceso.microperf, "Microperforado"), (nuevo_proceso.sellado, "Sellado"),
                    (nuevo_proceso.tela_pvc, "Tela PVC")
                ]
                for valor, nombre in campos_taller:
                    if valor: mats_taller.append(nombre)
                
                cambios.append(f"\n--- PRODUCCIÓN TALLER ---")
                cambios.append(f"Insumos: {', '.join(mats_taller) if mats_taller else 'Sin materiales'}")
                if nuevo_proceso.otros_materiales:
                    cambios.append(f"Otros materiales: {nuevo_proceso.otros_materiales}")
                
                prod_tipo = []
                if nuevo_proceso.impresion: prod_tipo.append("Impresión")
                if nuevo_proceso.corte: prod_tipo.append("Corte")
                cambios.append(f"Procesos: {', '.join(prod_tipo) if prod_tipo else 'No especificado'}")


            if levantamiento: 
                cambios.append(f"\n--- DETALLES DE TERRENO ---")
                cambios.append(f"Medidas: {levantamiento.ancho}x{levantamiento.alto}x{levantamiento.profundidad_letrero} cm")
                cambios.append(f"Ubicación: {levantamiento.ubicacion} (Altura: {levantamiento.altura_instalacion}m)")
                

                accs = []
                if levantamiento.acceso_escalera: accs.append("Escalera")
                if levantamiento.acceso_andamio: accs.append("Andamio")
                if levantamiento.acceso_grua: accs.append("Grúa")
                cambios.append(f"Medios de Acceso: {', '.join(accs) if accs else 'No especificados'}")
                if levantamiento.restricciones_acceso:
                    cambios.append(f"Restricciones de Acceso: {levantamiento.restricciones_acceso}")


                sops = []
                if levantamiento.soporte_muro: sops.append("Muro")
                if levantamiento.soporte_metal: sops.append("Estructura Metal")
                if levantamiento.soporte_vidrio: sops.append("Vidrio")
                if levantamiento.soporte_panel_compuesto: sops.append("Panel Compuesto")
                if levantamiento.soporte_otro: sops.append(f"Otro: {levantamiento.soporte_otro}")
                cambios.append(f"Soportes: {', '.join(sops) if sops else 'No definidos'}")


                elec_info = []
                if levantamiento.punto_cercano: elec_info.append("Punto de energía cercano")
                if levantamiento.tablero_accesible: elec_info.append("Tablero accesible")
                if levantamiento.voltaje: elec_info.append(f"Voltaje: {levantamiento.voltaje}")
                
                cambios.append(f"\n--- INSTALACIÓN ELÉCTRICA ---")
                cambios.append(f"Datos: {', '.join(elec_info) if elec_info else 'No requiere / Sin datos'}")


                mats_terr = []
                if levantamiento.mat_pvc: mats_terr.append("PVC")
                if levantamiento.mat_pvc_lum: mats_terr.append("PVC Lumínico")
                if levantamiento.mat_acrilico: mats_terr.append("Acrílico")
                if levantamiento.mat_adh_nor: mats_terr.append("Adhesivo Normal")
                if levantamiento.mat_adh_trans: mats_terr.append("Adhesivo Transparente")
                cambios.append(f"Materiales Terreno: {', '.join(mats_terr) if mats_terr else 'Sin definir'}")

                terms_terr = []
                if levantamiento.term_ojetillos: terms_terr.append("Ojetillos")
                if levantamiento.term_bolsillo: terms_terr.append("Bolsillo")
                if levantamiento.term_tubo: terms_terr.append("Tubo")
                if levantamiento.term_bastidor: terms_terr.append("Bastidor")
                if levantamiento.term_laminado: terms_terr.append("Laminado")
                if levantamiento.term_troquel: terms_terr.append("Troquelado")
                cambios.append(f"Terminaciones Terreno: {', '.join(terms_terr) if terms_terr else 'Sin definir'}")


                riesgos = []
                if levantamiento.riesgo_altura: riesgos.append("Altura")
                if levantamiento.riesgo_transito: riesgos.append("Tránsito")
                if levantamiento.riesgo_permiso: riesgos.append("Requiere Permiso")
                if levantamiento.riesgo_energia: riesgos.append("Energía")
                cambios.append(f"Riesgos detectados: {', '.join(riesgos) if riesgos else 'Ninguno'}")
                cambios.append(f"Tiempo est. instalación: {levantamiento.tiempo_estimado_instalacion}")
            else:
                    cambios.append(f"\n--- DETALLES DE TERRENO ---")
                    cambios.append("No se ingresó ficha técnica de terreno en la creación.")


            detalle_final = "\n".join(cambios)

            AccionHistorial.objects.create(
                    usuario=request.user,
                    accion=f"ADMIN: Creó Proceso Completo #{nuevo_proceso.id}",
                    detalles=detalle_final
                )

            if proceso_id:
                messages.success(request, f"Proceso #{nuevo_proceso.id} actualizado correctamente")
            else:
                messages.success(request, f"¡Proceso #{nuevo_proceso.id} creado correctamente!")
            return redirect('dashboard')

        except Exception as e:
            print(f"ERROR FATAL: {e}")
            messages.error(request, f"Error al guardar: {e}")

    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def generar_pdf_proceso(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    try:
        lev = proceso.levantamiento
    except:
        lev = None

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="OT_{proceso.id}.pdf"'

    p = canvas.Canvas(response, pagesize=LETTER)

    p.setTitle(f"OT-{proceso.id:05d} - {proceso.cliente.razon_social}")
    width, height = LETTER
    

    azul_oscuro = (0.02, 0.02, 0.26)

    p.setFillColorRGB(*azul_oscuro)
    p.rect(0, height-80, width, 80, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)

    p.drawString(30, height-45, f"ORDEN DE TRABAJO: OT-{proceso.id:05d} | {proceso.get_familia_display().upper()}")
    
    p.setFont("Helvetica", 10)
    fecha_ot = proceso.creado.strftime('%d/%m/%Y') if proceso.creado else 'S/D'
    fecha_entrega = proceso.fecha_entrega.strftime('%d/%m/%Y') if proceso.fecha_entrega else 'S/D'
    

    p.drawString(30, height-60, f"Cliente: {proceso.cliente.razon_social} | Fecha OT: {fecha_ot} | Entrega: {fecha_entrega}")




    y = height - 110
    p.setFillColorRGB(*azul_oscuro)
    p.rect(30, y, width-60, 20, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y+6, "DATOS DE TERRENO")
    
    y -= 20
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 9)
    
    if lev:

        p.drawString(40, y, f"DIMENSIONES: {lev.ancho} x {lev.alto} x {lev.profundidad_letrero} cm")

        p.drawString(320, y, f"UBICACIÓN: {lev.ubicacion.upper()} (Alt: {lev.altura_instalacion}m)")
        
        y -= 15

        acc = [n for v, n in [(lev.acceso_escalera, "Escalera"), (lev.acceso_andamio, "Andamio"), (lev.acceso_grua, "Grúa")] if v]
        p.drawString(40, y, f"ACCESOS: {', '.join(acc) or 'Normal'}")
        
        sop = [n for v, n in [(lev.soporte_muro, "Muro"), (lev.soporte_metal, "Metal"), (lev.soporte_vidrio, "Vidrio"), (lev.soporte_panel_compuesto, "Panel Comp.")] if v]
        p.drawString(320, y, f"SOPORTE: {', '.join(sop)} {lev.soporte_otro or ''}")

        y -= 15

        p.drawString(40, y, f"ELEC: {'Punto OK' if lev.punto_cercano else 'S/P'} | Tablero: {'OK' if lev.tablero_accesible else 'N/A'} | V: {lev.voltaje or 'S/D'}")
        
        rie = [n for v, n in [(lev.riesgo_altura, "Altura"), (lev.riesgo_transito, "Tránsito"), (lev.riesgo_permiso, "Permiso"), (lev.riesgo_energia, "Energía")] if v]
        p.drawString(320, y, f"RIESGOS: {', '.join(rie) or 'Bajo Control'}")

        y -= 15

        mat_t = [n for v, n in [(lev.mat_pvc, "PVC"), (lev.mat_pvc_lum, "PVC Lum"), (lev.mat_acrilico, "Acril."), (lev.mat_adh_nor, "Adh. Nor")] if v]
        p.drawString(40, y, f"MATERIAL: {', '.join(mat_t)}")
        p.drawString(320, y, f"EST. INSTALACIÓN: {lev.tiempo_estimado_instalacion or 'S/D'}")

        y -= 20 
    

        styles = getSampleStyleSheet()
        estilo_restricciones = styles["Normal"]
        estilo_restricciones.fontName = "Helvetica"
        estilo_restricciones.fontSize = 9
        estilo_restricciones.leading = 11


        p.setFont("Helvetica-Bold", 9)
        p.drawString(40, y, "RESTRICCIONES DE ACCESO:")


        ancho_disponible = width - 185 - 40 
        texto_restricciones = f"{lev.restricciones_acceso or 'Ninguna.'}"
        p_restricciones = Paragraph(texto_restricciones, estilo_restricciones)


        w_p, h_p = p_restricciones.wrap(ancho_disponible, height)
        p_restricciones.drawOn(p, 185, y - h_p + 8)



        y -= h_p
        
    else:
        p.drawString(40, y, "No hay datos de levantamiento registrados.")




    y -= 35
    p.setFillColorRGB(*azul_oscuro)
    p.rect(30, y, width-60, 20, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y+6, f"ÁREA DE DISEÑO - RESPONSABLE: {proceso.responsable_diseno or 'NO ASIGNADO'}")
    
    y -= 20
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(40, y, "PIEZAS / DESCRIPCIÓN")
    p.drawString(350, y, "MEDIDAS (LxA)")
    p.drawString(500, y, "CANTIDAD")
    p.line(30, y-2, 580, y-2)
    
    y -= 15
    p.setFont("Helvetica", 8)
    try:
        mediciones = json.loads(proceso.mediciones_json)
        for m in mediciones:
            p.drawString(40, y, str(m.get('descripcion', 'S/D'))[:65])
            p.drawString(350, y, f"{m.get('largo', '0')} x {m.get('ancho', '0')} cm")
            p.drawString(500, y, str(m.get('cantidad', '1')))
            y -= 12
    except:
        p.drawString(40, y, "Sin mediciones de diseño.")


    y -= 10
    p.setFont("Helvetica-Bold", 8)
    checks_d = [(proceso.reunion, "Reunión"), (proceso.pauta, "Pauta"), (proceso.aprobacion_final, "APROBACIÓN FINAL")]
    x_d = 40
    for val, txt in checks_d:
        p.drawString(x_d, y, f"[{'X' if val else ' '}] {txt}")
        x_d += 120




    y -= 35
    p.setFillColorRGB(*azul_oscuro)
    p.rect(30, y, width-60, 20, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y+6, f"ÁREA DE TALLER - RESPONSABLE: {proceso.responsable_taller or 'NO ASIGNADO'}")
    

    y -= 20
    p.setFillColorRGB(0, 0, 0)
    

    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "MATERIALES:")
    
    p.setFont("Helvetica", 8)
    mats = [n for v, n in [
            (proceso.acrilico, "Acrílico"), (proceso.sintra, "Sintra"), 
            (proceso.ojetillo, "Ojetillo"), (proceso.ad_prom, "Adh. Prom."), 
            (proceso.ad_vehicular, "Adh. Vehicular"), (proceso.empavonado, "Empavonado"), 
            (proceso.microperf, "Microperf."), (proceso.sellado, "Sellado"), 
            (proceso.tela_pvc, "Tela PVC")
        ] if v]
    
    texto_mats = ", ".join(mats)
    if proceso.otros_materiales:
        texto_mats += f" | OTROS: {proceso.otros_materiales}"
    

    p.drawString(110, y, texto_mats[:110]) 


    y -= 18
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "PROCESOS:")
    
    p.setFont("Helvetica", 8)
    check_impresion = 'X' if proceso.impresion else ' '
    check_corte = 'X' if proceso.corte else ' '
    check_aprobado = 'X' if proceso.aprobacion_taller else ' '
    

    p.drawString(110, y, f"[{check_impresion}] IMPRESIÓN      [{check_corte}] CORTE      [{check_aprobado}] APROBACIÓN FINAL TALLER")


    y -= 15
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "TERMINACIONES:")
    p.setFont("Helvetica", 8)
    p.drawString(130, y, f"{proceso.terminaciones or 'Sin terminaciones especiales'}")


    y -= 10
    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(35, y, width-35, y)
    y -= 15



    y -= 35
    p.setFillColorRGB(*azul_oscuro)
    p.rect(30, y, width-60, 20, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y+6, "PLOTEO VEHICULAR")
    
    y -= 20
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 8)

    p.drawString(40, y, "DESCRIPCIÓN DE PIEZA / MATERIAL")
    p.drawString(300, y, "MEDIDAS (LxA)")
    p.drawString(420, y, "CANT.")
    p.drawString(480, y, "OBSERVACIÓN")
    
    y -= 5
    p.line(30, y, 580, y)
    y -= 12
    
    p.setFont("Helvetica", 8)
    try:

        med_taller = proceso.get_mediciones_taller_list()
        
        if not med_taller:
             p.drawString(40, y, "No se registraron detalles de despiece para producción.")
        else:
            for mt in med_taller:
                if y < 50:
                    p.showPage()
                    y = height - 50
                    p.setFont("Helvetica", 8)


                desc = str(mt.get('nombre') or mt.get('descripcion') or 'Pieza').strip()
                


                medida_str = mt.get('medida', '0 x 0')
                if 'x' in medida_str:
                    partes = medida_str.split('x')
                    largo = partes[0].strip()
                    ancho = partes[1].strip()
                else:
                    largo = medida_str
                    ancho = "0"



                cant = str(mt.get('cantidad') or '1').strip()
                obs = str(mt.get('observacion') or '').strip()


                p.drawString(40, y, desc[:55]) 
                p.drawString(300, y, f"{largo} x {ancho} cm")
                p.drawString(420, y, cant)
                p.drawString(480, y, obs[:25])
                
                y -= 12
    except Exception as e:
        p.drawString(40, y, f"Error técnico en datos de taller: {str(e)}")




    y -= 30
    p.line(30, y, 580, y)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(30, y-15, "INSTRUCCIONES ADMINISTRACIÓN:")
    p.setFont("Helvetica", 9)
    p.drawString(30, y-30, f"{proceso.instrucciones_admin or 'Sin instrucciones especiales.'}")

    p.showPage()
    p.save()
    return response

@login_required
def finalizar_diseno(request, pk):

    proceso = get_object_or_404(Proceso, pk=pk)
    


    if proceso.pasa_por_taller:
        proceso.estado = 'taller'
        msg = f"Diseño de {proceso} aprobado. Se ha movido a la bandeja de Taller."
    else:
        proceso.estado = 'finalizado'
        msg = f"Diseño de {proceso} finalizado. No requiere taller, se movió a revisión final."


    try:
        proceso.save()
        messages.success(request, msg)
    except Exception as e:

        messages.error(request, f"Error al actualizar el proceso: {str(e)}")
        

    return redirect('dashboard_diseno')



