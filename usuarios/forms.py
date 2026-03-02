from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil, Proceso, Articulo, Servicio 
from .models import Proceso



class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['familia', 'descripcion', 'costo_m2']
        widgets = {
            'familia': forms.Select(attrs={'class': 'form-select bg-light border-0 rounded-pill px-3'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control bg-light border-0 rounded-3', 'rows': 3}),
            # CAMBIO CLAVE: Usamos NumberInput en lugar de TextInput
            'costo_m2': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ESTO ELIMINA EL ERROR DEL CERO EXTRA: 
        # Forzamos a que Django NO use puntos de miles dentro del input al cargar para editar
        self.fields['costo_m2'].localize = False
        self.fields['costo_m2'].widget.is_localized = False

class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = ['familia', 'descripcion', 'costo_compra', 'margen_ganancia', 'precio_unitario']
        widgets = {
            'familia': forms.Select(attrs={'class': 'form-select bg-light border-0 rounded-pill px-3'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control bg-light border-0 rounded-3', 'rows': 3}),
            # CAMBIO AQUÍ TAMBIÉN PARA EVITAR ERRORES EN ARTÍCULOS
            'costo_compra': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'step': '0.01'
            }),
            'margen_ganancia': forms.NumberInput(attrs={
                'class': 'form-control bg-light border-0 rounded-pill px-3',
                'placeholder': '%',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'precio_unitario': forms.NumberInput(attrs={
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
            'cliente', 'responsable_proyecto',
            # SECCIÓN DISEÑO
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
            'cliente', 'responsable_proyecto',
            'reunion', 'pauta', 'enviado_correccion', 
            'correccion_1', 'correccion_2', 'correccion_3', 
            'aprobacion_final'
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'responsable_proyecto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del encargado'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que el cliente no sea obligatorio al editar para que no de error si no está en el HTML
        if self.instance and self.instance.pk:
            self.fields['cliente'].required = False
            # Opcional: Bloquearlo para que el diseñador no cambie el cliente de una orden
            self.fields['cliente'].widget.attrs['disabled'] = True

class UsuarioForm(UserCreationForm):

    email = forms.EmailField(label="Correo Electrónico", required=True)

    # 👇 NUEVO CAMPO
    tipo_usuario = forms.ChoiceField(
        label="Tipo de Usuario",
        choices=Perfil.TIPO_CHOICES,
        required=True
    )

    class Meta:
        model = User


        fields = ['username', 'email', 'password1', 'password2', 'tipo_usuario']

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

    username = forms.CharField(
        label="Usuario",
        max_length=150,
        help_text="Solo letras, números y @/./+/-/_",
    )

    class Meta:
        model = User
        fields = ['username', 'email']

# forms.py

# forms.py

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