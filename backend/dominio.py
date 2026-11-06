"""Reglas de negocio puras (Capa 2). Sin FastAPI ni SQLite.

Traducción a Python de las funciones del bloque `domain/` de index.html.
Toda función que depende del tiempo recibe `ahora` como parámetro (spec D-09).
Fuente: spec.md RN-01 (INV-01), RN-02 (INV-02), RN-03, RN-04 y RN-06.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# --- Configuración (spec RN-01, RN-04 y §1.4) -------------------------------------------------
CANCELLATION_WINDOW_HOURS: int = 2
MIN_LEAD_HOURS: int = 1
HORIZON_DAYS: int = 60
GRID_MIN: int = 15
ZONA_HORARIA: ZoneInfo = ZoneInfo(os.environ.get("ZONA_HORARIA", "America/Argentina/Buenos_Aires"))

FORMATO_UTC = "%Y-%m-%dT%H:%M:%SZ"

# --- Catálogo de errores de dominio (spec §7) -------------------------------------------------
HTTP_POR_CODIGO: dict[str, int] = {
    "SLOT_UNAVAILABLE": 409,
    "CANCELLATION_WINDOW_EXPIRED": 409,
    "INVALID_CONTACT": 422,
    "EMAIL_NOT_VERIFIED": 403,
    "INVALID_TIME_RANGE": 422,
    "INVALID_STATE_TRANSITION": 409,
    "SERVICE_HAS_ACTIVE_BOOKINGS": 409,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
}


class ErrorDominio(Exception):
    """Violación de una regla del spec. `codigo` pertenece al catálogo de spec §7."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.http = HTTP_POR_CODIGO[codigo]


# --- Tiempo -----------------------------------------------------------------------------------
def a_utc(valor: datetime) -> datetime:
    """Convierte un datetime con zona horaria a UTC. Un datetime sin zona es un error de programación."""
    if valor.tzinfo is None:
        raise ValueError("Se requiere un datetime con zona horaria")
    return valor.astimezone(timezone.utc)


def texto_utc(valor: datetime) -> str:
    """Formato de almacenamiento y de respuesta: ISO 8601 en UTC con sufijo Z (spec §11.2)."""
    return a_utc(valor).strftime(FORMATO_UTC)


def desde_texto(valor: str) -> datetime:
    return datetime.strptime(valor, FORMATO_UTC).replace(tzinfo=timezone.utc)


def overlaps(a_inicio: datetime, a_fin: datetime, b_inicio: datetime, b_fin: datetime) -> bool:
    """RN-02: intervalos semiabiertos [inicio, fin). Los contiguos (a_fin == b_inicio) NO se solapan."""
    return a_inicio < b_fin and b_inicio < a_fin


# --- RN-01 / INV-01: ventana de cancelación ---------------------------------------------------
def cliente_puede_cancelar(inicio: datetime, ahora: datetime) -> bool:
    """El cliente puede cancelar si faltan al menos 2 h. El límite exacto de 2 h se permite."""
    return inicio - ahora >= timedelta(hours=CANCELLATION_WINDOW_HOURS)


# --- RN-03: contacto --------------------------------------------------------------------------
_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


@dataclass(frozen=True)
class Contacto:
    nombre_completo: str
    email: str
    telefono: str
    email_verificado: bool


def normalizar_contacto(c: Contacto) -> Contacto:
    """Trim, email en minúsculas y teléfono sin separadores (spec RN-03)."""
    telefono = re.sub(r"[\s\-().]", "", c.telefono.strip())
    return Contacto(c.nombre_completo.strip(), c.email.strip().lower(), telefono, c.email_verificado)


def validar_contacto(contacto: Contacto) -> None:
    """RN-03. Lanza INVALID_CONTACT (422) o EMAIL_NOT_VERIFIED (403)."""
    c = normalizar_contacto(contacto)
    if not 2 <= len(c.nombre_completo) <= 100:
        raise ErrorDominio("INVALID_CONTACT", "El nombre completo debe tener entre 2 y 100 caracteres.")
    if not _EMAIL.match(c.email):
        raise ErrorDominio("INVALID_CONTACT", "El email no es válido.")
    if not _E164.match(c.telefono):
        raise ErrorDominio("INVALID_CONTACT", "El teléfono debe estar en formato internacional (E.164).")
    if not c.email_verificado:
        raise ErrorDominio("EMAIL_NOT_VERIFIED", "Tenés que verificar tu email antes de reservar.")


# --- RN-04: integridad temporal ---------------------------------------------------------------
def validar_tiempo(inicio: datetime, ahora: datetime) -> None:
    """RN-04. Lanza INVALID_TIME_RANGE (422)."""
    if inicio.second != 0 or inicio.microsecond != 0 or inicio.minute % GRID_MIN != 0:
        raise ErrorDominio("INVALID_TIME_RANGE", f"El inicio debe estar alineado a la grilla de {GRID_MIN} minutos.")
    if inicio < ahora + timedelta(hours=MIN_LEAD_HOURS):
        raise ErrorDominio("INVALID_TIME_RANGE", f"El turno requiere una antelación mínima de {MIN_LEAD_HOURS} hora.")
    if inicio > ahora + timedelta(days=HORIZON_DAYS):
        raise ErrorDominio("INVALID_TIME_RANGE", f"No se puede reservar a más de {HORIZON_DAYS} días.")


def calcular_fin(inicio: datetime, duracion_min: int) -> datetime:
    """RN-04: `fin` lo calcula el servidor; el cliente no lo envía."""
    return inicio + timedelta(minutes=duracion_min)


# --- RN-02: horario laboral -------------------------------------------------------------------
def dentro_de_horario_laboral(inicio: datetime, fin: datetime, tramos: list[tuple[int, str, str]]) -> bool:
    """`tramos` son (dia_semana, 'HH:MM', 'HH:MM') del profesional, con 0 = domingo.

    El turno debe caber completo en un tramo del mismo día, en hora local de la zona de operación.
    """
    ini_local = inicio.astimezone(ZONA_HORARIA)
    fin_local = fin.astimezone(ZONA_HORARIA)
    if ini_local.date() != fin_local.date():
        return False
    dia = (ini_local.weekday() + 1) % 7  # Python: lunes = 0 → convención del spec: domingo = 0
    desde, hasta = ini_local.strftime("%H:%M"), fin_local.strftime("%H:%M")
    return any(d == dia and h_ini <= desde and hasta <= h_fin for d, h_ini, h_fin in tramos)


# --- RN-06: ciclo de vida ---------------------------------------------------------------------
ESTADOS_TERMINALES = frozenset({"CANCELADO", "COMPLETADO", "AUSENTE"})


def validar_cancelable(estado: str) -> None:
    """Solo un turno CONFIRMADO puede cancelarse; los estados terminales no admiten transiciones."""
    if estado != "CONFIRMADO":
        raise ErrorDominio("INVALID_STATE_TRANSITION", f"Un turno {estado} no puede cancelarse.")
