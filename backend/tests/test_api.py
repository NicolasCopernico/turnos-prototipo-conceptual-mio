"""Pruebas de la API contra spec §8 (criterios 1 a 13). Cada prueba usa su propia base de datos temporal."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import db
import main
import seed
from dominio import ZONA_HORARIA, desde_texto, texto_utc

P1, S1, S2 = seed.P1, seed.S1, seed.S2  # S1: 30 min con P1 · S2: 60 min con P1
C1, C2, C3, ADMIN = seed.C1, seed.C2, seed.C3, seed.ADMIN
T_FUERA_DE_VENTANA = seed._id(0x109)  # C3, inicia ~3 h después de la carga
T_DENTRO_DE_VENTANA = seed._id(0x108)  # C1, inicia ~1 h 59 min después de la carga
T_COMPLETADO = seed._id(0x101)  # C1


@pytest.fixture()
def ruta_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "turnos.db"
    monkeypatch.setenv("TURNOS_DB", str(ruta))
    return ruta


@pytest.fixture()
def client(ruta_db: Path) -> Iterator[TestClient]:
    with TestClient(main.app) as c:  # el `with` ejecuta el evento de arranque (crea la base de datos)
        yield c
    main.app.dependency_overrides.clear()


def dia_habil_lejano() -> date:
    """Un lunes a viernes a ~4 semanas: sin choques con los datos iniciales y dentro del horizonte de 60 días."""
    d = datetime.now(timezone.utc).astimezone(ZONA_HORARIA).date() + timedelta(days=28)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def hora_local(h: int, m: int = 0, d: date | None = None) -> str:
    """Instante ISO 8601 en UTC de una hora local de la zona de operación."""
    local = datetime.combine(d or dia_habil_lejano(), time(h, m), tzinfo=ZONA_HORARIA)
    return texto_utc(local)


def reservar(client: TestClient, cliente: str, servicio: str, inicio: str) -> Any:
    return client.post("/api/turnos", json={"cliente_id": cliente, "servicio_id": servicio, "inicio": inicio})


def cancelar(client: TestClient, turno_id: str, actor: str, motivo: str | None = None) -> Any:
    cuerpo: dict[str, Any] = {"actor_id": actor}
    if motivo is not None:
        cuerpo["motivo_cancelacion"] = motivo
    return client.post(f"/api/turnos/{turno_id}/cancelar", json=cuerpo)


def turno_en_db(ruta: Path, turno_id: str) -> sqlite3.Row:
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    try:
        fila: sqlite3.Row = conn.execute("SELECT * FROM turno WHERE id = ?", (turno_id,)).fetchone()
        return fila
    finally:
        conn.close()


def fijar_ahora(valor: datetime) -> None:
    main.app.dependency_overrides[main.obtener_ahora] = lambda: valor


# --- Arranque y GET ----------------------------------------------------------------------------
def test_arranque_crea_las_6_tablas_de_la_seccion_4_y_la_carga_inicial(client: TestClient, ruta_db: Path) -> None:
    conn = sqlite3.connect(ruta_db)
    tablas = {f[0] for f in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    conn.close()
    assert tablas == {"usuario", "servicio", "turno", "horario_laboral", "bloqueo", "auditoria_evento"}
    r = client.get("/api/turnos")
    assert r.status_code == 200
    turnos = r.json()
    assert len(turnos) == 15
    assert [t["inicio"] for t in turnos] == sorted(t["inicio"] for t in turnos)
    assert set(turnos[0]) == {
        "id", "cliente_id", "profesional_id", "servicio_id", "inicio", "fin", "estado",
        "motivo_cancelacion", "cancelado_por_id", "creado_en", "actualizado_en",
    }


def test_get_filtra_por_cliente_y_estado(client: TestClient) -> None:  # criterio 7 (lado listado)
    de_c1 = client.get("/api/turnos", params={"cliente_id": C1}).json()
    assert de_c1 and all(t["cliente_id"] == C1 for t in de_c1)
    cancelados = client.get("/api/turnos", params={"estado": "CANCELADO"}).json()
    assert len(cancelados) == 2 and all(t["estado"] == "CANCELADO" for t in cancelados)
    assert client.get("/api/turnos", params={"estado": "INVENTADO"}).status_code == 422


def test_cors_permisivo(client: TestClient) -> None:
    r = client.get("/api/turnos", headers={"Origin": "null"})
    assert r.headers["access-control-allow-origin"] == "*"
    pre = client.options(
        "/api/turnos",
        headers={"Origin": "null", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == "*"


# --- POST /api/turnos --------------------------------------------------------------------------
def test_crear_turno_201_calcula_fin_y_audita(client: TestClient, ruta_db: Path) -> None:
    r = reservar(client, C1, S1, hora_local(10))
    assert r.status_code == 201
    t = r.json()
    assert t["estado"] == "CONFIRMADO" and t["profesional_id"] == P1
    assert desde_texto(t["fin"]) - desde_texto(t["inicio"]) == timedelta(minutes=30)
    conn = sqlite3.connect(ruta_db)
    (n,) = conn.execute("SELECT COUNT(*) FROM auditoria_evento WHERE entidad_id = ? AND accion = 'TURNO_CREADO'", (t["id"],)).fetchone()
    conn.close()
    assert n == 1


def test_doble_reserva_solapamiento_parcial(client: TestClient) -> None:  # criterio 1
    assert reservar(client, C1, S1, hora_local(10)).status_code == 201
    r = reservar(client, C3, S1, hora_local(10, 15))
    assert r.status_code == 409 and r.json()["error"] == "SLOT_UNAVAILABLE"
    assert len([t for t in client.get("/api/turnos", params={"estado": "CONFIRMADO"}).json() if t["inicio"] == hora_local(10, 15)]) == 0


def test_turnos_contiguos_se_aceptan(client: TestClient) -> None:  # criterio 3
    assert reservar(client, C1, S1, hora_local(10)).status_code == 201
    assert reservar(client, C3, S1, hora_local(10, 30)).status_code == 201


def test_mismo_cliente_no_puede_solaparse_con_otro_profesional(client: TestClient) -> None:  # RN-02
    assert reservar(client, C1, S1, hora_local(11)).status_code == 201
    r = reservar(client, C1, seed.S3, hora_local(11, 15))  # S3: P2, 45 min
    assert r.status_code == 409 and r.json()["error"] == "SLOT_UNAVAILABLE"


def test_horario_fuera_de_jornada_y_bloqueo(client: TestClient) -> None:  # RN-02, RN-05
    r = reservar(client, C1, S1, hora_local(20))
    assert r.status_code == 409 and r.json()["error"] == "SLOT_UNAVAILABLE"
    conn = sqlite3.connect(db.ruta_db())
    d = dia_habil_lejano()
    conn.execute(
        "INSERT INTO bloqueo (id, profesional_id, inicio, fin, motivo) VALUES ('b-x', ?, ?, ?, 'Prueba')",
        (P1, hora_local(15, d=d), hora_local(16, d=d)),
    )
    conn.commit()
    conn.close()
    r = reservar(client, C1, S1, hora_local(15, 30))
    assert r.status_code == 409 and r.json()["error"] == "SLOT_UNAVAILABLE"


def test_concurrencia_exactamente_uno_se_confirma(client: TestClient, ruta_db: Path) -> None:  # criterio 11
    inicio = hora_local(10)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = [pool.submit(reservar, client, c, S1, inicio) for c in (C1, C3)]
        codigos = sorted(f.result().status_code for f in futuros)
    assert codigos == [201, 409]
    conn = sqlite3.connect(ruta_db)
    (n,) = conn.execute(
        "SELECT COUNT(*) FROM turno WHERE profesional_id = ? AND estado = 'CONFIRMADO' AND inicio = ?", (P1, inicio)
    ).fetchone()
    conn.close()
    assert n == 1


def test_contacto_invalido_y_email_sin_verificar(client: TestClient, ruta_db: Path) -> None:  # criterio 6
    r = reservar(client, C2, S1, hora_local(10))  # C2 tiene el email sin verificar
    assert r.status_code == 403 and r.json()["error"] == "EMAIL_NOT_VERIFIED"
    conn = sqlite3.connect(ruta_db)
    conn.execute("UPDATE usuario SET telefono = 'sin-telefono' WHERE id = ?", (C3,))
    conn.commit()
    conn.close()
    r = reservar(client, C3, S1, hora_local(10))
    assert r.status_code == 422 and r.json()["error"] == "INVALID_CONTACT"
    assert not [t for t in client.get("/api/turnos").json() if t["inicio"] == hora_local(10)]


def test_rango_de_tiempo_invalido(client: TestClient) -> None:  # RN-04
    ahora = datetime.now(timezone.utc)
    pasado = texto_utc(ahora - timedelta(days=1))
    for inicio in (pasado, hora_local(10, 5), texto_utc(ahora + timedelta(days=90))):
        r = reservar(client, C1, S1, inicio)
        assert r.status_code == 422 and r.json()["error"] == "INVALID_TIME_RANGE", inicio


def test_entidades_inexistentes_y_cuerpo_invalido(client: TestClient) -> None:
    r = reservar(client, C1, "00000000-0000-4000-8000-0000000000ff", hora_local(10))
    assert r.status_code == 404 and r.json()["error"] == "NOT_FOUND"
    r = reservar(client, P1, S1, hora_local(10))  # un profesional no reserva para sí
    assert r.status_code == 404
    # El cliente no puede enviar `fin` ni `profesional_id` (RN-04, §4.3): cuerpo rechazado por Pydantic.
    r = client.post("/api/turnos", json={"cliente_id": C1, "servicio_id": S1, "inicio": hora_local(10), "fin": hora_local(11)})
    assert r.status_code == 422
    r = client.post("/api/turnos", json={"cliente_id": C1, "servicio_id": S1, "inicio": "2026-11-09T10:00:00"})  # sin zona
    assert r.status_code == 422


def test_servicio_inactivo_422_sin_codigo_de_dominio(client: TestClient, ruta_db: Path) -> None:  # D-07
    conn = sqlite3.connect(ruta_db)
    conn.execute("UPDATE servicio SET activo = 0 WHERE id = ?", (S1,))
    conn.commit()
    conn.close()
    r = reservar(client, C1, S1, hora_local(10))
    assert r.status_code == 422 and "detail" in r.json() and "error" not in r.json()


# --- POST /api/turnos/{id}/cancelar ------------------------------------------------------------
def test_cancelacion_fuera_de_ventana_critica_3h(client: TestClient, ruta_db: Path) -> None:  # criterio 4 y 12
    r = cancelar(client, T_FUERA_DE_VENTANA, C3)
    assert r.status_code == 200
    t = r.json()
    assert t["estado"] == "CANCELADO" and t["cancelado_por_id"] == C3
    assert turno_en_db(ruta_db, T_FUERA_DE_VENTANA)["estado"] == "CANCELADO"  # persistido, no borrado


def test_cancelacion_a_1h59_rechazada_y_fila_intacta(client: TestClient, ruta_db: Path) -> None:  # criterio 5 y 12
    antes = dict(turno_en_db(ruta_db, T_DENTRO_DE_VENTANA))
    r = cancelar(client, T_DENTRO_DE_VENTANA, C1)
    assert r.status_code == 409 and r.json()["error"] == "CANCELLATION_WINDOW_EXPIRED"
    assert dict(turno_en_db(ruta_db, T_DENTRO_DE_VENTANA)) == antes


def test_limite_exacto_de_2_horas(client: TestClient) -> None:  # INV-01
    inicio = desde_texto(client.get("/api/turnos", params={"cliente_id": C3, "estado": "CONFIRMADO"}).json()[0]["inicio"])
    t = client.get("/api/turnos", params={"cliente_id": C3, "estado": "CONFIRMADO"}).json()[0]
    fijar_ahora(inicio - timedelta(hours=1, minutes=59, seconds=59))
    assert cancelar(client, t["id"], C3).status_code == 409
    fijar_ahora(inicio - timedelta(hours=2))
    assert cancelar(client, t["id"], C3).status_code == 200


def test_cancelar_libera_el_slot(client: TestClient) -> None:  # criterio 4
    t = reservar(client, C1, S1, hora_local(10)).json()
    assert reservar(client, C3, S1, hora_local(10)).status_code == 409
    assert cancelar(client, t["id"], C1).status_code == 200
    assert reservar(client, C3, S1, hora_local(10)).status_code == 201


def test_aislamiento_un_cliente_ajeno_recibe_404(client: TestClient, ruta_db: Path) -> None:  # criterio 7 / RBAC-02
    r = cancelar(client, T_FUERA_DE_VENTANA, C1)  # el turno es de C3
    assert r.status_code == 404 and r.json()["error"] == "NOT_FOUND"
    assert turno_en_db(ruta_db, T_FUERA_DE_VENTANA)["estado"] == "CONFIRMADO"
    assert cancelar(client, "no-existe", C1).status_code == 404
    otro_prof = seed.P2  # un profesional ajeno tampoco accede al turno de P3
    assert cancelar(client, T_FUERA_DE_VENTANA, otro_prof, "x").status_code == 404


def test_estado_terminal_no_se_cancela(client: TestClient) -> None:  # RN-06
    r = cancelar(client, T_COMPLETADO, C1)
    assert r.status_code == 409 and r.json()["error"] == "INVALID_STATE_TRANSITION"


def test_admin_y_profesional_cancelan_dentro_de_ventana_con_motivo(client: TestClient, ruta_db: Path) -> None:  # RN-01, excepción
    sin_motivo = cancelar(client, T_DENTRO_DE_VENTANA, ADMIN)
    assert sin_motivo.status_code == 422 and "error" not in sin_motivo.json()  # D-07
    assert cancelar(client, T_DENTRO_DE_VENTANA, ADMIN, "   ").status_code == 422
    r = cancelar(client, T_DENTRO_DE_VENTANA, ADMIN, "Profesional enfermo")
    assert r.status_code == 200
    t = r.json()
    assert t["estado"] == "CANCELADO" and t["cancelado_por_id"] == ADMIN and t["motivo_cancelacion"] == "Profesional enfermo"
    conn = sqlite3.connect(ruta_db)
    (rol,) = conn.execute(
        "SELECT rol FROM auditoria_evento WHERE entidad_id = ? AND accion = 'TURNO_CANCELADO'", (T_DENTRO_DE_VENTANA,)
    ).fetchone()
    conn.close()
    assert rol == "ADMIN"
    # el profesional dueño del turno (P3) también puede
    assert cancelar(client, T_FUERA_DE_VENTANA, seed.P3, "Cambio de agenda").status_code == 200


# --- INV-03: persistencia y atomicidad ---------------------------------------------------------
def test_persistencia_tras_reinicio(ruta_db: Path) -> None:  # criterio 9
    with TestClient(main.app) as primero:
        creado = reservar(primero, C1, S1, hora_local(10)).json()
        total = len(primero.get("/api/turnos").json())
    # "reinicio": se apaga la aplicación y se vuelve a arrancar sobre el mismo archivo
    with TestClient(main.app) as segundo:
        turnos = segundo.get("/api/turnos").json()
    assert len(turnos) == total  # la carga inicial no se duplica
    assert [t for t in turnos if t["id"] == creado["id"]] == [creado]


def test_rollback_si_falla_la_auditoria_al_crear(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:  # criterio 10
    def falla(*_: Any, **__: Any) -> None:
        raise sqlite3.OperationalError("disco lleno")

    antes = client.get("/api/turnos").json()
    with monkeypatch.context() as m:  # no usar monkeypatch.undo(): también desharía TURNOS_DB
        m.setattr(db, "insertar_auditoria", falla)
        r = reservar(client, C1, S1, hora_local(10))
    assert r.status_code == 500
    assert client.get("/api/turnos").json() == antes  # ningún turno quedó a medias


def test_rollback_si_falla_la_auditoria_al_cancelar(client: TestClient, ruta_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # criterio 10
    def falla(*_: Any, **__: Any) -> None:
        raise sqlite3.OperationalError("disco lleno")

    antes = dict(turno_en_db(ruta_db, T_FUERA_DE_VENTANA))
    with monkeypatch.context() as m:
        m.setattr(db, "insertar_auditoria", falla)
        assert cancelar(client, T_FUERA_DE_VENTANA, C3).status_code == 500
    assert dict(turno_en_db(ruta_db, T_FUERA_DE_VENTANA)) == antes


def test_la_base_de_datos_rechaza_solapamientos_por_si_sola(client: TestClient, ruta_db: Path) -> None:  # criterio 13
    ini, fin = hora_local(10), hora_local(10, 30)
    sql = (
        "INSERT INTO turno (id, cliente_id, profesional_id, servicio_id, inicio, fin, estado, creado_en, actualizado_en)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn = sqlite3.connect(ruta_db)
    conn.execute(sql, ("x1", C1, P1, S1, ini, fin, "CONFIRMADO"))
    with pytest.raises(sqlite3.IntegrityError, match="SLOT_UNAVAILABLE"):
        conn.execute(sql, ("x2", C3, P1, S1, hora_local(10, 15), hora_local(10, 45), "CONFIRMADO"))
    conn.execute(sql, ("x3", C3, P1, S1, fin, hora_local(11), "CONFIRMADO"))  # contiguo: válido
    conn.execute(sql, ("x4", C3, P1, S1, ini, fin, "CANCELADO"))  # los cancelados no participan
    conn.commit()
    conn.close()
