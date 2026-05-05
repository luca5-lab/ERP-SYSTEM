from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil, Proceso, Articulo, Servicio, Factura, Venta, Compra, LevantamientoTerreno
from decimal import Decimal

from django import forms
from .models import LevantamientoTerreno

class LevantamientoTerrenoForm(forms.ModelForm):
    class Meta:
        model = LevantamientoTerreno
        exclude = ['proceso', 'firma_tecnico', 'firma_cliente'] # Las firmas las tratamos aparte
        widgets = {
            'restricciones_acceso': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'observaciones_adicionales': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'ubicacion': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le ponemos clases de Tailwind/Bootstrap a todos los inputs automáticamente
        for field in self.fields:
            if isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({'class': 'form-check-input'})
            else:
                self.fields[field].widget.attrs.update({'class': 'form-control'})



class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        # Se incluye margen_ganancia para que Django lo procese y guarde
        fields = ['familia', 'descripcion', 'costo_m2', 'margen_ganancia']
        
        widgets = {
            'familia': forms.Select(attrs={
                'class': 'form-select bg-light border-0 rounded-pill px-3'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control bg-light border-0 rounded-3', 
                'rows': 3
            }),
            'costo_m2': forms.TextInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'inputmode': 'numeric',  # Abre teclado numérico en móviles
                'type': 'text',          # Acepta puntos de miles visuales
            }),
            'margen_ganancia': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'step': '0.1',
                'min': '0',
                'placeholder': 'Ej: 20',
                'id': 'id_margen_ganancia' # Clave para que tu JavaScript lo reconozca
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ESTO ELIMINA EL ERROR DEL CERO EXTRA Y FORMATO LOCALIZADO: 
        # Forzamos a que Django NO use puntos de miles dentro del input al cargar para editar
        self.fields['costo_m2'].localize = False
        self.fields['costo_m2'].widget.is_localized = False
        
        # También aplicamos a margen por seguridad en la edición
        self.fields['margen_ganancia'].localize = False
        self.fields['margen_ganancia'].widget.is_localized = False

class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = ['familia', 'descripcion', 'costo_compra', 'margen_ganancia', 'precio_unitario']
        widgets = {
            'familia': forms.Select(attrs={'class': 'form-select bg-light border-0 rounded-pill px-3'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control bg-light border-0 rounded-3', 'rows': 3}),
            # CAMBIO AQUÍ TAMBIÉN PARA EVITAR ERRORES EN ARTÍCULOS
            'costo_compra': forms.TextInput(attrs={  # Cambiado a TextInput
                'class': 'form-control bg-light border-0 rounded-pill px-3',
            }),
            'margen_ganancia': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'placeholder': '%',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'precio_unitario': forms.TextInput(attrs={ # Cambiado a TextInput
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'readonly': 'readonly'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['precio_unitario'].widget.attrs['readonly'] = True
        # Desactivamos localización en los precios de artículos también
        self.fields['costo_compra'].localize = False
        self.fields['precio_unitario'].localize = False
        
class ProcesoForm(forms.ModelForm):
    class Meta:
        model = Proceso
        fields = [
            'cliente', 'responsable_diseno',   
            'responsable_taller',
            'familia',
            'reunion', 'pauta', 'enviado_correccion', 
            'correccion_1', 'correccion_2', 'correccion_3', 
            'aprobacion_final',
            # SECCIÓN TALLER
            'acrilico', 'sintra', 'ojetillo', 'ad_prom', 'ad_vehicular',
            'empavonado', 'microperf', 'sellado', 'tela_pvc',
            'impresion', 'corte', 'terminaciones'
        ]
        widgets = {
            'terminaciones': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'cliente': forms.Select(attrs={'class': 'form-select select-tech'}),
            'responsable_proyecto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Juan Pérez'}),
        }


class DisenoForm(forms.ModelForm):
    class Meta:
        model = Proceso
        fields = [
            'reunion', 'pauta', 'enviado_correccion', 
            'correccion_1', 'correccion_2', 'correccion_3', 
            'aprobacion_final'
        ]

class UsuarioForm(UserCreationForm):

    codigo_vendedor = forms.CharField(
        label="Código Vendedor", 
        max_length=10, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: VEND-001'})
    )

    email = forms.EmailField(label="Correo Electrónico", required=True)

    # 👇 NUEVO CAMPO
    tipo_usuario = forms.ChoiceField(
        label="Tipo de Usuario",
        choices=Perfil.TIPO_CHOICES,
        required=True
    )

    class Meta:
        model = User


        fields = ['codigo_vendedor', 'username', 'email', 'password1', 'password2', 'tipo_usuario']

        labels = {
            'username': 'Usuario',
            'password1': 'Contraseña',
            'password2': 'Confirmar Contraseña',
        }

        help_texts = {
            'username': '',
            'password1': '',
            'password2': '',
        }


class EditarUsuarioForm(forms.ModelForm):

    codigo_vendedor = forms.CharField(
        label="Código Vendedor",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-light border-0 rounded-pill px-3',
            'placeholder': 'Ej: VEND-001'
        })
    )
    
    tipo_usuario = forms.ChoiceField(
        label="Rol / Tipo de Usuario",
        choices=Perfil.TIPO_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select bg-light border-0 rounded-pill px-3'})
    )

    username = forms.CharField(
        label="Usuario",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3'})
    )
    
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3'})
    )

    # NUEVO: Campo de contraseña con tu estilo visual
    nueva_password = forms.CharField(
        label="Nueva Contraseña (Opcional)",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-light border-0 rounded-pill px-3',
            'placeholder': 'Dejar en blanco para mantener actual'
        }),
        help_text="Solo complete este campo si desea cambiar la clave del usuario."
    )

    class Meta:
        model = User
        fields = ['codigo_vendedor', 'username', 'email']

    def __init__(self, *args, **kwargs):
        super(EditarUsuarioForm, self).__init__(*args, **kwargs)
        # Cargar el rol inicial desde el perfil
        if self.instance and hasattr(self.instance, 'perfil'):
            self.fields['tipo_usuario'].initial = self.instance.perfil.tipo_usuario
            self.fields['codigo_vendedor'].initial = self.instance.perfil.codigo_vendedor

    def save(self, commit=True):
        # Obtenemos la instancia del usuario
        user = super().save(commit=False)
        
        # Lógica para la contraseña
        nueva_pwd = self.cleaned_data.get("nueva_password")
        if nueva_pwd:
            user.set_password(nueva_pwd)  # Importante: set_password hace el hash (encriptación)
            
        if commit:
            user.save()
        return user

class FacturaForm(forms.ModelForm):
    condicion_pago_display = forms.CharField(
        label="Condición de Pago (Cliente)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-light border-0 rounded-pill px-3',
            'readonly': 'readonly',
            'id': 'id_condicion_pago_display'
        })
    )
    def __init__(self, *args, **kwargs):
        super(FacturaForm, self).__init__(*args, **kwargs)
        # Quitamos la obligatoriedad estática para que el navegador no moleste
        self.fields['archivo_pdf'].required = False

    def clean_archivo_pdf(self):
        archivo = self.cleaned_data.get('archivo_pdf')
        
        # Si NO estamos editando (no hay instancia) y NO se subió archivo
        if not self.instance.pk and not archivo:
            raise forms.ValidationError("El archivo PDF es obligatorio para nuevos registros.")
        
        return archivo

    def clean_total_facturado(self):
        valor = self.cleaned_data.get('total_facturado')

        if isinstance(valor, str):
            valor = valor.replace(',', '.')

        return valor

    class Meta:
        model = Factura
        fields = [
            'n_factura', 'fecha_facturacion', 'cliente', 
            'total_facturado', 'estado_pago', 'valor_abonado', 'archivo_pdf'
        ]
        widgets = {
            'n_factura': forms.TextInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3'}),
            'fecha_facturacion': forms.DateInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3', 'type': 'date'}),
            'cliente': forms.Select(attrs={'class': 'form-select bg-light border-0 rounded-pill px-3'}),
            'total_facturado': forms.NumberInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3'}),
            'estado_pago': forms.Select(attrs={'class': 'form-select bg-light border-0 rounded-pill px-3'}),
            'valor_abonado': forms.NumberInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3'}),
            'archivo_pdf': forms.FileInput(attrs={'class': 'form-control bg-light border-0 rounded-pill px-3', 'accept': 'application/pdf'}),
        }

class TallerForm(forms.ModelForm):
    class Meta:
        model = Proceso
        fields = [
            'cliente', 
            'acrilico', 'sintra', 'ojetillo', 'ad_prom', 'ad_vehicular',
            'empavonado', 'microperf', 'sellado', 'tela_pvc',
            'impresion', 'corte', 'terminaciones',
            'aprobacion_taller'  # <--- AGREGADO AQUÍ
        ]
        widgets = {
            'terminaciones': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'cliente': forms.Select(attrs={'class': 'form-select select-tech'}),
        }
        labels = {
            'aprobacion_taller': 'APROBACIÓN FINAL TALLER (LISTO PARA ENTREGA)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Al igual que en Diseño, bloqueamos el cliente para que no se cambie por error en taller
        if self.instance and self.instance.pk:
            self.fields['cliente'].widget.attrs['disabled'] = True
            self.fields['cliente'].required = False



class CompraForm(forms.ModelForm):
    # --- CAMPOS ADICIONALES PARA LÓGICA DE VENCIMIENTO ---
    condicion_pago_display = forms.CharField(
        label="Condición de Pago (Proveedor)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-light border-0 rounded-pill px-3',
            'readonly': 'readonly',
            'id': 'id_condicion_pago_display_compra',
            'placeholder': 'Días de crédito'
        })
    )
    
    vencimiento_display = forms.CharField(
        label="Fecha Vencimiento Estimada",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-info bg-opacity-10 border-0 rounded-pill px-3',
            'readonly': 'readonly',
            'id': 'id_vencimiento_display_compra',
            'placeholder': 'Se calcula al elegir fecha'
        })
    )

    class Meta:
        model = Compra
        fields = [
            'n_factura', 'fecha_registro', 'proveedor', 
            'total_compra', 'estado_pago', 'valor_abonado', 'archivo_compra'
        ]
        widgets = {
            'n_factura': forms.TextInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'id': 'id_n_factura'
            }),
            'fecha_registro': forms.DateInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3', 
                'type': 'date',
                'id': 'id_fecha_registro'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select bg-light border-0 rounded-pill px-3',
                'id': 'id_proveedor'
            }),
            'total_compra': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'id': 'id_total_compra'
            }),
            'estado_pago': forms.Select(attrs={
                'class': 'form-select bg-light border-0 rounded-pill px-3',
                'id': 'id_estado_pago'
            }),
            'valor_abonado': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'id': 'id_valor_abonado'
            }),
            'archivo_compra': forms.FileInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3', 
                'accept': 'application/pdf,image/*',
                'id': 'id_archivo_compra'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(CompraForm, self).__init__(*args, **kwargs)
        # El archivo no es obligatorio en el HTML para permitir ediciones sin resubir
        self.fields['archivo_compra'].required = False

    def clean_archivo_compra(self):
        archivo = self.cleaned_data.get('archivo_compra')
        # Obligatorio solo si es un registro nuevo (no tiene Primary Key)
        if not self.instance.pk and not archivo:
            raise forms.ValidationError("El archivo de respaldo es obligatorio para nuevos registros.")
        return archivo