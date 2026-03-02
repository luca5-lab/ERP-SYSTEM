from django import forms
from .models import Cliente, Proveedor
import re


def validar_rut_real(rut):

    rut = rut.replace(".", "").replace("-", "")

    cuerpo = rut[:-1]
    dv = rut[-1].upper()

    suma = 0
    multiplo = 2

    for d in reversed(cuerpo):
        suma += int(d) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1

    resto = suma % 11
    dv_calc = 11 - resto

    if dv_calc == 11:
        dv_calc = "0"
    elif dv_calc == 10:
        dv_calc = "K"
    else:
        dv_calc = str(dv_calc)

    return dv == dv_calc


class ClienteForm(forms.ModelForm):

    class Meta:
        model = Cliente

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

        rut = self.cleaned_data['rut']

        # Validar formato
        patron = r'^\d{1,3}(\.\d{3})*-[0-9Kk]$'

        if not re.match(patron, rut):
            raise forms.ValidationError(
                "Ingrese el RUT en formato 12.345.678-9"
            )

        # Validar RUT real
        if not validar_rut_real(rut):
            raise forms.ValidationError("RUT inválido")

        return rut.upper()


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

        rut = self.cleaned_data['rut']

        patron = r'^\d{1,3}(\.\d{3})*-[0-9Kk]$'

        if not re.match(patron, rut):
            raise forms.ValidationError(
                "Ingrese el RUT en formato 12.345.678-9"
            )

        if not validar_rut_real(rut):
            raise forms.ValidationError("RUT inválido")

        return rut.upper()