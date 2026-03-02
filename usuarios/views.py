from django.shortcuts import render, redirect
from reportlab.lib.utils import ImageReader
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm, AuthenticationForm
from .forms import UsuarioForm, EditarUsuarioForm, ProcesoForm, ArticuloForm, ServicioForm, DisenoForm, TallerForm
from clientes.models import Cliente, Proveedor
from .models import Perfil, Proceso, MaterialStock, Articulo, Servicio, CotizacionArticulo, DetalleCotizacionArticulo,CotizacionServicio, AccionHistorial
from django.contrib.auth import authenticate, login
from .decorators import usuario_tipo_requerido
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from decimal import Decimal
import os  
from django.conf import settings 
from reportlab.lib.units import cm
from django.contrib.staticfiles import finders
from django.utils import timezone

@login_required
def generar_pdf_cotizacion(request, pk):
    # 1. Obtener datos base
    cotizacion = get_object_or_404(CotizacionArticulo, pk=pk)
    detalles = cotizacion.detalles.all()
    cliente = cotizacion.cliente

    # 2. Configurar respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Cotizacion_{cotizacion.n_presupuesto}.pdf"'

    p = canvas.Canvas(response, pagesize=LETTER)
    width, height = LETTER

    # ==================================================
    # LOGO
    # ==================================================
    logo_path = finders.find('images/logo.png')
    if logo_path:
        logo = ImageReader(logo_path)
        p.drawImage(logo, 30, height-95, width=175, height=100, preserveAspectRatio=True, mask='auto')

    # ==================================================
    # DATOS EMPRESA (BLOQUE DERECHA)
    # ==================================================
    x_empresa = width - 300
    y_empresa = height - 40
    p.setFont("Helvetica-Bold", 11)
    p.drawString(x_empresa, y_empresa, "USBTECH SPA")
    p.setFont("Helvetica", 9)
    p.drawString(x_empresa, y_empresa-15, "Camino a Montahue #55, San Pedro de La Paz.")
    p.drawString(x_empresa, y_empresa-30, "contacto@usbtech.cl | +56 9 9653 3834")
    p.drawString(x_empresa, y_empresa-45, "www.usbtech.cl")
    p.drawString(x_empresa, y_empresa-60, "Rut: 77.859.775-6")
    p.drawString(x_empresa, y_empresa-75, "Giro: OTRAS ACTIVIDADES ESPECIALIZADAS DE DISEÑO N.C.P")

    # ==================================================
    # LINEA SUPERIOR Y CLIENTE
    # ==================================================
    p.line(40, height-135, width-40, height-135)
    y_info = height-160
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_info, "Cliente:")
    p.drawString(40, y_info-15, cliente.razon_social.upper())
    p.drawString(width-230, y_info, f"Presupuesto: {str(cotizacion.n_presupuesto).zfill(5)}")
    p.setFont("Helvetica", 9)
    p.drawString(width-230, y_info-15, f"Fecha: {cotizacion.fecha.strftime('%d-%m-%Y')}")
    p.line(40, y_info-30, width-40, y_info-30)

    # ==================================================
    # ENCABEZADO TABLA
    # ==================================================
    y = y_info-55
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Descripción del articulo")
    p.drawString(330, y, "Cantidad")
    p.drawString(420, y, "Precio Unitario")
    p.drawString(520, y, "Total")
    p.line(40, y-5, width-40, y-5)

    # ==================================================
    # DETALLE (BUCLE DINÁMICO)
    # ==================================================
    y -= 25
    p.setFont("Helvetica", 9)
    neto = Decimal("0.00")

    for item in detalles:
        # --- LÓGICA DE PRECIO SEGURO ---
        # Si el precio_unitario del detalle es > 0, usamos ese (el especial).
        # Si es 0 o None, usamos el del catálogo (el original).
        if item.precio_unitario and item.precio_unitario > 0:
            precio_final = item.precio_unitario
        else:
            precio_final = item.articulo.precio_unitario
            
        subtotal = item.cantidad * precio_final
        neto += subtotal

        # Escribir fila
        descripcion = item.articulo.descripcion[:60]
        p.drawString(40, y, descripcion)
        p.drawRightString(360, y, str(item.cantidad))
        p.drawRightString(470, y, f"$ {precio_final:,.0f}")
        p.drawRightString(560, y, f"$ {subtotal:,.0f}")

        y -= 18

        # Salto de página
        if y < 150:
            p.showPage()
            y = height - 80
            p.setFont("Helvetica", 9)

    # ==================================================
    # TOTALES Y DATOS DE PAGO
    # ==================================================
    if y < 220:
        p.showPage()
        y = height - 80

    y_final = y - 40 

    # Bloque Izquierda: Pago
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_final, "Datos de Pago:")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_final-15, "Condiciones de pago: 50% inicio / 50% entrega")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_final-40, "DATOS BANCARIOS")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_final-55, "USBTECH SPA | Rut: 77.859.775-6")
    p.drawString(40, y_final-70, "Banco Santander | Cuenta Corriente: 98308091")
    p.drawString(40, y_final-85, "contacto@usbtech.cl")

    # Bloque Derecha: Totales
    iva = neto * Decimal("0.19")
    total = neto + iva

    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, y_final, "Subtotal")
    p.drawRightString(560, y_final, f"$ {neto:,.0f}")
    p.drawString(400, y_final-18, "IVA (19)%")
    p.drawRightString(560, y_final-18, f"$ {iva:,.0f}")
    
    p.line(390, y_final-30, width-40, y_final-30)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(400, y_final-45, "Total")
    p.drawRightString(560, y_final-45, f"$ {total:,.0f}")

    p.showPage()
    p.save()
    return response

@require_POST
@login_required
def actualizar_stock_ajax(request):
    material_id = request.POST.get('id')
    accion = request.POST.get('accion')
    material = get_object_or_404(MaterialStock, id=material_id)

    if accion == 'up':
        material.nivel_actual = min(100, material.nivel_actual + 5) 
    elif accion == 'down':
        material.nivel_actual = max(0, material.nivel_actual - 5)   
    
    material.save()
    
    return JsonResponse({
        'nuevo_nivel': material.nivel_actual,
        'status': 'success'
    })

@login_required
def login_redirect(request):
    user = request.user
    
    # 1. Superusuarios siempre al panel de administración principal
    if user.is_superuser:
        return redirect('dashboard')

    # 2. Obtener el tipo de usuario del perfil
    tipo = getattr(user.perfil, 'tipo_usuario', None)

    # 3. Lógica de redirección por tipo
    if tipo == 'taller':
        return redirect('dashboard_taller')
    
    elif tipo in ['diseno', 'diseño']:
        return redirect('dashboard_diseno')
    
    elif tipo in ['admin', 'administrador', 'administracion']: 
        return redirect('dashboard')
    
    # 4. Fallback (si nada coincide, al dashboard general)
    return redirect('dashboard')


def login_usuario(request):
    """Vista personalizada de login que redirige según tipo de usuario."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Autenticar usuario
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Verificar si el usuario está activo
            if not user.is_active:
                messages.error(request, "Usuario desactivado. Contacte al administrador.")
                return redirect('login')

            # Iniciar sesión en el sistema
            login(request, user)

            # --- INICIO DE REDIRECCIÓN INTELIGENTE ---
            
            # Superuser directo al dashboard administrativo
            if user.is_superuser:
                return redirect('dashboard')

            # Obtener tipo de usuario de forma segura
            try:
                tipo = user.perfil.tipo_usuario
            except AttributeError:
                tipo = None

            # Redirección según tipo de perfil
            if tipo == 'taller':
                return redirect('dashboard_taller')
            
            elif tipo in ['diseno', 'diseño']:
                return redirect('dashboard_diseno')
            
            elif tipo in ['admin', 'administrador', 'administracion']:
                return redirect('dashboard')

            # Por defecto si no tiene un tipo asignado que reconozcamos
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



# views.py

@login_required
def dashboard_taller(request):
    # Solo mostramos lo que Diseño ya despachó
    procesos = Proceso.objects.filter(estado='taller').order_by('-creado')
    
    if request.method == 'POST':
        # Buscamos el ID del proceso que se está editando en taller
        proceso_id = request.POST.get('proceso_id')
        proceso = get_object_or_404(Proceso, id=proceso_id)
        form = TallerForm(request.POST, instance=proceso)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Avance de producción guardado.")
            AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"MODIFICÓ datos técnicos del proceso ID {proceso.id}"
            )
            return redirect('dashboard_taller')
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

    # ESTA LÍNEA ES LA CLAVE:
    # 'FAMILIAS_SERVICIOS' es el nombre de la lista que creamos en el Model
    familias_opciones = Servicio.FAMILIAS_SERVICIOS 

    return render(request, 'usuarios/lista_servicios.html', {
        'servicios': servicios,
        'familias': familias_opciones, # <--- Asegúrate que este nombre coincida con el del HTML
        'busqueda_codigo': busqueda_codigo,
        'busqueda_familia': busqueda_familia
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def crear_articulo(request):
    if request.method == 'POST':
        form = ArticuloForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_articulos')
    else:
        form = ArticuloForm()
    return render(request, 'usuarios/crear_articulo.html', {'form': form})


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_articulo(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    
    if request.method == 'POST':
        # instance=articulo es lo que hace que se actualice y no se cree otro
        form = ArticuloForm(request.POST, instance=articulo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Artículo {articulo.codigo} actualizado.")
            return redirect('lista_articulos')
    else:
        # Pre-carga el formulario con los datos del artículo
        form = ArticuloForm(instance=articulo)
    
    return render(request, 'usuarios/crear_articulo.html', {
        'form': form, 
        'editando': True
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_articulo(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    codigo_eliminado = articulo.codigo
    articulo.delete()
    messages.warning(request, f"Artículo {codigo_eliminado} eliminado correctamente.")
    return redirect('lista_articulos')
    


@login_required
def stock_view(request):
    materiales = MaterialStock.objects.all().order_by('categoria')

    context = {
        'materiales': materiales,
    }
    
    return render(request, 'usuarios/stock.html', context)

@login_required
def editar_proceso(request, pk):
    # 1. Obtenemos el objeto original de la DB
    proceso = get_object_or_404(Proceso, pk=pk)
    
    # 2. Guardamos el cliente original en una variable por seguridad
    cliente_original = proceso.cliente 

    if request.method == 'POST':
        form = TallerForm(request.POST, instance=proceso)
        
        if form.is_valid():
            # 3. commit=False crea el objeto en memoria pero no lo escribe aún
            proceso_editado = form.save(commit=False)
            
            # 4. Forzamos el cliente original de vuelta al objeto
            proceso_editado.cliente = cliente_original
            
            # 5. Guardamos definitivamente
            proceso_editado.save()
            
            AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"MODIFICÓ datos técnicos y aprobación del proceso ID {proceso.id}"
            )
            return redirect('dashboard_taller')
        else:
            print(form.errors) # Para ver si hay otros errores en consola
    else:
        form = TallerForm(instance=proceso)
    
    return render(request, 'usuarios/editar_proceso.html', {
        'form': form, 
        'proceso': proceso
    })


@require_POST
@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_material_nombre_ajax(request):
    # Usamos MaterialStock que es como lo tienes en tus imports
    material_id = request.POST.get('id')
    nuevo_nombre = request.POST.get('nombre')
    nueva_variedad = request.POST.get('variedad')
    
    try:
        # CAMBIO AQUÍ: Usamos MaterialStock en lugar de Material
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

    # No permitir desactivarse a sí mismo
    if request.user == user_obj:
        messages.error(request, "No puedes desactivar tu propio usuario.")
        return redirect('lista_usuarios')

    # Cambiar el estado activo
    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    if user_obj.is_active:
        messages.success(request, f"Usuario {user_obj.username} activado correctamente.")
    else:
        messages.success(request, f"Usuario {user_obj.username} desactivado correctamente.")

    return redirect('lista_usuarios')

@login_required
def dashboard(request):
    user = request.user

    # 1. SEGURIDAD Y REDIRECCIÓN POR ROL
    try:
        tipo = user.perfil.tipo_usuario
    except:
        tipo = None

    if not user.is_superuser and tipo != 'administracion':
        if tipo in ['diseno', 'diseño']:
            return redirect('dashboard_diseno')
        elif tipo == 'taller':
            return redirect('dashboard_taller')

    # 2. CÁLCULO DE CONTADORES
    en_diseno_count = Proceso.objects.filter(estado='diseno').count()
    en_taller_count = Proceso.objects.filter(estado='taller').count()
    pendientes_cierre = Proceso.objects.filter(estado='finalizado').count()
    
    # 3. OBTENER PROCESOS PARA LA TABLA
    procesos = Proceso.objects.all().order_by('-creado')[:20] 

    # 4. OBTENER CLIENTES PARA EL MODAL (ESTO FALTABA)
    # Traemos todos los clientes para que aparezcan en el selector del modal "Tareas"
    clientes = Cliente.objects.all().order_by('razon_social')

    # 5. CONTEXTO PARA EL TEMPLATE
    context = {
        'en_diseno_count': en_diseno_count,
        'en_taller_count': en_taller_count,
        'pendientes_cierre': pendientes_cierre,
        'procesos': procesos, 
        'clientes': clientes,  # <--- Agregamos esto para el modal
        'clientes_count': clientes.count(),
        'hoy': timezone.now(),
    }

    return render(request, 'usuarios/dashboard.html', context)

@login_required
@usuario_tipo_requerido('admin','administracion')
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'usuarios/lista_usuarios.html', {'usuarios': usuarios})


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def registrar_usuario(request):

    if request.method == 'POST':
        form = UsuarioForm(request.POST)

        if form.is_valid():

            user = form.save()

            Perfil.objects.create(
                user=user,
                tipo_usuario=form.cleaned_data['tipo_usuario']
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

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)

        if form.is_valid():
            form.save()
            messages.success(request, "Usuario editado correctamente")
            return redirect('lista_usuarios')

        else:
            for errors in form.errors.values():
                for error in errors:
                    mensaje = PASSWORD_TRANSLATIONS.get(error, error)
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

    # Evitar que el usuario se elimine a sí mismo
    if request.user == usuario:
        messages.error(request, "No puedes eliminar tu propio usuario.")
        return redirect('lista_usuarios')

    # Evitar eliminar superusuarios
    if usuario.is_superuser:
        messages.error(request, "No se puede eliminar un usuario administrador.")
        return redirect('lista_usuarios')

    if request.method == 'POST':
        usuario.delete()
        messages.success(request, f"Usuario {usuario.username} eliminado correctamente.")
        return redirect('lista_usuarios')

    return render(
        request,
        'usuarios/confirmar_eliminar_usuario.html',
        {'usuario': usuario}
    )


@login_required
@usuario_tipo_requerido('admin','administracion')
def crear_servicio(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_servicios')
    else:
        form = ServicioForm()
    return render(request, 'usuarios/crear_servicio.html', {'form': form, 'editando': False})

@login_required
@usuario_tipo_requerido('admin','administracion')
def editar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return redirect('lista_servicios')
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'usuarios/crear_servicio.html', {'form': form, 'editando': True})

@login_required
@usuario_tipo_requerido('admin','administracion')
def eliminar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    servicio.delete()
    return redirect('lista_servicios')

@login_required
def menu_cotizaciones(request):
    return render(request, 'usuarios/menu_cotizaciones.html')

@login_required
def cotizar_servicio_nuevo(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        servicio_id = request.POST.get('servicio')
        # Limpiamos la cantidad por si llega con comas de miles o decimales mal formateados
        cantidad_str = request.POST.get('cantidad', '0').replace(',', '.') 
        
        cliente = get_object_or_404(Cliente, id=cliente_id)
        servicio = get_object_or_404(Servicio, id=servicio_id)
        
        # Creamos la cotización
        # IMPORTANTE: Usamos el precio directamente desde el objeto 'servicio' de la BD
        # para evitar cualquier error de manipulación en el frontend.
        CotizacionServicio.objects.create(
            cliente=cliente,
            servicio=servicio,
            cantidad_m2=Decimal(cantidad_str),
            valor_unitario_m2=servicio.costo_m2 
        )
        
        return redirect('lista_cotizaciones_servicios')

    context = {
        'clientes': Cliente.objects.all().order_by('razon_social'),
        'servicios': Servicio.objects.all().order_by('codigo'),
    }
    return render(request, 'usuarios/cotizar_servicio.html', context)

@login_required
def cotizar_articulos_nuevo(request):
    # Traemos los artículos para que el usuario pueda seleccionarlos después
    articulos = Articulo.objects.all().order_by('descripcion')
    clientes = Cliente.objects.all().order_by('razon_social')

    return render(request, 'usuarios/cotizar_articulo.html', {
        'articulos': articulos,
        'clientes': clientes
    })

@login_required
def lista_cotizaciones_articulos(request):
    # Empezamos con todas las cotizaciones
    cotizaciones = CotizacionArticulo.objects.all().order_by('-fecha')

    # Filtro por N° de Presupuesto
    n_presupuesto = request.GET.get('n_presupuesto')
    if n_presupuesto:
        cotizaciones = cotizaciones.filter(n_presupuesto__icontains=n_presupuesto)

    # Filtro por Cliente (busca en la razón social del cliente relacionado)
    cliente_query = request.GET.get('cliente')
    if cliente_query:
        cotizaciones = cotizaciones.filter(cliente__razon_social__icontains=cliente_query)

    return render(request, 'usuarios/lista_cotizaciones_articulos.html', {
        'cotizaciones': cotizaciones
    })

@login_required
@require_POST
def guardar_cotizacion_articulo(request):
    try:
        data = json.loads(request.body)

        cliente_id = data.get('cliente_id')
        items = data.get('items')
        total_final = data.get('total_final')

        if not items:
            return JsonResponse({
                'status': 'error',
                'message': 'No hay artículos en la lista'
            }, status=400)

        cliente = Cliente.objects.get(id=cliente_id)

        cotizacion = CotizacionArticulo.objects.create(
            cliente=cliente,
            total_final=Decimal(str(total_final))
        )

        for item in items:

            articulo = Articulo.objects.get(id=item['id'])

            precio = Decimal(str(item['precio_unitario']))

            DetalleCotizacionArticulo.objects.create(
                cotizacion=cotizacion,
                articulo=articulo,
                cantidad=int(item['cantidad']),
                precio_unitario=precio   # 👈 AQUÍ estaba el fallo
            )

        return JsonResponse({
            'status': 'success',
            'n_presupuesto': cotizacion.n_presupuesto
        })

    except Cliente.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Cliente no encontrado'
        }, status=404)

    except Exception as e:
        print("Error al guardar cotización:", e)
        return JsonResponse({
            'status': 'error',
            'message': 'Error al guardar cotización'
        }, status=400)

@login_required
def lista_cotizaciones_servicios(request):
    # Obtenemos todas las cotizaciones de servicios
    cotizaciones = CotizacionServicio.objects.all().order_by('-fecha')

    # Filtros (opcional, igual que en artículos)
    cliente_query = request.GET.get('cliente')
    if cliente_query:
        cotizaciones = cotizaciones.filter(cliente__razon_social__icontains=cliente_query)

    return render(request, 'usuarios/lista_cotizaciones_servicios.html', {
        'cotizaciones': cotizaciones
    })

@login_required
def generar_pdf_cotizacion_servicio(request, pk):
    # 1. Obtener datos base (Cambiamos el modelo a CotizacionServicio)
    cotizacion = get_object_or_404(CotizacionServicio, pk=pk)
    cliente = cotizacion.cliente

    # 2. Configurar respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Cotizacion_Servicio_{cotizacion.id}.pdf"'

    p = canvas.Canvas(response, pagesize=LETTER)
    width, height = LETTER

    # ==================================================
    # LOGO
    # ==================================================
    logo_path = finders.find('images/logo.png')
    if logo_path:
        logo = ImageReader(logo_path)
        p.drawImage(logo, 30, height-95, width=175, height=100, preserveAspectRatio=True, mask='auto')

    # ==================================================
    # DATOS EMPRESA (BLOQUE DERECHA)
    # ==================================================
    x_empresa = width - 300
    y_empresa = height - 40
    p.setFont("Helvetica-Bold", 11)
    p.drawString(x_empresa, y_empresa, "USBTECH SPA")
    p.setFont("Helvetica", 9)
    p.drawString(x_empresa, y_empresa-15, "Camino a Montahue #55, San Pedro de La Paz.")
    p.drawString(x_empresa, y_empresa-30, "contacto@usbtech.cl | +56 9 9653 3834")
    p.drawString(x_empresa, y_empresa-45, "www.usbtech.cl")
    p.drawString(x_empresa, y_empresa-60, "Rut: 77.859.775-6")
    p.drawString(x_empresa, y_empresa-75, "Giro: OTRAS ACTIVIDADES ESPECIALIZADAS DE DISEÑO N.C.P")

    # ==================================================
    # LINEA SUPERIOR Y CLIENTE
    # ==================================================
    p.line(40, height-135, width-40, height-135)
    y_info = height-160
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_info, "Cliente:")
    p.drawString(40, y_info-15, cliente.razon_social.upper())
    # Usamos id porque CotizacionServicio no tiene n_presupuesto
    p.drawString(width-230, y_info, f"Presupuesto: {str(cotizacion.id).zfill(5)}") 
    p.setFont("Helvetica", 9)
    p.drawString(width-230, y_info-15, f"Fecha: {cotizacion.fecha.strftime('%d-%m-%Y')}")
    p.line(40, y_info-30, width-40, y_info-30)

    # ==================================================
    # ENCABEZADO TABLA (ADAPTADO A SERVICIOS)
    # ==================================================
    y = y_info-55
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y, "Descripción del Servicio")
    p.drawString(330, y, "Cant. m2")
    p.drawString(420, y, "Valor m2")
    p.drawString(520, y, "Total")
    p.line(40, y-5, width-40, y-5)

    # ==================================================
    # DETALLE (ÚNICA FILA PARA SERVICIO)
    # ==================================================
    y -= 25
    p.setFont("Helvetica", 9)
    
    # Datos del modelo CotizacionServicio
    descripcion = cotizacion.servicio.descripcion[:60]
    cantidad = cotizacion.cantidad_m2
    precio_m2 = cotizacion.valor_unitario_m2
    neto = cotizacion.total_neto

    # Escribir fila única
    p.drawString(40, y, descripcion)
    p.drawRightString(360, y, f"{cantidad:,.2f}") # Formato 2 decimales para m2
    p.drawRightString(470, y, f"$ {precio_m2:,.0f}")
    p.drawRightString(560, y, f"$ {neto:,.0f}")

    # ==================================================
    # TOTALES Y DATOS DE PAGO (IGUAL AL ORIGINAL)
    # ==================================================
    y_final = y - 60 

    # Bloque Izquierda: Pago
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_final, "Datos de Pago:")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_final-15, "Condiciones de pago: 50% inicio / 50% entrega")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, y_final-40, "DATOS BANCARIOS")
    p.setFont("Helvetica", 9)
    p.drawString(40, y_final-55, "USBTECH SPA | Rut: 77.859.775-6")
    p.drawString(40, y_final-70, "Banco Santander | Cuenta Corriente: 98308091")
    p.drawString(40, y_final-85, "contacto@usbtech.cl")

    # Bloque Derecha: Totales
    # Calculamos IVA sobre el total_neto de la cotización
    iva = neto * Decimal("0.19")
    total = neto + iva

    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, y_final, "Subtotal")
    p.drawRightString(560, y_final, f"$ {neto:,.0f}")
    p.drawString(400, y_final-18, "IVA (19)%")
    p.drawRightString(560, y_final-18, f"$ {iva:,.0f}")
    
    p.line(390, y_final-30, width-40, y_final-30)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(400, y_final-45, "Total")
    p.drawRightString(560, y_final-45, f"$ {total:,.0f}")

    p.showPage()
    p.save()
    return response

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def crear_material_ajax(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        categoria = request.POST.get('categoria')
        variedad = request.POST.get('variedad')
        
        # Se crea siempre con 100% como pediste
        MaterialStock.objects.create(
            nombre=nombre,
            categoria=categoria,
            variedad=variedad,
            nivel_actual=100
        )
        messages.success(request, "Material agregado al 100%")
        return redirect('stock_interno')

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_material(request, pk):
    material = get_object_or_404(MaterialStock, pk=pk)
    material.delete()
    return redirect('stock_interno')


@login_required
def dashboard_diseno(request):
    procesos = Proceso.objects.filter(estado='diseno').order_by('-creado')
    
    if request.method == 'POST':
        form = DisenoForm(request.POST) # <--- Usamos el formulario limitado
        if form.is_valid():
            proceso = form.save(commit=False)
            proceso.usuario = request.user
            proceso.estado = 'diseno'
            proceso.save()
            AccionHistorial.objects.create(
            usuario=request.user, 
            accion=f"CREÓ orden de trabajo para {proceso.cliente.razon_social}"
        )
            return redirect('dashboard_diseno')
    else:
        form = DisenoForm()

    return render(request, 'usuarios/dashboard_diseno.html', {'form': form, 'procesos': procesos})

@login_required
def pasar_a_taller(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    
    # REGLA DE ORO: Si el Admin dijo que NO pasa por taller, va a 'finalizado'
    if not proceso.pasa_por_taller:
        proceso.estado = 'finalizado'
        mensaje = f"Proyecto de {proceso.cliente.razon_social} finalizado en diseño y enviado a revisión de Admin."
    else:
        # Si sí requiere taller, sigue el flujo normal
        proceso.estado = 'taller'
        mensaje = f"Proyecto de {proceso.cliente.razon_social} enviado exitosamente a Taller."
    
    proceso.save()
    messages.success(request, mensaje)
    
    # Redirigir al panel de diseño
    return redirect('dashboard_diseno')

@login_required
def pasar_a_admin(request, pk):
    """Taller finaliza fabricación y envía a revisión de Admin."""
    proceso = get_object_or_404(Proceso, pk=pk)
    # Aquí podrías validar que impresión y corte estén marcados
    proceso.estado = 'finalizado'
    proceso.save()
    messages.success(request, f"Producción de {proceso.cliente.razon_social} terminada. Enviado a Admin.")
    AccionHistorial.objects.create(
        usuario=request.user, 
        accion=f"TERMINÓ manufactura y envió a Admin (Cliente: {proceso.cliente.razon_social})"
    )
    return redirect('dashboard_taller')

@login_required
@usuario_tipo_requerido('administracion')
def cerrar_proceso(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    proceso.estado = 'cerrado' # Cambia el estado para que desaparezca de la lista de pendientes
    proceso.save()
    messages.success(request, f"El proceso de {proceso.cliente.razon_social} ha sido archivado con éxito.")
    AccionHistorial.objects.create(
            usuario=request.user, 
            accion=f"CIERRE DEFINITIVO: Finalizó y archivó el proyecto de {proceso.cliente.razon_social} (ID: {proceso.id})"
        )
    return redirect('dashboard')

# views.py
@login_required
def editar_proceso_diseno(request, pk):
    # 1. Obtenemos el proceso original
    proceso = get_object_or_404(Proceso, pk=pk)
    # Guardamos el cliente original en una variable por si acaso
    cliente_original = proceso.cliente 
    
    if request.method == 'POST':
        # 2. Cargamos los datos del formulario
        form = DisenoForm(request.POST, instance=proceso)
        
        if form.is_valid():
            # 3. commit=False crea el objeto en memoria pero NO lo guarda aún
            proceso_editado = form.save(commit=False)
            
            # 4. Forzamos que el cliente sea el original (evita el IntegrityError)
            proceso_editado.cliente = cliente_original
            
            # 5. Ahora sí guardamos en la base de datos
            proceso_editado.save()
            
            messages.success(request, f"Actualizado: {cliente_original.razon_social}")
            AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"MODIFICÓ datos técnicos del proceso ID {proceso.id}"
            )
            return redirect('dashboard_diseno')
        else:
            messages.error(request, f"Errores: {form.errors}")
    else:
        form = DisenoForm(instance=proceso)
    
    return render(request, 'usuarios/editar_proceso_diseno.html', {
        'form': form,
        'proceso': proceso
    })

# views.py
@login_required
def finalizar_taller(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    # Cambiamos el estado a finalizado (esto pondrá el % en 90 automáticamente)
    proceso.estado = 'finalizado'
    proceso.save()
    messages.success(request, f"¡Proyecto de {proceso.cliente.razon_social} enviado a Administración!")
    return redirect('dashboard_taller')

@login_required
def enviar_a_admin(request, pk):
    """ Taller envía el trabajo terminado a revisión de Admin """
    proceso = get_object_or_404(Proceso, pk=pk)
    # Cambiamos a 'finalizado' (que según nuestro modelo es 90%)
    proceso.estado = 'finalizado'
    proceso.save()
    messages.success(request, f"Proyecto de {proceso.cliente.razon_social} enviado a Administración.")
    AccionHistorial.objects.create(
        usuario=request.user, 
        accion=f"TERMINÓ manufactura y envió a Admin (Cliente: {proceso.cliente.razon_social})"
    )
    return redirect('dashboard_taller')

@login_required
def cerrar_proceso_final(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    # Seguridad: Solo admin o superuser
    if request.user.is_superuser or request.user.perfil.tipo_usuario == 'administracion':
        proceso.estado = 'cerrado' # Esto activa el 100%
        proceso.save()
        messages.success(request, f"¡Proyecto de {proceso.cliente.razon_social} finalizado con éxito!")
        AccionHistorial.objects.create(
                usuario=request.user, 
                accion=f"CIERRE DEFINITIVO: Finalizó y archivó el proyecto de {proceso.cliente.razon_social} (ID: {proceso.id})"
            )
    return redirect('dashboard')

def error_403(request, exception=None):
    return render(request, '403.html', status=403)

@login_required
def lista_acciones(request):
    if not (request.user.is_superuser or request.user.perfil.tipo_usuario == 'administracion'):
        return redirect('dashboard')
    
    acciones = AccionHistorial.objects.all()
    return render(request, 'usuarios/lista_acciones.html', {'acciones': acciones})

@login_required
@usuario_tipo_requerido('administracion', 'admin')
@login_required
def crear_proceso_admin(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        pasa_diseno = request.POST.get('pasa_por_diseno') == 'on'
        pasa_taller = request.POST.get('pasa_por_taller') == 'on'
        instrucciones = request.POST.get('terminaciones') # Lo que el admin escribió en el punto 3

        # 1. Validar que el cliente exista
        cliente = get_object_or_404(Cliente, id=cliente_id)
        
        # 2. Determinar estado inicial
        estado_inicial = 'diseno' if pasa_diseno else 'taller'

        # 3. CREAR EL PROCESO (Aquí es donde faltaba el usuario)
        Proceso.objects.create(
            cliente=cliente,
            usuario=request.user,  # <--- ESTO SOLUCIONA EL ERROR
            estado=estado_inicial,
            terminaciones=instrucciones
        )

        return redirect('login_redirect')

@login_required
def finalizar_diseno(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    
    # Revisamos la ruta que definió el Admin
    if proceso.pasa_por_taller:
        proceso.estado = 'taller'
        msg = "Diseño aprobado. Enviado a Taller."
    else:
        proceso.estado = 'finalizado'
        msg = "Diseño aprobado. Enviado a Revisión de Admin (No requiere taller)."
        
    proceso.save()
    messages.success(request, msg)
    return redirect('dashboard_diseno')

@login_required
def finalizar_taller(request, pk):
    proceso = get_object_or_404(Proceso, pk=pk)
    # Taller siempre es el último paso técnico, así que siempre vuelve a Admin
    proceso.estado = 'finalizado'
    proceso.save()
    
    messages.success(request, f"Producción de {proceso.cliente.razon_social} terminada. Enviado a Admin.")
    return redirect('dashboard_taller')