"""Acceso a SQLite (Capa 3 desde la Capa 2). SQL explícito, sin ORM (plan §3.2).

- Una conexión por solicitud, con claves foráneas activadas.
- Cada escritura corre en una transacción `BEGIN IMMEDIATE … COMMIT/ROLLBACK` (INV-03).
- Los instantes se guardan y comparan como texto 'YYYY-MM-DDTHH:MM:SSZ' (UTC).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

RUTA_SCHEMA = Path(__file__).with_name("schema.sql")
RUTA_DB_POR_DEFECTO = Path(__file__).resolve().parent.parent / "turnos.db"


def ruta_db() -> Path:
    """`turnos.db` en la raíz del proyecto; se puede sobrescribir con TURNOS_DB (útil en pruebas)."""
    return Path(os.environ.get("TURNOS_DB", str(RUTA_DB_POR_DEFECTO)))


def conectar() -> sqlite3.Connection:
    # isolation_level=None: autocommit; las transacciones se abren de forma explícita en `transaccion`.
    # check_same_thread=False: FastAPI puede abrir la conexión y usarla en hilos distintos del pool, pero
    # cada conexión pertenece a una sola solicitud y se usa de forma secuencial.
    conn = sqlite3.connect(ruta_db(), isolation_level=None, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaccion(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE serializa a los escritores (RN-02). Ante cualquier excepción: ROLLBACK."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def crear_esquema(conn: sqlite3.Connection) -> None:
    """Crea las tablas de spec §4.1 si no existen (idempotente)."""
    conn.executescript(RUTA_SCHEMA.read_text(encoding="utf-8"))


def esta_vacia(conn: sqlite3.Connection) -> bool:
    fila = conn.execute("SELECT COUNT(*) AS n FROM usuario").fetchone()
    return int(fila["n"]) == 0


# --- Consultas (lectura) ----------------------------------------------------------------------
def obtener_usuario(conn: sqlite3.Connection, usuario_id: str) -> sqlite3.Row | None:
    fila: sqlite3.Row | None = conn.execute("SELECT * FROM usuario WHERE id = ?", (usuario_id,)).fetchone()
    return fila


def obtener_servicio(conn: sqlite3.Connection, servicio_id: str) -> sqlite3.Row | None:
    fila: sqlite3.Row | None = conn.execute("SELECT * FROM servicio WHERE id = ?", (servicio_id,)).fetchone()
    return fila


def obtener_turno(conn: sqlite3.Connection, turno_id: str) -> sqlite3.Row | None:
    fila: sqlite3.Row | None = conn.execute("SELECT * FROM turno WHERE id = ?", (turno_id,)).fetchone()
    return fila


def listar_turnos(
    conn: sqlite3.Connection, cliente_id: str | None, profesional_id: str | None, estado: str | None
) -> list[sqlite3.Row]:
    """Filtros opcionales sobre campos de Turno (spec §11.4). Orden por `inicio` ascendente."""
    condiciones: list[str] = []
    parametros: list[str] = []
    for columna, valor in (("cliente_id", cliente_id), ("profesional_id", profesional_id), ("estado", estado)):
        if valor is not None:
            condiciones.append(f"{columna} = ?")  # `columna` es una constante de esta función, no entrada del usuario
            parametros.append(valor)
    donde = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas: list[sqlite3.Row] = conn.execute(
        f"SELECT * FROM turno{donde} ORDER BY inicio ASC, id ASC", parametros
    ).fetchall()
    return filas


def tramos_laborales(conn: sqlite3.Connection, profesional_id: str) -> list[tuple[int, str, str]]:
    filas = conn.execute(
        "SELECT dia_semana, hora_inicio, hora_fin FROM horario_laboral WHERE profesional_id = ?", (profesional_id,)
    ).fetchall()
    return [(int(f["dia_semana"]), str(f["hora_inicio"]), str(f["hora_fin"])) for f in filas]


def hay_bloqueo(conn: sqlite3.Connection, profesional_id: str, inicio: str, fin: str) -> bool:
    """RN-02/RN-05: solapamiento con un Bloqueo del profesional, sobre [inicio, fin)."""
    fila = conn.execute(
        "SELECT 1 FROM bloqueo WHERE profesional_id = ? AND inicio < ? AND ? < fin LIMIT 1",
        (profesional_id, fin, inicio),
    ).fetchone()
    return fila is not None


def hay_turno_solapado(
    conn: sqlite3.Connection, de: Literal["profesional", "cliente"], usuario_id: str, inicio: str, fin: str
) -> bool:
    """RN-02: otro turno CONFIRMADO del profesional (o del cliente) que se solape en [inicio, fin)."""
    columna = "profesional_id" if de == "profesional" else "cliente_id"
    fila = conn.execute(
        f"SELECT 1 FROM turno WHERE {columna} = ? AND estado = 'CONFIRMADO' AND inicio < ? AND ? < fin LIMIT 1",
        (usuario_id, fin, inicio),
    ).fetchone()
    return fila is not None


# --- Escrituras (siempre dentro de `transaccion`) ---------------------------------------------
def insertar_turno(
    conn: sqlite3.Connection, turno_id: str, cliente_id: str, profesional_id: str, servicio_id: str,
    inicio: str, fin: str, creado_en: str,
) -> None:
    conn.execute(
        "INSERT INTO turno (id, cliente_id, profesional_id, servicio_id, inicio, fin, estado,"
        " motivo_cancelacion, cancelado_por_id, creado_en, actualizado_en)"
        " VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMADO', NULL, NULL, ?, ?)",
        (turno_id, cliente_id, profesional_id, servicio_id, inicio, fin, creado_en, creado_en),
    )


def marcar_cancelado(
    conn: sqlite3.Connection, turno_id: str, cancelado_por_id: str, motivo: str | None, actualizado_en: str
) -> None:
    """RN-06: el turno no se borra, solo cambia de estado."""
    conn.execute(
        "UPDATE turno SET estado = 'CANCELADO', motivo_cancelacion = ?, cancelado_por_id = ?, actualizado_en = ?"
        " WHERE id = ? AND estado = 'CONFIRMADO'",
        (motivo, cancelado_por_id, actualizado_en, turno_id),
    )


def insertar_auditoria(
    conn: sqlite3.Connection, evento_id: str, entidad_id: str, accion: str, actor_id: str, rol: str,
    ocurrido_en: str, detalle: str | None,
) -> None:
    """RN-08. Solo INSERT: el log de auditoría es inmutable."""
    conn.execute(
        "INSERT INTO auditoria_evento (id, entidad, entidad_id, accion, actor_id, rol, ocurrido_en, detalle)"
        " VALUES (?, 'Turno', ?, ?, ?, ?, ?, ?)",
        (evento_id, entidad_id, accion, actor_id, rol, ocurrido_en, detalle),
    )
