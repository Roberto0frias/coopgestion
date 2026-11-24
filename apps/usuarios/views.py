from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from apps.auditoria.services import registrar_evento


class CambioContrasenaView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.debe_cambiar_password = False
        self.request.user.save(update_fields=["debe_cambiar_password"])
        registrar_evento(
            usuario=self.request.user,
            accion="CONTRASENA_CAMBIADA",
            request=self.request,
            objeto=self.request.user,
        )
        return response
