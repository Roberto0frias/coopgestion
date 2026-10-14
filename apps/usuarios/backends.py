"""Backend de autenticación que obtiene los permisos del rol del usuario.

Django, por omisión, resuelve ``has_perm()`` consultando ``user.user_permissions`` y los
grupos del usuario. En COOPGESTION los permisos provienen exclusivamente del **rol**, así
que se sustituye esa resolución. Sin este backend, anular ``get_user_permissions()`` en el
modelo no tendría ningún efecto sobre ``has_perm()``.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class BackendRoles(ModelBackend):
    """Resuelve los permisos a partir del rol asignado al usuario."""

    def get_user_permissions(self, user_obj: Any, obj: Any = None) -> set[str]:
        """Permisos que otorga el rol del usuario."""
        if not getattr(user_obj, "is_active", False) or obj is not None:
            return set()
        if user_obj.is_anonymous:
            return set()
        return user_obj.get_user_permissions(obj)

    def get_group_permissions(self, user_obj: Any, obj: Any = None) -> set[str]:
        """No se usan los grupos de Django: la fuente de verdad es el rol."""
        return set()

    def get_all_permissions(self, user_obj: Any, obj: Any = None) -> set[str]:
        """Todos los permisos efectivos del usuario."""
        if not getattr(user_obj, "is_active", False) or obj is not None:
            return set()
        if user_obj.is_anonymous:
            return set()
        if getattr(user_obj, "is_superuser", False):
            return {
                f"{etiqueta}.{nombre}"
                for etiqueta, nombre in Permission.objects.values_list(
                    "content_type__app_label", "codename"
                )
            }
        return self.get_user_permissions(user_obj, obj) | self.get_group_permissions(user_obj, obj)

    def has_perm(self, user_obj: Any, perm: str, obj: Any = None) -> bool:
        """Comprueba un permiso concreto, respetando el estado de la cuenta."""
        if not getattr(user_obj, "is_active", False) or user_obj.is_anonymous:
            return False
        if getattr(user_obj, "is_superuser", False):
            return True
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj: Any, app_label: str) -> bool:
        """Indica si el usuario tiene algún permiso dentro de una aplicación."""
        if not getattr(user_obj, "is_active", False) or user_obj.is_anonymous:
            return False
        if getattr(user_obj, "is_superuser", False):
            return True
        prefijo = f"{app_label}."
        return any(permiso.startswith(prefijo) for permiso in self.get_all_permissions(user_obj))
