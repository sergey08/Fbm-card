"""Adaptador Afición FBM: bloqueo explícito hasta validar acceso invitado.

La app es la única fuente prevista. Este adaptador no inventa rutas,
parámetros de sesión, credenciales ni datos deportivos.
"""


class FBMAccessNotValidated(RuntimeError):
    """Aún no hay un acceso invitado autorizado y reproducible."""


class AficionFBMAdapter:
    """Interfaz de consulta para el gestor FBM, pendiente de implementación."""

    async def query(self, kind: str, identifiers: dict) -> dict:
        """No enviar tráfico hasta conocer el protocolo real y sus condiciones."""
        raise FBMAccessNotValidated(
            "Pendiente validar el acceso oficial invitado a Afición FBM "
            "y las condiciones de uso de su API"
        )
