from django import forms
from django.forms import formset_factory

from .models import CuentaContable


class AsientoBorradorForm(forms.Form):
    fecha = forms.DateField(
        label="Fecha contable",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    descripcion = forms.CharField(label="Descripción", max_length=255)


class LineaAsientoForm(forms.Form):
    cuenta = forms.ModelChoiceField(
        label="Cuenta",
        queryset=CuentaContable.objects.none(),
        empty_label="Selecciona una cuenta",
    )
    descripcion = forms.CharField(label="Detalle", max_length=180, required=False)
    debito = forms.DecimalField(label="Débito", min_value=0, decimal_places=2, required=False)
    credito = forms.DecimalField(label="Crédito", min_value=0, decimal_places=2, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].queryset = CuentaContable.objects.filter(
            activa=True, permite_movimiento=True
        ).order_by("codigo")

    def clean(self):
        cleaned_data = super().clean()
        cuenta = cleaned_data.get("cuenta")
        debito = cleaned_data.get("debito") or 0
        credito = cleaned_data.get("credito") or 0
        detalle_vacio = not cuenta and debito == 0 and credito == 0
        if detalle_vacio:
            return cleaned_data
        if not cuenta:
            self.add_error("cuenta", "Selecciona la cuenta contable.")
        if (debito > 0) == (credito > 0):
            self.add_error(None, "Indica un monto en débito o crédito, no en ambos.")
        return cleaned_data


LineaAsientoFormSet = formset_factory(
    LineaAsientoForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=False,
)
