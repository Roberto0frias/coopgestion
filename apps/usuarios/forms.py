"""Formularios de usuarios: autenticación, alta, edición y contraseñas."""

from __future__ import annotations

from typing import Any

from apps.core.exceptions import ErrorDeNegocio
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import Rol, Usuario
from .services import crear_usuario

ESTILO_CAMPO = {"class": "campo"}


class FormularioInicioSesion(AuthenticationForm):
    """Inicio de sesión con bloqueo por intentos fallidos y registro en la bitácora.

    No se usa ``authenticate()`` de Django ni ``AuthenticationForm.clean()``: toda la
    validación pasa por :func:`apps.usuarios.services.autenticar`, que aplica la política
    de intentos, bloqueo y registro. Si se llamara al método padre, Django autenticaría
    por su cuenta y saltaría por completo esa política.
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Usuario o contraseña incorrectos.",
    }

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={**ESTILO_CAMPO, "autofocus": True, "autocomplete": "username"}
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={**ESTILO_CAMPO, "autocomplete": "current-password"}),
    )

    def clean(self) -> dict[str, Any]:
        from .services import autenticar

        datos = self.cleaned_data
        username = datos.get("username")
        password = datos.get("password")
        if username and password:
            try:
                self.user_cache = autenticar(username, password, request=self.request)
            except ErrorDeNegocio as exc:
                raise forms.ValidationError(str(exc), code="credenciales") from exc
        return datos


class UsuarioCrearForm(forms.ModelForm):
    """Alta de un usuario interno. La contraseña se valida contra la política del sistema."""

    password1 = forms.CharField(
        label="Contraseña inicial",
        widget=forms.PasswordInput(attrs={**ESTILO_CAMPO, "autocomplete": "new-password"}),
        help_text="Mínimo 12 caracteres. El usuario deberá cambiarla al entrar.",
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={**ESTILO_CAMPO, "autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = [
            "username",
            "email",
            "nombres",
            "apellidos",
            "cedula",
            "telefono",
            "rol",
            "sucursal",
        ]
        widgets = {
            "username": forms.TextInput(attrs=ESTILO_CAMPO),
            "email": forms.EmailInput(attrs=ESTILO_CAMPO),
            "nombres": forms.TextInput(attrs=ESTILO_CAMPO),
            "apellidos": forms.TextInput(attrs=ESTILO_CAMPO),
            "cedula": forms.TextInput(attrs={**ESTILO_CAMPO, "placeholder": "00000000000"}),
            "telefono": forms.TextInput(attrs={**ESTILO_CAMPO, "placeholder": "809-000-0000"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["rol"].queryset = Rol.objects.filter(activo=True)
        self.fields["rol"].widget.attrs.update(ESTILO_CAMPO)
        self.fields["sucursal"].widget.attrs.update(ESTILO_CAMPO)
        self.fields["rol"].empty_label = "Seleccione un rol"

    def clean(self) -> dict[str, Any]:
        datos = super().clean()
        clave1 = datos.get("password1")
        clave2 = datos.get("password2")
        if clave1 and clave2 and clave1 != clave2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return datos

    def save(self, commit: bool = True) -> Usuario:
        """Crea el usuario a través del servicio, para que quede auditado.

        ``commit`` se acepta por compatibilidad con la firma de ``ModelForm``; el servicio
        siempre confirma la transacción.
        """
        datos = self.cleaned_data
        return crear_usuario(
            username=datos["username"],
            email=datos["email"],
            nombres=datos["nombres"],
            apellidos=datos["apellidos"],
            rol=datos["rol"],
            password=datos["password1"],
            sucursal=datos.get("sucursal"),
            cedula=datos.get("cedula") or None,
            telefono=datos.get("telefono", ""),
            debe_cambiar_password=True,
        )


class UsuarioEditarForm(forms.ModelForm):
    """Edición de los datos de un usuario (sin tocar la contraseña)."""

    class Meta:
        model = Usuario
        fields = [
            "email",
            "nombres",
            "apellidos",
            "cedula",
            "telefono",
            "rol",
            "sucursal",
            "is_active",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["rol"].queryset = Rol.objects.filter(activo=True)
        for nombre, campo in self.fields.items():
            if nombre != "is_active":
                campo.widget.attrs.update(ESTILO_CAMPO)
        self.fields["is_active"].label = "Usuario activo"
        self.fields["is_active"].help_text = (
            "Desactive en lugar de eliminar: el historial debe conservarse."
        )


class PerfilForm(forms.ModelForm):
    """Datos que el propio usuario puede actualizar."""

    class Meta:
        model = Usuario
        fields = ["nombres", "apellidos", "email", "telefono"]
        widgets = {
            "nombres": forms.TextInput(attrs=ESTILO_CAMPO),
            "apellidos": forms.TextInput(attrs=ESTILO_CAMPO),
            "email": forms.EmailInput(attrs=ESTILO_CAMPO),
            "telefono": forms.TextInput(attrs=ESTILO_CAMPO),
        }


class FormularioCambioPassword(PasswordChangeForm):
    """Cambio de contraseña por el propio usuario."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.update(ESTILO_CAMPO)


class RestablecerPasswordForm(forms.Form):
    """Restablecimiento de la contraseña de otro usuario por un administrador."""

    password1 = forms.CharField(
        label="Contraseña temporal",
        widget=forms.PasswordInput(attrs={**ESTILO_CAMPO, "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña temporal",
        widget=forms.PasswordInput(attrs={**ESTILO_CAMPO, "autocomplete": "new-password"}),
    )

    def clean(self) -> dict[str, Any]:
        datos = super().clean()
        if datos.get("password1") and datos["password1"] != datos.get("password2"):
            self.add_error("password2", "Las contraseñas no coinciden.")
        return datos


__all__ = [
    "FormularioCambioPassword",
    "FormularioInicioSesion",
    "PerfilForm",
    "RestablecerPasswordForm",
    "UsuarioCrearForm",
    "UsuarioEditarForm",
]
