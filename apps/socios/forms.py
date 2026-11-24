from django import forms

from .models import Socio


class SocioForm(forms.ModelForm):
    class Meta:
        model = Socio
        fields = (
            "tipo",
            "es_voluntaria_proyecto",
            "proyecto",
            "nombres",
            "apellidos",
            "cedula",
            "fecha_nacimiento",
            "estado_civil",
            "ocupacion",
            "ingresos_mensuales",
            "direccion",
            "telefono",
            "email",
            "es_pep",
        )
        widgets = {  # noqa: RUF012
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "ingresos_mensuales": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "es_voluntaria_proyecto": forms.CheckboxInput(),
            "es_pep": forms.CheckboxInput(),
        }

    def clean_cedula(self) -> str:
        return "".join(self.cleaned_data["cedula"].upper().split()).replace("-", "")


class RechazoAdmisionForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo del rechazo",
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        max_length=1000,
    )
