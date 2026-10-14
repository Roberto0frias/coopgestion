"""Formularios del núcleo: parámetros del sistema."""

from __future__ import annotations

from django import forms

from .models import ParametroSistema


class ParametroSistemaForm(forms.ModelForm):
    """Edición de un parámetro del sistema con validación de tipo."""

    class Meta:
        model = ParametroSistema
        fields = ["valor", "descripcion", "editable"]
        widgets = {
            "valor": forms.TextInput(attrs={"class": "campo", "autocomplete": "off"}),
            "descripcion": forms.TextInput(attrs={"class": "campo"}),
        }
        help_texts = {
            "valor": "Escriba el valor según el tipo declarado del parámetro.",
        }

    def clean_valor(self) -> str:
        """Valida el valor contra el tipo declarado del parámetro."""
        valor = self.cleaned_data["valor"]
        if self.instance.pk:
            self.instance.valor = valor
            self.instance.clean()
        return valor
