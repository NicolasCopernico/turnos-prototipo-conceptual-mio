"""Carga inicial de datos de ejemplo (plan §3.3). Mismos datos mock que index.html, con `id` fijos.

Solo inserta atributos que existen en spec §4.1. Las fechas son relativas a "hoy", así que la
carga no envejece. Uso:

    python seed.py              # crea el esquema y carga los datos si la base está vacía
    python seed.py --reiniciar  # borra turnos.db y la vuelve a crear con los datos iniciales
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone

import db
from dominio import ZONA_HORARIA, texto_utc

# --- Identificadores fijos (el frontend los usa en su catálogo mock, spec D-08) ---------------
def _id(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012x}"


ADMIN = _id(0x01)
P1, P2, P3 = _id(0x11), _id(0x12), _id(0x13)
C1, C2, C3 = _id(0x21), _id(0x22), _id(0x23)
S1, S2, S3, S4, S5, S6 = (_id(0x30 + i) for i in range(1, 7))

# El hash no es verificable: el inicio de sesión (F-01) está fuera de la Fase 2 (spec D-06).
HASH_NO_VERIFICABLE = "!"

# (id, email, verificado, nombre, teléfono, rol)
USUARIOS = [
    (ADMIN, "admin@turnospro.test", 1, "Admin General", "+5491100000000", "ADMIN"),
    (P1, "ana@turnospro.test", 1, "Dra. Ana Martínez", "+5491100000001", "PROFESIONAL"),
    (P2, "bruno@turnospro.test", 1, "Dr. Bruno Salas", "+5491100000002", "PROFESIONAL"),
    (P3, "carla@turnospro.test", 1, "Lic. Carla Ibáñez", "+5491100000003", "PROFESIONAL"),
    (C1, "lucia@mail.test", 1, "Lucía Fernández", "+5491155550101", "CLIENTE"),
    (C2, "martin@mail.test", 0, "Martín Gómez", "+5491155550102", "CLIENTE"),  # email sin verificar
    (C3, "sofia@mail.test", 1, "Sofía Ruiz", "+5491155550103", "CLIENTE"),
]

# (id, profesional, nombre, descripción, duración, precio)
SERVICIOS = [
    (S1, P1, "Consulta general", "Evaluación clínica y orientación.", 30, 18000),
    (S2, P1, "Control anual", "Chequeo completo con estudios básicos.", 60, 32000),
    (S3, P2, "Sesión de terapia", "Sesión individual.", 45, 25000),
    (S4, P2, "Evaluación inicial", "Primera entrevista y plan de trabajo.", 60, 30000),
    (S5, P3, "Asesoría nutricional", "Seguimiento y ajustes.", 30, 15000),
    (S6, P3, "Plan alimentario", "Diseño de plan personalizado.", 45, 22000),
]
DURACION = {s[0]: s[4] for s in SERVICIOS}
PROFESIONAL_DE = {s[0]: s[1] for s in SERVICIOS}

# Lunes a viernes (dia_semana 1 a 5; 0 = domingo), hora local.
HORARIOS = {
    P1: [("09:00", "13:00"), ("14:00", "18:00")],
    P2: [("10:00", "14:00"), ("15:00", "19:00")],
    P3: [("09:00", "13:00")],
}


def _hoy_local(ahora: datetime) -> date:
    return ahora.astimezone(ZONA_HORARIA).date()


def _es_habil(d: date) -> bool:
    return d.weekday() < 5


def _dia_habil(base: date, n: int) -> date:
    """n-ésimo día hábil a partir de `base`: n > 0 hacia adelante, n < 0 hacia atrás (excluye `base`)."""
    paso = 1 if n > 0 else -1
    d = base
    for _ in range(abs(n)):
        d += timedelta(days=paso)
        while not _es_habil(d):
            d += timedelta(days=paso)
    return d


def _local_a_utc(d: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(d, time(hora, minuto), tzinfo=ZONA_HORARIA).astimezone(timezone.utc)


def cargar_datos_iniciales(conn: sqlite3.Connection, ahora: datetime) -> None:
    """Inserta los datos de ejemplo en una sola transacción (INV-03)."""
    hoy = _hoy_local(ahora)
    creado = texto_utc(ahora - timedelta(days=5))
    ahora_txt = texto_utc(ahora)

    # (id, cliente, servicio, inicio UTC, estado, motivo, cancelado_por)
    turnos: list[tuple[str, str, str, datetime, str, str | None, str | None]] = []

    def t(n: int, cliente: str, servicio: str, inicio: datetime, estado: str,
          motivo: str | None = None, cancelado_por: str | None = None) -> None:
        turnos.append((_id(0x100 + n), cliente, servicio, inicio, estado, motivo, cancelado_por))

    # Historial (días hábiles anteriores): completados, ausente y cancelados.
    t(1, C1, S1, _local_a_utc(_dia_habil(hoy, -3), 9), "COMPLETADO")
    t(2, C3, S2, _local_a_utc(_dia_habil(hoy, -3), 10), "COMPLETADO")
    t(3, C1, S3, _local_a_utc(_dia_habil(hoy, -2), 10), "COMPLETADO")
    t(4, C3, S5, _local_a_utc(_dia_habil(hoy, -2), 11), "AUSENTE")
    t(5, C2, S1, _local_a_utc(_dia_habil(hoy, -1), 9, 30), "COMPLETADO")
    t(6, C1, S4, _local_a_utc(_dia_habil(hoy, -1), 15), "CANCELADO", None, C1)
    t(7, C3, S6, _local_a_utc(_dia_habil(hoy, -1), 10), "CANCELADO", "Imprevisto médico", P3)

    # Para probar INV-01 sin esperar: uno dentro de la ventana (1 h 59 min) y otro fuera (3 h).
    # Se cargan sin alinear a la grilla; la alineación (RN-04) se exige al CREAR por la API.
    ahora_min = ahora.replace(second=0, microsecond=0)
    t(8, C1, S5, ahora_min + timedelta(hours=1, minutes=59), "CONFIRMADO")
    t(9, C3, S5, ahora_min + timedelta(hours=3), "CONFIRMADO")

    # Próximos días hábiles (solo P1 y P2, para no chocar con los dos turnos relativos de P3).
    d1, d2, d3 = (_dia_habil(hoy, n) for n in (1, 2, 3))
    t(10, C2, S3, _local_a_utc(d1, 11), "CONFIRMADO")
    t(11, C1, S2, _local_a_utc(d1, 15), "CONFIRMADO")
    t(12, C3, S1, _local_a_utc(d1, 10), "CONFIRMADO")
    t(13, C1, S4, _local_a_utc(d2, 11), "CONFIRMADO")
    t(14, C2, S3, _local_a_utc(d2, 15), "CONFIRMADO")
    t(15, C1, S2, _local_a_utc(d3, 15, 30), "CONFIRMADO")

    bloqueos = [
        (_id(0x201), P1, _local_a_utc(d2, 12), _local_a_utc(d2, 13), "Trámite personal"),
        (_id(0x202), P2, _local_a_utc(d3, 10), _local_a_utc(d3, 19), "Capacitación"),
    ]

    with db.transaccion(conn):
        conn.executemany(
            "INSERT INTO usuario (id, email, email_verificado, password_hash, nombre_completo, telefono, rol, activo, creado_en)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            [(i, e, v, HASH_NO_VERIFICABLE, n, tel, r, creado) for i, e, v, n, tel, r in USUARIOS],
        )
        conn.executemany(
            "INSERT INTO servicio (id, profesional_id, nombre, descripcion, duracion_min, precio_referencia, activo)"
            " VALUES (?, ?, ?, ?, ?, ?, 1)",
            SERVICIOS,
        )
        for prof, tramos in HORARIOS.items():
            for dia in range(1, 6):
                for h_ini, h_fin in tramos:
                    conn.execute(
                        "INSERT INTO horario_laboral (id, profesional_id, dia_semana, hora_inicio, hora_fin)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), prof, dia, h_ini, h_fin),
                    )
        conn.executemany(
            "INSERT INTO bloqueo (id, profesional_id, inicio, fin, motivo) VALUES (?, ?, ?, ?, ?)",
            [(i, p, texto_utc(a), texto_utc(b), m) for i, p, a, b, m in bloqueos],
        )
        for tid, cliente, servicio, inicio, estado, motivo, cancelado_por in turnos:
            fin = inicio + timedelta(minutes=DURACION[servicio])
            conn.execute(
                "INSERT INTO turno (id, cliente_id, profesional_id, servicio_id, inicio, fin, estado,"
                " motivo_cancelacion, cancelado_por_id, creado_en, actualizado_en)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, cliente, PROFESIONAL_DE[servicio], servicio, texto_utc(inicio), texto_utc(fin), estado,
                 motivo, cancelado_por, creado, creado),
            )
            _auditar(conn, "TURNO_CREADO", tid, cliente, "CLIENTE", creado, "Datos iniciales")
            if estado != "CONFIRMADO":
                actor, rol = (cancelado_por or PROFESIONAL_DE[servicio]), "CLIENTE" if cancelado_por == cliente else "PROFESIONAL"
                _auditar(conn, f"TURNO_{estado}", tid, actor, rol, ahora_txt, motivo or "Datos iniciales")


def _auditar(conn: sqlite3.Connection, accion: str, turno_id: str, actor: str, rol: str, cuando: str, detalle: str) -> None:
    conn.execute(
        "INSERT INTO auditoria_evento (id, entidad, entidad_id, accion, actor_id, rol, ocurrido_en, detalle)"
        " VALUES (?, 'Turno', ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), turno_id, accion, actor, rol, cuando, detalle),
    )


def inicializar(conn: sqlite3.Connection, ahora: datetime | None = None) -> None:
    """Crea el esquema (idempotente) y carga los datos de ejemplo solo si la base está vacía (B1.7)."""
    db.crear_esquema(conn)
    if db.esta_vacia(conn):
        cargar_datos_iniciales(conn, ahora or datetime.now(timezone.utc))


if __name__ == "__main__":
    if "--reiniciar" in sys.argv:
        for sufijo in ("", "-wal", "-shm", "-journal"):
            db.ruta_db().with_name(db.ruta_db().name + sufijo).unlink(missing_ok=True)
    conexion = db.conectar()
    try:
        inicializar(conexion)
    finally:
        conexion.close()
    print(f"Base de datos lista en {db.ruta_db()}")
