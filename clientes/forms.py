from django import forms
from .models import Cliente, Proveedor
import re


from django import forms
from .models import Cliente, Proveedor
import re

def validar_rut_real(rut):
    rut = rut.replace(".", "").replace("-", "")
    if len(rut) < 2: return False
    
    cuerpo = rut[:-1]
    dv = rut[-1].upper()
    suma = 0
    multiplo = 2
    for d in reversed(cuerpo):
        suma += int(d) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    resto = suma % 11
    dv_calc = 11 - resto
    if dv_calc == 11: dv_calc = "0"
    elif dv_calc == 10: dv_calc = "K"
    else: dv_calc = str(dv_calc)
    return dv == dv_calc

def formatear_rut(rut_sucio):
    # Extraer solo números y la letra K
    rut_limpio = re.sub(r'[^0-9Kk]', '', rut_sucio)
    if len(rut_limpio) < 2: return rut_limpio.upper()

    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1].upper()
    
    # Poner los puntos
    cuerpo_con_puntos = ""
    i = len(cuerpo) - 1
    j = 1
    while i >= 0:
        cuerpo_con_puntos = cuerpo[i] + cuerpo_con_puntos
        if j % 3 == 0 and i != 0:
            cuerpo_con_puntos = "." + cuerpo_con_puntos
        i -= 1
        j += 1
    return f"{cuerpo_con_puntos}-{dv}"

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['razon_social', 'giro', 'rut', 'direccion', 'correo', 'telefono', 'condiciones_pago']
        labels = {
            'razon_social': 'Razón Social',
            'giro': 'Giro',
            'rut': 'RUT',
            'direccion': 'Dirección',
            'correo': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'condiciones_pago': 'Condiciones de Pago',
        }
        widgets = {
            'rut': forms.TextInput(attrs={
                'placeholder': '12.345.678-9 o 12345678-9',
                'oninput': 'formatearRut(this)',
                'maxlength': '12'
            })
        }

    def clean_rut(self):
        rut_raw = self.cleaned_data['rut']

        # 1. Limpieza extrema: Dejar solo números y la K
        # Esto elimina letras, espacios o símbolos raros que el usuario pueda meter
        rut_limpio = re.sub(r'[^0-9Kk]', '', rut_raw)

        # 2. Validación de largo mínimo (Un RUT no puede tener menos de 8 caracteres: 1234567-8)
        if len(rut_limpio) < 8:
            raise forms.ValidationError("El RUT ingresado es demasiado corto o contiene caracteres no permitidos.")

        # 3. Validar si el dígito verificador es matemáticamente correcto
        if not validar_rut_real(rut_limpio):
            raise forms.ValidationError("RUT inválido. Verifique el número y el dígito verificador.")

        # 4. Si pasó todo lo anterior, lo formateamos para que se guarde con puntos
        return formatear_rut(rut_limpio)


class ProveedorForm(forms.ModelForm):

    class Meta:
        model = Proveedor

        fields = [
            'razon_social',
            'giro',
            'rut',
            'direccion',
            'correo',
            'telefono',
            'condiciones_pago',
        ]

        labels = {
            'razon_social': 'Razón Social',
            'giro': 'Giro',
            'rut': 'RUT',
            'direccion': 'Dirección',
            'correo': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'condiciones_pago': 'Condiciones de Pago',
        }

        widgets = {
            'rut': forms.TextInput(attrs={
                'placeholder': '12.345.678-9',
                'oninput': 'formatearRut(this)',
                'maxlength': '12'
            })
        }


    def clean_rut(self):
        rut_raw = self.cleaned_data['rut']

        # 1. Limpieza extrema: Dejar solo números y la K
        # Esto elimina letras, espacios o símbolos raros que el usuario pueda meter
        rut_limpio = re.sub(r'[^0-9Kk]', '', rut_raw)

        # 2. Validación de largo mínimo (Un RUT no puede tener menos de 8 caracteres: 1234567-8)
        if len(rut_limpio) < 8:
            raise forms.ValidationError("El RUT ingresado es demasiado corto o contiene caracteres no permitidos.")

        # 3. Validar si el dígito verificador es matemáticamente correcto
        if not validar_rut_real(rut_limpio):
            raise forms.ValidationError("RUT inválido. Verifique el número y el dígito verificador.")

        # 4. Si pasó todo lo anterior, lo formateamos para que se guarde con puntos
        return formatear_rut(rut_limpio)