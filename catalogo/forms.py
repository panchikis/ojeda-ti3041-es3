from django import forms

from .models import ConsultaCliente


class ConsultaClienteForm(forms.ModelForm):
    class Meta:
        model = ConsultaCliente
        fields = ["nombre", "correo", "mensaje", "producto"]
        labels = {
            "nombre": "Tu nombre",
            "correo": "Tu correo",
            "mensaje": "Tu consulta",
            "producto": "Producto de interés (opcional)",
        }
        widgets = {
            "mensaje": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 letras.")
        return nombre

    def clean_mensaje(self):
        mensaje = self.cleaned_data["mensaje"].strip()
        if len(mensaje) < 10:
            raise forms.ValidationError(
                "Cuéntanos un poco más: escribe al menos 10 caracteres."
            )
        return mensaje
