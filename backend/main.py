"""Backend de Turnos Pro — Capa 2 (FastAPI, puerto 8000). Contrato: spec.md §11.

Arranque (desde la carpeta backend/):

    uvicorn main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs

Solo expone los 3 endpoints del contrato. Las reglas viven en `dominio.py`; el acceso a SQLite, en `db.py`.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

import db
import dominio
import seed
from dominio import Contacto, ErrorDominio

Estado = Literal["CONFIRMADO", "CANCELADO", "COMPLETADO", "AUSENTE"]


# --- Modelos Pydantic (campos = spec §4.1 y §11.4; nada más) -------------------------------------
class TurnoCrear(BaseModel):
    """Cuerpo de POST /api/turnos. El cliente NO envía `fin` ni `profesional_id` (RN-04, §4.3)."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: UUID
    servicio_id: UUID
    inicio: AwareDatetime = Field(description="Instante en ISO 8601 con zona, por ejemplo 2026-11-09T12:00:00Z.")


class TurnoCancelar(BaseModel):
    """Cuerpo de POST /api/turnos/{id}/cancelar. `motivo_cancelacion` es obligatorio para PROFESIONAL/ADMIN."""

    model_config = ConfigDict(extra="forbid")

    actor_id: UUID
    motivo_cancelacion: str | None = Field(default=None, max_length=500)


class TurnoOut(BaseModel):
    id: str
    cliente_id: str
    profesional_id: str
    servicio_id: str
    inicio: str
    fin: str
    estado: Estado
    motivo_cancelacion: str | None
    cancelado_por_id: str | None
    creado_en: str
    actualizado_en: str


class ErrorOut(BaseModel):
    """Error de dominio: `error` es un código del catálogo de spec §7."""

    error: str
    mensaje: str


# --- Aplicación -------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Al iniciar: crea las tablas de spec §4.1 si no existen y carga los datos de ejemplo si está vacía."""
    conn = db.conectar()
    try:
        seed.inicializar(conn)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="Turnos Pro — API",
    version="0.2.2",
    description="Contrato REST de la Fase 2 (spec.md §11). Persistencia en SQLite (`turnos.db`, INV-03).",
    lifespan=lifespan,
)

# CORS permisivo solo para desarrollo local: el frontend puede abrirse como archivo (origen `null`)
# y la API no usa cookies ni credenciales (plan §3.2).
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
    return JSONResponse(status_code=exc.http, content={"error": exc.codigo, "mensaje": exc.mensaje})


@app.exception_handler(sqlite3.Error)
async def manejar_error_persistencia(_request: Request, _exc: sqlite3.Error) -> JSONResponse:
    # INV-03: la transacción ya hizo ROLLBACK; no se informa éxito ni se persiste nada.
    return JSONResponse(status_code=500, content={"detail": "Error de persistencia. No se guardó ningún cambio."})


# --- Dependencias -----------------------------------------------------------------------------
def obtener_conexion() -> Iterator[sqlite3.Connection]:
    conn = db.conectar()
    try:
        yield conn
    finally:
        conn.close()


def obtener_ahora() -> datetime:
    """Reloj real en UTC (D-09). Las pruebas lo reemplazan con `app.dependency_overrides`."""
    return datetime.now(timezone.utc).replace(microsecond=0)


Conexion = Annotated[sqlite3.Connection, Depends(obtener_conexion)]
Ahora = Annotated[datetime, Depends(obtener_ahora)]

RESPUESTAS_ERROR: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorOut, "description": "EMAIL_NOT_VERIFIED"},
    404: {"model": ErrorOut, "description": "NOT_FOUND"},
    409: {"model": ErrorOut, "description": "SLOT_UNAVAILABLE · CANCELLATION_WINDOW_EXPIRED · INVALID_STATE_TRANSITION"},
    422: {"description": "INVALID_CONTACT · INVALID_TIME_RANGE, o validación de la solicitud"},
}


# --- Endpoints --------------------------------------------------------------------------------
@app.get("/api/turnos", response_model=list[TurnoOut], summary="Listar turnos")
def listar_turnos(
    conn: Conexion,
    cliente_id: Annotated[UUID | None, Query()] = None,
    profesional_id: Annotated[UUID | None, Query()] = None,
    estado: Annotated[Estado | None, Query()] = None,
) -> list[dict[str, Any]]:
    """Todos los turnos (en cualquier estado, RN-06), ordenados por `inicio`. Filtros opcionales."""
    filas = db.listar_turnos(
        conn,
        str(cliente_id) if cliente_id else None,
        str(profesional_id) if profesional_id else None,
        estado,
    )
    return [dict(f) for f in filas]


@app.post(
    "/api/turnos",
    response_model=TurnoOut,
    status_code=201,
    responses=RESPUESTAS_ERROR,
    summary="Crear reserva",
)
def crear_turno(datos: TurnoCrear, conn: Conexion, ahora: Ahora) -> dict[str, Any]:
    """Aplica RN-03, RN-04 y **INV-02** (RN-02) en el servidor y persiste en una sola transacción (INV-03)."""
    cliente_id, servicio_id = str(datos.cliente_id), str(datos.servicio_id)
    inicio = dominio.a_utc(datos.inicio)
    try:
        with db.transaccion(conn):
            # 1. Existencia
            cliente = db.obtener_usuario(conn, cliente_id)
            servicio = db.obtener_servicio(conn, servicio_id)
            if cliente is None or cliente["rol"] != "CLIENTE" or servicio is None:
                raise ErrorDominio("NOT_FOUND", "El cliente o el servicio no existe.")
            # 2. Contacto (RN-03)
            dominio.validar_contacto(
                Contacto(cliente["nombre_completo"], cliente["email"], cliente["telefono"], bool(cliente["email_verificado"]))
            )
            # 3. Integridad temporal (RN-04)
            dominio.validar_tiempo(inicio, ahora)
            if not servicio["activo"]:  # RN-07 / D-07: 422 sin código de dominio nuevo
                raise HTTPException(status_code=422, detail="El servicio está desactivado y no admite nuevas reservas.")
            # 4. Disponibilidad (INV-02 / RN-02)
            profesional_id: str = servicio["profesional_id"]
            fin = dominio.calcular_fin(inicio, int(servicio["duracion_min"]))
            ini_txt, fin_txt = dominio.texto_utc(inicio), dominio.texto_utc(fin)
            if not dominio.dentro_de_horario_laboral(inicio, fin, db.tramos_laborales(conn, profesional_id)):
                raise ErrorDominio("SLOT_UNAVAILABLE", "Ese horario está fuera de la jornada laboral del profesional.")
            if db.hay_bloqueo(conn, profesional_id, ini_txt, fin_txt):
                raise ErrorDominio("SLOT_UNAVAILABLE", "El profesional bloqueó ese horario.")
            if db.hay_turno_solapado(conn, "profesional", profesional_id, ini_txt, fin_txt):
                raise ErrorDominio("SLOT_UNAVAILABLE", "Ese horario ya fue reservado.")
            if db.hay_turno_solapado(conn, "cliente", cliente_id, ini_txt, fin_txt):
                raise ErrorDominio("SLOT_UNAVAILABLE", "Ya tenés un turno confirmado que se solapa con ese horario.")
            # 5. Persistencia atómica: Turno + AuditoriaEvento (INV-03, RN-08)
            turno_id, creado_en = str(uuid.uuid4()), dominio.texto_utc(ahora)
            db.insertar_turno(conn, turno_id, cliente_id, profesional_id, servicio_id, ini_txt, fin_txt, creado_en)
            db.insertar_auditoria(
                conn, str(uuid.uuid4()), turno_id, "TURNO_CREADO", cliente_id, "CLIENTE", creado_en,
                f"{servicio['nombre']} · {ini_txt}",
            )
            creado = db.obtener_turno(conn, turno_id)
    except sqlite3.IntegrityError as exc:
        raise _traducir_integridad(exc) from exc
    assert creado is not None
    return dict(creado)


@app.post(
    "/api/turnos/{turno_id}/cancelar",
    response_model=TurnoOut,
    responses=RESPUESTAS_ERROR,
    summary="Cancelar reserva",
)
def cancelar_turno(turno_id: str, datos: TurnoCancelar, conn: Conexion, ahora: Ahora) -> dict[str, Any]:
    """Aplica **INV-01** (RN-01) en el servidor: el cliente solo cancela con 2 h o más de antelación."""
    actor_id = str(datos.actor_id)
    motivo = (datos.motivo_cancelacion or "").strip() or None
    with db.transaccion(conn):
        # 1. Existencia y acceso: un recurso ajeno responde 404, no 403 (RBAC-02)
        turno = db.obtener_turno(conn, turno_id)
        actor = db.obtener_usuario(conn, actor_id)
        if turno is None or actor is None:
            raise ErrorDominio("NOT_FOUND", "El turno no existe.")
        es_cliente = actor_id == turno["cliente_id"]
        es_gestor = actor["rol"] == "ADMIN" or (actor["rol"] == "PROFESIONAL" and actor_id == turno["profesional_id"])
        if not (es_cliente or es_gestor):
            raise ErrorDominio("NOT_FOUND", "El turno no existe.")
        # 2. Ciclo de vida (RN-06)
        dominio.validar_cancelable(turno["estado"])
        # 3. Ventana (INV-01) para el cliente; motivo obligatorio para PROFESIONAL/ADMIN (excepción de RN-01)
        if es_cliente:
            if not dominio.cliente_puede_cancelar(dominio.desde_texto(turno["inicio"]), ahora):
                raise ErrorDominio(
                    "CANCELLATION_WINDOW_EXPIRED",
                    f"Solo se puede cancelar con al menos {dominio.CANCELLATION_WINDOW_HOURS} horas de anticipación.",
                )
            rol = "CLIENTE"
        else:
            if motivo is None:  # D-07: 422 sin código de dominio nuevo
                raise HTTPException(status_code=422, detail="motivo_cancelacion es obligatorio para PROFESIONAL y ADMIN.")
            rol = str(actor["rol"])
        # 4. Persistencia atómica: Turno + AuditoriaEvento (INV-03, RN-08)
        ahora_txt = dominio.texto_utc(ahora)
        db.marcar_cancelado(conn, turno_id, actor_id, motivo, ahora_txt)
        db.insertar_auditoria(
            conn, str(uuid.uuid4()), turno_id, "TURNO_CANCELADO", actor_id, rol, ahora_txt,
            f"Motivo: {motivo}" if motivo else "Cancelado por el cliente",
        )
        cancelado = db.obtener_turno(conn, turno_id)
    assert cancelado is not None
    return dict(cancelado)


def _traducir_integridad(exc: sqlite3.IntegrityError) -> Exception:
    """El trigger de schema.sql aborta con el código de dominio como mensaje (INV-02 en la base de datos)."""
    if "SLOT_UNAVAILABLE" in str(exc):
        return ErrorDominio("SLOT_UNAVAILABLE", "Ese horario ya fue reservado.")
    return exc
