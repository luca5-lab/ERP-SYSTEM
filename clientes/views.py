from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cliente
from .forms import ClienteForm, ProveedorForm
import pandas as pd
from django.http import HttpResponse
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from .models import Proveedor
from usuarios.models import Perfil
import openpyxl
from usuarios.decorators import usuario_tipo_requerido
from usuarios.models import Proceso, Perfil


@login_required
@usuario_tipo_requerido('admin','administracion')  
def informes(request):
    clientes_count = Cliente.objects.count()
    proveedores_count = Proveedor.objects.count()
    total_ventas = 0 

    context = {
        'clientes_count': clientes_count,
        'proveedores_count': proveedores_count,
        'total_ventas': total_ventas
    }

    return render(request, 'clientes/informes.html', context)

@login_required
@usuario_tipo_requerido('admin', 'taller', 'administracion')
def lista_proveedores(request):

    buscar = request.GET.get("buscar")

    proveedores = Proveedor.objects.all()

    if buscar:
        proveedores = proveedores.filter(rut__icontains=buscar)

    # Obtener el tipo de usuario del perfil
    tipo_usuario = getattr(request.user, 'perfil', None)
    tipo_usuario = tipo_usuario.tipo_usuario if tipo_usuario else None

    return render(
        request,
        'clientes/lista_proveedores.html',
        {
            'proveedores': proveedores,
            'buscar': buscar,
            'tipo_usuario': tipo_usuario  # <-- enviamos al template
        }
    )

@login_required
@usuario_tipo_requerido('admin')
def registrar_proveedor(request):

    if request.method == 'POST':
        form = ProveedorForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('lista_proveedores')

    else:
        form = ProveedorForm()

    return render(
        request,
        'clientes/registrar_proveedor.html',
        {'form': form}
    )

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_proveedor(request, pk):

    proveedor = get_object_or_404(Proveedor, pk=pk)

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)

        if form.is_valid():
            form.save()
            return redirect('lista_proveedores')

    else:
        form = ProveedorForm(instance=proveedor)

    return render(
        request,
        'clientes/registrar_proveedor.html',
        {
            'form': form,
            'editando': True
        }
    )

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_proveedor(request, pk):

    proveedor = get_object_or_404(Proveedor, pk=pk)

    if request.method == 'POST':
        proveedor.delete()
        return redirect('lista_proveedores')

    return render(
        request,
        'clientes/confirmar_eliminar_proveedor.html',
        {
            'proveedor': proveedor
        }
    )

@login_required
def exportar_clientes_excel(request):
    # 1. En lugar de .values(), obtenemos los objetos para usar sus métodos de "display"
    clientes_qs = Cliente.objects.all()

    # 2. Creamos una lista de diccionarios manualmente para asegurar el texto legible
    data = []
    for c in clientes_qs:
        data.append({
            'RAZÓN SOCIAL': c.razon_social,
            'GIRO': c.giro,
            'RUT': c.rut,
            'DIRECCIÓN': c.direccion,
            'EMAIL': c.correo,
            'TELÉFONO': c.telefono,
            'FECHA REGISTRO': c.fecha_registro,
            # Aquí está el truco: get_campo_display() trae el texto, no el número
            'COND. PAGO': c.get_condiciones_pago_display() 
        })

    df = pd.DataFrame(data)

    # 3. Limpiar zona horaria para Excel
    if not df.empty:
        df['FECHA REGISTRO'] = df['FECHA REGISTRO'].dt.tz_localize(None)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Reporte_Clientes_USBTech.xlsx"'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Base de Clientes')
        worksheet = writer.sheets['Base de Clientes']

        # --- ESTILOS (Igual que los tenías) ---
        header_fill = PatternFill(start_color="0D6EFD", end_color="0D6EFD", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        alignment_center = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # Estilo encabezados y auto-ancho
        for col_num, column_title in enumerate(df.columns, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = alignment_center
            cell.border = thin_border

            max_length = max(df[column_title].astype(str).map(len).max(), len(column_title)) + 5
            worksheet.column_dimensions[chr(64 + col_num)].width = max_length

        # Estilo datos
        for row in worksheet.iter_rows(min_row=2, max_row=len(df) + 1):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="left")

    return response


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    
    # Aquí añadimos 'editando': True al contexto
    return render(request, 'clientes/registrar_cliente.html', {
        'form': form, 
        'editando': True  # <--- Esta es la clave
    })

@login_required
@usuario_tipo_requerido('admin', 'administracion')
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        return redirect('lista_clientes')
    return render(request, 'clientes/confirmar_eliminar.html', {'cliente': cliente})


@login_required
@usuario_tipo_requerido('admin', 'administracion')
def registrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes') # Ahora esto ya no fallará
    else:
        form = ClienteForm()
    return render(request, 'clientes/registrar_cliente.html', {'form': form})


@login_required
def lista_clientes(request):

    buscar = request.GET.get("buscar")

    clientes = Cliente.objects.all()

    if buscar:
        clientes = clientes.filter(rut__icontains=buscar)

    tipo_usuario = getattr(request.user, 'perfil', None)
    tipo_usuario = tipo_usuario.tipo_usuario if tipo_usuario else None

    return render(
        request,
        'clientes/lista_clientes.html',
        {
            'clientes': clientes,
            'buscar': buscar,
            'tipo_usuario': tipo_usuario  
        }
    )

@login_required
def exportar_proveedores_excel(request):
    # Obtener datos de proveedores
    proveedores = Proveedor.objects.all()
    
    # Crear una lista de diccionarios para el DataFrame
    data = []
    for p in proveedores:
        data.append({
            'RAZÓN SOCIAL': p.razon_social,
            'GIRO': p.giro,
            'RUT': p.rut,
            'EMAIL': p.correo,
            'TELÉFONO': p.telefono or "",
            'COND. PAGO': p.get_condiciones_pago_display()
        })

    df = pd.DataFrame(data)

    # Configurar la respuesta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Reporte_Proveedores_USBTech.xlsx"'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Base de Proveedores')
        worksheet = writer.sheets['Base de Proveedores']

        # --- DEFINICIÓN DE ESTILOS ---
        header_fill = PatternFill(
            start_color="0D6EFD", # Azul corporativo
            end_color="0D6EFD",
            fill_type="solid"
        )

        header_font = Font(
            color="FFFFFF", # Blanco
            bold=True,
            size=12
        )

        alignment_center = Alignment(horizontal="center", vertical="center")
        alignment_left = Alignment(horizontal="left", vertical="center")

        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # --- APLICAR ESTILOS A ENCABEZADOS Y AJUSTAR COLUMNAS ---
        for col_num, column_title in enumerate(df.columns, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = alignment_center
            cell.border = thin_border

            # Calcular ancho automático (largo del texto + margen)
            max_length = max(
                df[column_title].astype(str).map(len).max(),
                len(column_title)
            ) + 5
            
            # Convertir número de columna a letra (1->A, 2->B, etc.)
            col_letter = chr(64 + col_num)
            worksheet.column_dimensions[col_letter].width = max_length

        # --- APLICAR ESTILOS A LOS DATOS ---
        for row in worksheet.iter_rows(
            min_row=2,
            max_row=len(df) + 1,
            min_col=1,
            max_col=len(df.columns)
        ):
            for cell in row:
                cell.border = thin_border
                cell.alignment = alignment_left

    return response

@login_required
def lista_procesos_clientes(request):
    buscar = request.GET.get("buscar")
    
    # Obtenemos los procesos ordenados por los más recientes
    procesos = Proceso.objects.select_related('cliente', 'usuario').all().order_by('-creado')

    if buscar:
        # Filtramos por nombre de cliente o RUT
        procesos = procesos.filter(
            Q(cliente__razon_social__icontains=buscar) | 
            Q(cliente__rut__icontains=buscar)
        )

    return render(request, 'clientes/lista_procesos.html', {
        'procesos': procesos,
        'buscar': buscar
    })

