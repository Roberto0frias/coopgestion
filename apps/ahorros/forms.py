from django import forms

from apps.socios.models import Socio

from .models import CuentaAhorro, ProductoAhorro


class ProductoAhorroForm(forms.ModelForm):
    class Meta:
        model = ProductoAhorro
        fields = ("nombre", "tipo_socio", "tasa_anual", "base_dias", "activa")


class AperturaCuentaForm(forms.ModelForm):
    class Meta:
        model = CuentaAhorro
        fields = ("socio", "producto")

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)
        self.fields["socio"].queryset = Socio.objects.filter(estado=Socio.Estado.ACTIVO)
        self.fields["producto"].queryset = ProductoAhorro.objects.filter(activa=True)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field-control"

    def clean(self):
        cleaned = super().clean()
        cuenta = CuentaAhorro(**cleaned, abierta_por=self.usuario)
        if cuenta.socio_id and cuenta.producto_id:
            cuenta.clean()
            if CuentaAhorro.objects.filter(socio=cuenta.socio, producto=cuenta.producto).exists():
                self.add_error("producto", "El socio ya tiene una cuenta de este producto.")
        return cleaned
