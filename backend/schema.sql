-- schema.sql — Capa 3 (persistencia). SQLite.
-- Una tabla por entidad de spec.md §4.1, con exactamente sus atributos. Nada más.
-- Convenciones (spec §11.5): UUID, timestamps y enums como TEXT; booleanos como INTEGER 0/1;
-- decimal como NUMERIC. Los instantes se guardan en UTC con formato fijo
-- 'YYYY-MM-DDTHH:MM:SSZ', por lo que la comparación de texto equivale a la cronológica.

CREATE TABLE IF NOT EXISTS usuario (
    id               TEXT PRIMARY KEY,
    email            TEXT NOT NULL UNIQUE,
    email_verificado INTEGER NOT NULL DEFAULT 0 CHECK (email_verificado IN (0, 1)),
    password_hash    TEXT NOT NULL,
    nombre_completo  TEXT NOT NULL CHECK (length(nombre_completo) BETWEEN 2 AND 100),
    telefono         TEXT NOT NULL,
    rol              TEXT NOT NULL CHECK (rol IN ('CLIENTE', 'PROFESIONAL', 'ADMIN')),
    activo           INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS servicio (
    id                TEXT PRIMARY KEY,
    profesional_id    TEXT NOT NULL REFERENCES usuario (id),
    nombre            TEXT NOT NULL,
    descripcion       TEXT,
    duracion_min      INTEGER NOT NULL CHECK (duracion_min BETWEEN 15 AND 480),
    precio_referencia NUMERIC NOT NULL CHECK (precio_referencia >= 0),
    activo            INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

-- Sin ON DELETE CASCADE: el historial se preserva (spec §4.3, RN-06, RN-07).
CREATE TABLE IF NOT EXISTS turno (
    id                 TEXT PRIMARY KEY,
    cliente_id         TEXT NOT NULL REFERENCES usuario (id),
    profesional_id     TEXT NOT NULL REFERENCES usuario (id),
    servicio_id        TEXT NOT NULL REFERENCES servicio (id),
    inicio             TEXT NOT NULL,
    fin                TEXT NOT NULL,
    estado             TEXT NOT NULL CHECK (estado IN ('CONFIRMADO', 'CANCELADO', 'COMPLETADO', 'AUSENTE')),
    motivo_cancelacion TEXT,
    cancelado_por_id   TEXT REFERENCES usuario (id),
    creado_en          TEXT NOT NULL,
    actualizado_en     TEXT NOT NULL,
    CHECK (fin > inicio),
    CHECK (cliente_id <> profesional_id)
);

CREATE TABLE IF NOT EXISTS horario_laboral (
    id             TEXT PRIMARY KEY,
    profesional_id TEXT NOT NULL REFERENCES usuario (id),
    dia_semana     INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),  -- 0 = domingo
    hora_inicio    TEXT NOT NULL,                                        -- 'HH:MM' local
    hora_fin       TEXT NOT NULL,
    CHECK (hora_fin > hora_inicio)
);

CREATE TABLE IF NOT EXISTS bloqueo (
    id             TEXT PRIMARY KEY,
    profesional_id TEXT NOT NULL REFERENCES usuario (id),
    inicio         TEXT NOT NULL,
    fin            TEXT NOT NULL,
    motivo         TEXT NOT NULL,
    CHECK (fin > inicio)
);

CREATE TABLE IF NOT EXISTS auditoria_evento (
    id          TEXT PRIMARY KEY,
    entidad     TEXT NOT NULL,
    entidad_id  TEXT NOT NULL,
    accion      TEXT NOT NULL,
    actor_id    TEXT NOT NULL REFERENCES usuario (id),
    rol         TEXT NOT NULL CHECK (rol IN ('CLIENTE', 'PROFESIONAL', 'ADMIN')),
    ocurrido_en TEXT NOT NULL,
    detalle     TEXT
);

-- INV-02 / RN-02: la base de datos impide por sí sola dos turnos CONFIRMADO solapados
-- del mismo profesional, sobre intervalos semiabiertos [inicio, fin). Turnos contiguos son válidos.
-- Es la alternativa a EXCLUDE USING gist que admite RN-02 (spec §11.5). El mensaje es el código de dominio.
CREATE TRIGGER IF NOT EXISTS turno_sin_solapamiento_insert
BEFORE INSERT ON turno
WHEN NEW.estado = 'CONFIRMADO'
BEGIN
    SELECT RAISE(ABORT, 'SLOT_UNAVAILABLE')
    WHERE EXISTS (
        SELECT 1 FROM turno t
        WHERE t.profesional_id = NEW.profesional_id
          AND t.estado = 'CONFIRMADO'
          AND t.inicio < NEW.fin
          AND NEW.inicio < t.fin
    );
END;

CREATE TRIGGER IF NOT EXISTS turno_sin_solapamiento_update
BEFORE UPDATE OF profesional_id, inicio, fin, estado ON turno
WHEN NEW.estado = 'CONFIRMADO'
BEGIN
    SELECT RAISE(ABORT, 'SLOT_UNAVAILABLE')
    WHERE EXISTS (
        SELECT 1 FROM turno t
        WHERE t.id <> NEW.id
          AND t.profesional_id = NEW.profesional_id
          AND t.estado = 'CONFIRMADO'
          AND t.inicio < NEW.fin
          AND NEW.inicio < t.fin
    );
END;
