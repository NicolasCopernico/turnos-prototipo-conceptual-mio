"""Pruebas unitarias del dominio puro (tarea B2.7). Cubren los casos de la autoverificación 1.10."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from dominio import (
    Contacto,
    ErrorDominio,
    calcular_fin,
    cliente_puede_cancelar,
    dentro_de_horario_laboral,
    overlaps,
    validar_cancelable,
    validar_contacto,
    validar_tiempo,
)

UTC = timezone.utc


def dt(h: int, m: int = 0, dia: int = 9) -> datetime:
    return datetime(2026, 11, dia, h, m, tzinfo=UTC)


def test_solapamiento_parcial() -> None:  # spec §8.1
    assert overlaps(dt(10), dt(10, 30), dt(10, 15), dt(10, 45))


def test_contiguos_no_se_solapan() -> None:  # spec §8.3
    assert not overlaps(dt(10), dt(10, 30), dt(10, 30), dt(11))
    assert not overlaps(dt(10, 30), dt(11), dt(10), dt(10, 30))


def test_contenido_y_disjuntos() -> None:
    assert overlaps(dt(10), dt(12), dt(10, 30), dt(11))
    assert not overlaps(dt(10), dt(11), dt(12), dt(13))


def test_ventana_de_cancelacion_limites() -> None:  # INV-01 / spec §8.4 y §8.5
    inicio = dt(12)
    assert cliente_puede_cancelar(inicio, inicio - timedelta(hours=3))
    assert cliente_puede_cancelar(inicio, inicio - timedelta(hours=2))  # límite exacto inclusivo
    assert not cliente_puede_cancelar(inicio, inicio - timedelta(hours=1, minutes=59))
    assert not cliente_puede_cancelar(inicio, inicio + timedelta(minutes=1))  # ya iniciado


def test_tiempo_valido_e_invalido() -> None:  # RN-04
    ahora = dt(9)
    validar_tiempo(dt(10), ahora)  # exactamente 1 h de antelación: válido
    for malo in (dt(9, 59), dt(10, 5), dt(10) + timedelta(seconds=1), ahora + timedelta(days=61)):
        with pytest.raises(ErrorDominio) as e:
            validar_tiempo(malo, ahora)
        assert e.value.codigo == "INVALID_TIME_RANGE" and e.value.http == 422


def test_calcular_fin() -> None:
    assert calcular_fin(dt(10), 45) == dt(10, 45)


def test_horario_laboral_usa_hora_local_y_domingo_cero() -> None:
    # 2026-11-09 es lunes (dia_semana = 1). Zona por defecto: UTC-3, así que 13:00Z = 10:00 local.
    tramos = [(1, "09:00", "13:00"), (1, "14:00", "18:00")]
    assert dentro_de_horario_laboral(dt(13), dt(13, 30), tramos)
    assert not dentro_de_horario_laboral(dt(15, 45), dt(16, 15), tramos)  # cruza las 13:00 locales
    assert not dentro_de_horario_laboral(dt(13, dia=8), dt(13, 30, dia=8), tramos)  # domingo


def test_contacto() -> None:  # RN-03
    ok = Contacto("Lucía Fernández", "Lucia@Mail.test ", "+54 9 11 5555-0101", True)
    validar_contacto(ok)  # se normaliza antes de validar
    casos = {
        "INVALID_CONTACT": [
            Contacto("L", "a@b.co", "+5491155550101", True),
            Contacto("Lucía", "no-es-email", "+5491155550101", True),
            Contacto("Lucía", "a@b.co", "1155550101", True),
        ],
        "EMAIL_NOT_VERIFIED": [Contacto("Lucía", "a@b.co", "+5491155550101", False)],
    }
    for codigo, contactos in casos.items():
        for c in contactos:
            with pytest.raises(ErrorDominio) as e:
                validar_contacto(c)
            assert e.value.codigo == codigo


def test_estados_terminales_no_se_cancelan() -> None:  # RN-06
    validar_cancelable("CONFIRMADO")
    for estado in ("CANCELADO", "COMPLETADO", "AUSENTE"):
        with pytest.raises(ErrorDominio) as e:
            validar_cancelable(estado)
        assert e.value.codigo == "INVALID_STATE_TRANSITION"
