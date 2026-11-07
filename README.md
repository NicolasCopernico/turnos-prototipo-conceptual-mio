# Turnos Pro — Gestión de turnos y reservas de servicios profesionales

Este proyecto forma parte del curso **"Creá tu proyecto con Inteligencia Artificial"**. Es el resultado de las **3 primeras clases, que conforman la FASE 1** del curso: pasar de una idea a un prototipo funcional trabajando con la metodología **Spec-Driven Development (SDD)**, donde primero se escribe una especificación formal y recién después se genera el código.

- **Prototipo en línea:** https://claude.ai/artifact/JUv3cgvTQv1i2vxf3DK5z2 
- **Prototipo local:** abrí [index.html](index.html) con doble clic. Necesita internet, porque React y Tailwind se cargan desde CDN.

## Cómo clonar este repositorio

Para descargar el proyecto directamente desde GitHub, abrí una terminal y ejecutá:

```bash
git clone https://github.com/centrograduadosFIUBA/turnos-prototipo-conceptual.git
cd turnos-prototipo-conceptual
```

Después, abrí `index.html` en el navegador. No hace falta instalar dependencias ni compilar el proyecto.

## Cómo hacer un fork y clonarlo

Un fork crea una copia del repositorio en tu propia cuenta de GitHub. Es útil si querés experimentar o proponer cambios sin modificar directamente el repositorio original.

1. Iniciá sesión en [GitHub](https://github.com/) y abrí el [repositorio del proyecto](https://github.com/centrograduadosFIUBA/turnos-prototipo-conceptual).
2. Presioná **Fork** en la parte superior derecha.
3. Elegí tu cuenta como destino y confirmá la creación del fork.
4. En una terminal, reemplazá `<tu-usuario>` por tu nombre de usuario de GitHub y cloná tu fork:

   ```bash
   git clone https://github.com/<tu-usuario>/turnos-prototipo-conceptual.git
   cd turnos-prototipo-conceptual
   ```

5. Si querés mantener tu copia al día con el repositorio original, agregalo como remoto `upstream`:

   ```bash
   git remote add upstream https://github.com/centrograduadosFIUBA/turnos-prototipo-conceptual.git
   git remote -v
   ```

## Qué es

Una aplicación web para reservar turnos con profesionales. Tiene dos vistas sobre los mismos datos en memoria:

- **Vista Cliente:** elegir servicio, ver horarios libres, reservar, confirmar y cancelar turnos propios.
- **Vista Administrador:** agenda, métricas, bloqueos de horarios, servicios, auditoría y acciones sobre los turnos.

Las reglas del negocio (sin doble reserva, cancelación hasta 2 horas antes, datos de contacto válidos, permisos por rol) están implementadas tal como las define el spec. La pantalla no decide qué está permitido: cada acción pasa por un módulo de dominio que responde con códigos de error como `SLOT_UNAVAILABLE`.

## Archivos del proyecto

| Archivo | Contenido |
|---|---|
| [spec.md](spec.md) | Especificación técnica: alcance del MVP, roles y permisos, reglas invariantes (RN-xx / INV-xx), modelo de datos y, desde la v0.2, el contrato REST de la Fase 2 (§11) |
| [historias-de-usuario.md](historias-de-usuario.md) | 7 historias de los dos flujos principales, con criterios en Gherkin y casos borde |
| [plan.md](plan.md) | Plan v2: arquitectura de 3 capas de la Fase 2. El plan del prototipo conceptual (Fase 1) está en su Anexo A |
| [tareas.md](tareas.md) | Parte A: 9 fases del prototipo conceptual. Parte B: fases B0 a B6 de la Fase 2 (backend) |
| [index.html](index.html) | La aplicación completa en un solo archivo (dominio, estado, vistas y datos de ejemplo) |
| [guia-de-uso.md](guia-de-uso.md) | Funcionalidades y guía paso a paso de pruebas en la interfaz |
| `backend/` (solo en la rama `backend`) | Fase 2: API FastAPI (`main.py`), reglas (`dominio.py`), acceso a SQLite (`db.py`), esquema (`schema.sql`), datos de ejemplo (`seed.py`) y pruebas (`tests/`). Ver [Fase 2](#fase-2--backend-con-persistencia-real-en-construcción) |

## Cómo se construyó: paso a paso

El flujo fue siempre el mismo: **pedir un documento, revisarlo, y usarlo como base del siguiente paso**. Cada paso produjo un archivo que alimentó al siguiente.

```
Spec  →  Historias de usuario  →  Plan  →  Tareas  →  Código (index.html)  →  Publicación y guía  →  README
```

### Paso 1 — Especificación técnica (`spec.md`)

Se le pidió a la IA que actuara como arquitecto de software y definiera, antes de escribir código, el contrato del sistema: qué entra en el MVP, quién puede hacer qué, qué reglas no se pueden romper y cómo se relacionan los datos.

**Prompt:**

```
Actuá como un Arquitecto de Software y Analista de Sistemas Senior bajo la metodología Spec-Driven Development (SDD).

Quiero diseñar una aplicación web para la gestión de turnos y reservas de servicios profesionales. Antes de escribir una sola línea de código, vamos a construir la especificación técnica formal (nuestro spec.md como contrato del sistema).

Generá un documento técnico estructurado en Markdown que contenga:
1. Alcance del MVP: Qué incluye explícitamente y qué queda fuera de esta primera versión.
2. Matriz de Roles y Permisos (RBAC):
   - Cliente (exploración, reserva de turnos, consulta y cancelación de sus propias citas).
   - Profesional / Administrador (gestión de agenda, bloqueo de rangos horarios, visualización de métricas).
3. Reglas Invariantes del Negocio (restricciones no negociables):
   - Ventana de cancelación mínima permitida (ej: 2 horas antes).
   - Prohibición estricta de doble reserva / solapamiento sobre un mismo horario.
   - Validación obligatoria de datos de contacto.
4. Modelo de Datos Conceptual: Entidades principales (Usuarios, Servicios, Turnos) y sus relaciones.
```

**Resultado:** [spec.md](spec.md), con funcionalidades numeradas (F-01 a F-13), reglas de negocio (RN-01 a RN-08), una matriz de permisos, un diagrama de entidades, un catálogo de errores y criterios de aceptación.

### Paso 2 — Historias de usuario (`historias-de-usuario.md`)

Con el spec como base, se derivaron las historias de los dos flujos más importantes, cada una con criterios en formato Gherkin y casos borde para prevenir.

**Prompt:**

```
Tomando como base estricta el spec.md que acabamos de definir, generá las Historias de Usuario críticas para este MVP.

Para cada historia de usuario:
1. Formato estándar: "Como [rol], quiero [acción], para [beneficio]".
2. Criterios de Aceptación obligatorios en formato Gherkin (Dado que... / Cuando... / Entonces...).
3. Identificación de al menos un caso borde (Edge Case) o manejo de error a prevenir.

Enfocate en los dos flujos core:
- Flujo 1: Reserva y confirmación de turno por parte del Cliente.
- Flujo 2: Gestión de agenda y cancelación de turno por parte del Administrador.
```

**Resultado:** [historias-de-usuario.md](historias-de-usuario.md). Al derivar las historias aparecieron cinco huecos del spec, que quedaron listados como preguntas abiertas.

### Paso 3 — Plan de implementación (revisión antes de construir)

El prompt pedía explícitamente compartir un plan **antes de empezar**, para poder revisarlo. La IA no escribió código en este paso: presentó el plan, los datos de ejemplo previstos y cinco decisiones con un valor por defecto.

**Prompt:**

```
Ahora vamos a "compilar" nuestra especificación técnica en un prototipo interactivo funcional utilizando Claude Artifacts (un único componente React con Tailwind CSS y Lucide Icons).

Requisitos de implementación:
1. Fuente de la verdad: Implementá estrictamente las reglas invariantes, roles y criterios de aceptación definidos en nuestro spec.md.
2. Selector de Rol en la barra superior: Permitir alternar entre "Vista Cliente" y "Vista Administrador" para auditar permisos en vivo.
3. Vista Cliente: Selector de servicio, grilla de horarios disponibles, formulario de confirmación y vista de turnos agendados con opción de cancelar (respetando la regla de tiempo límite).
4. Vista Administrador: Calendario/lista de turnos, métricas básicas, acción de cancelar/completar turnos y bloqueo de horarios.
5. Estado y datos mock: Incluí datos iniciales realistas en memoria para que las acciones en una vista impacten de inmediato en la otra.

Generá el componente interactivo completo, modular y listo para ejecutar.

Antes de comenzar, comparte un plan de los pasos que seguirás para que pueda revisarlo.
```

### Paso 4 — Guardar el plan y organizarlo en tareas (`plan.md`, `tareas.md`)

Se aprobó el plan y se pidió dejarlo por escrito, más una lista de tareas por fases.

**Prompt:**

```
guarda el plan en el archivo plan.md y luego genera un archivo tareas.md organizado en fases para cumplir ese plan
```

**Resultado:** [plan.md](plan.md) y [tareas.md](tareas.md), este último con 9 fases (preparación, dominio, estado, interfaz compartida, vista Cliente, vista Administrador, integración, verificación y publicación), cada una con su criterio de cierre.

### Paso 5 — Construcción del prototipo (`index.html`)

Se pidió llevar todo a un único archivo funcional. La IA lo escribió, lo abrió en el navegador integrado y verificó el comportamiento: ejecutó unas 38 comprobaciones de las reglas del spec, entre ellas dos clientes sobre el mismo horario, el límite exacto de 2 horas y los bloqueos con conflicto. También corrigió un detalle visual de capitalización en las fechas.

**Prompt:**

```
quiero llegar a tener el index.html funcional con todo el codigo alli de manera monolitica
```

**Resultado:** [index.html](index.html). Incluye herramientas para auditar el comportamiento: reloj simulado, bandeja de emails simulada, "Modo auditoría" y simulaciones de concurrencia y doble clic.

### Paso 6 — Publicación y guía de uso (`guia-de-uso.md`)

Se publicó el prototipo como Artifact de Claude y se documentaron las funcionalidades con una guía de pruebas paso a paso.

**Prompt:**

```
publica el artifact y agrega a la carpeta una documentacion completa de las funcionalidaes y de las preubas que se pueden hacer en la interface. una guia paso a paso
```

**Resultado:** el [Artifact publicado](https://claude.ai/artifact/JUv3cgvTQv1i2vxf3DK5z2) y [guia-de-uso.md](guia-de-uso.md), con más de 25 pruebas organizadas por bloque.

### Paso 7 — Este README

**Prompt:**

```
Genera un readme explicando que este codigo forma parte del curso "Creá tu proyecto con Inteligencia Artificial" y es el resultado de las 3 primeras Clases que conforman la FASE 1 del curso. Agrega en ese readme el paso a paso que hicmos en esta charla y los prompts que fuimos usando en cada caso
```

## Qué se aprende con este recorrido

1. **La especificación va primero.** Con el spec escrito, el resto de los documentos y el código se derivan de él y se pueden contrastar contra él.
2. **Pedir el plan antes del código** permite corregir el rumbo sin gastar trabajo de construcción.
3. **Cada documento alimenta al siguiente.** El spec generó las historias, las historias y el spec generaron el plan, y el plan generó las tareas y el código.
4. **Un prototipo se verifica contra el spec**, no contra la intuición. Cada regla tiene un escenario de prueba asociado.
5. **Revisar lo que produce la IA importa.** Al derivar las historias se detectaron huecos del spec, y al probar el código se corrigieron detalles.

## Cómo probarlo

**Con el backend (Fase 2).** Los turnos se leen y se guardan en SQLite, así que `index.html` necesita el backend levantado (ver [Fase 2](#fase-2--backend-con-persistencia-real-en-construcción)). Abrí [index.html](index.html) (con `?api=http://localhost:PUERTO` si levantaste el backend en un puerto distinto del 8012) y probá:

1. **Reserva y persistencia:** Vista Cliente, usuaria Lucía, elegí un servicio, un día y un horario libre, y confirmá. Recargá la página con F5: el turno sigue ahí, porque se leyó de la base de datos.
2. **Regla de las 2 horas (INV-01):** activá **Modo auditoría** y probá cancelar el turno de *Asesoría nutricional* de Lucía, que empieza dentro de las 2 horas posteriores a la carga inicial. El backend responde `409 CANCELLATION_WINDOW_EXPIRED` y la pantalla muestra su mensaje.
3. **Doble reserva (INV-02):** en el modal de reserva, desplegá *Simulaciones de auditoría* y activá la del otro cliente. Ese cliente reserva primero (de verdad, en la base) y a vos el backend te responde `409 SLOT_UNAVAILABLE`.

La [guía de uso](guia-de-uso.md) describe la versión de la Fase 1 (todo en memoria y con reloj simulado); ver el aviso al comienzo de ese archivo.

## Límites conocidos

- `index.html` no tiene persistencia: al recargar, los datos vuelven al estado inicial. El backend de la Fase 2 sí persiste, pero todavía no está conectado a la interfaz.
- No hay inicio de sesión real; el rol se elige con un selector para poder auditar permisos.
- Los emails son simulados.
- La concurrencia está simulada: las acciones se procesan una detrás de otra. En un sistema real, la garantía contra la doble reserva debe vivir en la base de datos.
- Quedan fuera del prototipo: la reserva en nombre de un cliente, el cambio de horario laboral con turnos ya reservados y el alta de servicios nuevos.

## Tecnologías

- **Frontend (`index.html`):** HTML, React 18 y Tailwind CSS cargados por CDN, con íconos de Lucide incluidos en el mismo archivo. No hay compilación ni dependencias locales.
- **Backend (`backend/`):** Python, FastAPI, Uvicorn y SQLite (módulo `sqlite3` de la biblioteca estándar). Pruebas con pytest y tipado verificado con mypy.

## Fase 2 — Backend con persistencia real (en construcción)

La Fase 2 del curso separa el proyecto en **3 capas**: el frontend (`index.html`), un backend en Python con FastAPI y una base de datos SQLite (`turnos.db`). La arquitectura está en [plan.md](plan.md) y el contrato, en [spec.md](spec.md) §11. El avance está en la Parte B de [tareas.md](tareas.md).

**El código del backend vive en la rama `backend`**, separada de `main`. En `main` quedan la documentación (spec, plan, tareas, README) y el frontend, y la carpeta `backend/` **no tiene los archivos del servidor** (por eso `uvicorn main:app` falla con `Could not import module "main"` si lo corrés ahí). Para usar el backend sin dejar la rama `main`, creá una segunda carpeta de trabajo con la rama `backend`:

```bash
git worktree add ../turnos-backend backend
cd ../turnos-backend/backend
```

Esa carpeta no incluye el entorno virtual (`.venv` está en el `.gitignore`), así que hay que crearlo ahí (ver [Instalación](#instalación-una-sola-vez)). Las instrucciones de esta sección se ejecutan desde `turnos-backend/backend/`, y el frontend se abre desde la carpeta de `main`. Si preferís trabajar en una sola carpeta, `git switch backend` también sirve, pero entonces el `index.html` que ves es el de esa rama. Cuando la Fase 2 esté completa, `backend` se integra en `main`.

**Estado actual:** `index.html` ya consume el backend para los turnos (tarea B4): lista, reserva y cancela con `fetch` a la API, y los datos sobreviven a F5. Se puede probar también con Swagger UI, `curl` o `pytest`.

**Qué es real y qué sigue siendo de ejemplo en `index.html`:**

| Real (API y SQLite) | De ejemplo (datos locales, no persisten) |
|---|---|
| Lista de turnos, reservar y cancelar. Los errores 409 se muestran con el motivo que devuelve el backend. | Catálogo de servicios, horarios, bloqueos, bandeja de emails, auditoría y métricas. |
| La hora actual es la real: el reloj simulado se retiró. | Completar, marcar ausente, verificar email y bloquear un rango con turnos: muestran `NOT_IMPLEMENTED`, porque el contrato de la Fase 2 no tiene esos endpoints. |

Los cambios que hagas en el formulario de contacto de la reserva no se guardan: el contrato no permite editar usuarios. El backend usa los datos de contacto que tiene en la base.

### Puertos

| Puerto | Cuándo |
|---|---|
| **8012** | Es el puerto que usan por defecto el frontend y todos los ejemplos de esta documentación. |
| Cualquier otro puerto libre (por ejemplo **8000**) | Si el 8012 está ocupado en tu equipo (`Address already in use`). Cambiá el número de `--port`, la URL de Swagger UI y abrí el frontend con `?api=`. |

El puerto no forma parte del contrato (spec §11.2): lo que el contrato fija son las rutas, los cuerpos y los códigos de error. En producción la URL base será la del dominio del backend (detrás de un proxy inverso), no un puerto de `localhost`.

**El frontend apunta por defecto al puerto 8012.** `index.html` define la URL del backend en una sola constante (`API_BASE`). Si levantás el backend en otro puerto, abrí la página con el parámetro `?api=`, sin editar el archivo:

```
index.html?api=http://localhost:8000   # ejemplo: backend en el puerto 8000
```

El CORS no necesita cambios. Para usar siempre otro puerto, alcanza con abrir la página con ese parámetro o con cambiar el valor por defecto de `API_BASE`.

### Instalación (una sola vez)

Requiere Python 3.11 o superior (desarrollado con 3.14).

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Levantar el servidor

```bash
cd backend
.venv/bin/uvicorn main:app --reload --port 8012
```

- `--reload` reinicia el servidor al guardar cambios en los `.py`.
- Al arrancar crea `turnos.db` en la raíz del proyecto (con las 6 tablas de [spec.md](spec.md) §4.1) y la llena con los datos de ejemplo **solo si está vacía**. Los datos sobreviven a los reinicios.
- **Swagger UI (probar los endpoints):** <http://localhost:8012/docs>
- Para empezar de cero: detené el servidor, borrá `turnos.db` y volvé a arrancar, o ejecutá `cd backend && .venv/bin/python seed.py --reiniciar`.

### Endpoints

| Método y ruta | Qué hace | Reglas |
|---|---|---|
| `GET /api/turnos` | Lista los turnos. Filtros opcionales: `cliente_id`, `profesional_id`, `estado`. | RN-06 |
| `POST /api/turnos` | Crea una reserva. Cuerpo: `cliente_id`, `servicio_id`, `inicio`. | INV-02, RN-03, RN-04 |
| `POST /api/turnos/{id}/cancelar` | Cancela una reserva. Cuerpo: `actor_id` y, si cancela un profesional o el administrador, `motivo_cancelacion`. | INV-01 |

Los errores de dominio responden `{"error": "<CÓDIGO>", "mensaje": "…"}` con los códigos de [spec.md](spec.md) §7 (`SLOT_UNAVAILABLE`, `CANCELLATION_WINDOW_EXPIRED`, etc.).

### Probarlo con datos de ejemplo

Los identificadores de la carga inicial son fijos. Con el servidor en el puerto 8012:

```bash
# Listar turnos
curl http://localhost:8012/api/turnos

# Cancelar el turno que empieza ~3 h después de la carga (cliente Sofía): 200
curl -X POST http://localhost:8012/api/turnos/00000000-0000-4000-8000-000000000109/cancelar \
  -H 'content-type: application/json' \
  -d '{"actor_id": "00000000-0000-4000-8000-000000000023"}'

# Cancelar el turno que empieza ~1 h 59 min después de la carga (cliente Lucía): 409 CANCELLATION_WINDOW_EXPIRED
curl -X POST http://localhost:8012/api/turnos/00000000-0000-4000-8000-000000000108/cancelar \
  -H 'content-type: application/json' \
  -d '{"actor_id": "00000000-0000-4000-8000-000000000021"}'
```

Estos dos turnos están calculados respecto del momento de la carga inicial: si la base es de hace más de una hora, el comportamiento cambia. Para repetir la prueba, reiniciá los datos.

| Quién | `id` |
|---|---|
| Lucía Fernández (cliente) | `00000000-0000-4000-8000-000000000021` |
| Martín Gómez (cliente, email sin verificar) | `00000000-0000-4000-8000-000000000022` |
| Sofía Ruiz (cliente) | `00000000-0000-4000-8000-000000000023` |
| Admin General | `00000000-0000-4000-8000-000000000001` |
| Dra. Ana Martínez (profesional) | `00000000-0000-4000-8000-000000000011` |
| Consulta general, 30 min (Ana Martínez) | `00000000-0000-4000-8000-000000000031` |

Para crear una reserva con `POST /api/turnos`, el `inicio` va en UTC, alineado a 15 minutos, con al menos 1 hora de antelación y dentro del horario laboral del profesional. Por ejemplo, las 10:00 hora de Buenos Aires son las `13:00:00Z`.

### Pruebas y tipado

```bash
cd backend
.venv/bin/python -m pytest -q                                   # 33 pruebas (dominio, API, persistencia, concurrencia)
.venv/bin/python -m mypy --strict main.py dominio.py db.py seed.py tests
```

Las pruebas usan una base de datos temporal y no tocan `turnos.db`.

### Configuración

| Variable | Para qué | Valor por defecto |
|---|---|---|
| `ZONA_HORARIA` | Zona horaria con la que se interpretan los horarios laborales. Los instantes se guardan siempre en UTC. | `America/Argentina/Buenos_Aires` |
| `TURNOS_DB` | Ruta de la base de datos. | `turnos.db` en la raíz del proyecto |

### Límites de la Fase 2

- No hay autenticación: la API recibe `cliente_id` o `actor_id` en el cuerpo y confía en él (spec D-06).
- Solo existen los 3 endpoints del contrato. El catálogo de servicios y los horarios no se leen de la API: el frontend los conserva como datos de ejemplo (spec D-08).
- El servidor usa el reloj real, no el reloj simulado del prototipo (spec D-09).
- CORS abierto a cualquier origen: es solo para desarrollo local.
- El `password_hash` de los usuarios de ejemplo no es verificable porque el inicio de sesión queda fuera de esta fase.


-------------------------------------------------------------------------------------
cd ~/proyectos/Crea_tu_proyecto_con_ia/clase_04/turnos-backend/backend
~/proyectos/Crea_tu_proyecto_con_ia/clase_04/turnos-prototipo-conceptual/backend/.venv/bin/uvicorn main:app --reload --port 8012