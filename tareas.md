# tareas.md — Tareas por fase para ejecutar [plan.md](plan.md)

Leyenda: `[ ]` pendiente · `[x]` hecho · **Salida** = entregable de la fase · **Hecho cuando** = criterio de cierre.
Cada fase depende de la anterior. Las referencias (`RN-xx`, `INV-xx`, `ERR-xx`, `HU-xx`) apuntan a [spec.md](spec.md) v0.2.1 y [historias-de-usuario.md](historias-de-usuario.md).

Este archivo tiene dos partes:

| Parte | Contenido | Estado |
|---|---|---|
| **A — Prototipo conceptual** | Fases 0 a 8 (Fase 1 del curso). Todo en memoria del navegador. | Casi completa; ver [Resumen de la Parte A](#resumen-de-dependencias-parte-a) |
| **B — Arquitectura desacoplada** | Fases B0 a B6 (Fase 2 del curso). Backend FastAPI y SQLite. Ver [plan.md](plan.md) v2. | No iniciada. [Ir a la Parte B](#parte-b--arquitectura-desacoplada-fase-2-del-curso) |

Las tareas pendientes de la Parte A (1.10, Fase 6, parte de la Fase 7 y 8.2, 8.4) **no bloquean** la Parte B. Los escenarios de la Fase 7 que siguen sin verificar se vuelven a cubrir en B5 contra la API.

---

# PARTE A — Prototipo conceptual (Fase 1 del curso)

## Fase 0 — Preparación

- [x] 0.1 Confirmar con el usuario la aprobación del plan y las 5 decisiones por defecto (plan §7).
- [x] 0.2 Cargar la guía `artifact-design` (tokens en `:root`, modo oscuro, layout móvil, título de 2 a 4 palabras).
- [x] 0.3 Definir el archivo de trabajo del prototipo (`prototipo-turnos.html`) y las versiones fijas de React, Babel y Lucide. _(Hecho con variación: el archivo es `index.html` y Lucide va como SVG inline.)_
- [x] 0.4 Definir las constantes de configuración del spec: ventana 2 h, antelación 1 h, horizonte 60 días, grilla 15 min.

**Salida:** archivo vacío con el esqueleto HTML, CDNs y tokens de tema.
**Hecho cuando:** la página carga sin errores en claro y oscuro.

---

## Fase 1 — Dominio puro (`domain/`)

- [x] 1.1 Utilidades de tiempo: sumar minutos, alinear a la grilla, comparar intervalos `[inicio, fin)`.
- [x] 1.2 `overlaps(a, b)`: solapamiento con contigüidad válida (RN-02).
- [x] 1.3 `computeSlots(profesional, servicio, fecha, estado, ahora)`: respeta horario laboral, turnos activos, bloqueos, antelación mínima, horizonte y que el servicio entre antes del fin de jornada (HU-01, EC-01.1 a EC-01.4).
- [x] 1.4 `validateContact(usuario)`: nombre, email, teléfono, email verificado (RN-03).
- [x] 1.5 `canClientCancel(turno, ahora)`: ventana de 2 h con límite exacto inclusivo (RN-01, EC-04.2).
- [x] 1.6 `transition(turno, accion, actor)`: tabla de transiciones y estados terminales (RN-06). _(Hecho con variación: sin función `transition`; la tabla de transiciones está repartida en `completeAppointment`, `markNoShow` y `applyCancel`.)_
- [x] 1.7 `bookAppointment`, `cancelAppointment`, `completeAppointment`, `markNoShow`, `createBlock`, `removeBlock`: cada una devuelve `{ok, estado}` o `{error: CODIGO}` usando el catálogo del spec §7.
- [x] 1.8 `createBlock` con detección de conflictos: lista los turnos afectados y, con confirmación, cancela y bloquea en una sola operación (RN-05, EC-06.2).
- [x] 1.9 Generación de eventos de auditoría y de correos simulados (RN-08, F-13).
- [ ] 1.10 Autoverificación en consola: casos de prueba rápidos de las funciones puras (solapamiento parcial, contiguo, límite 2 h, bloqueo).

**Salida:** módulo de dominio sin dependencias de React.
**Hecho cuando:** los casos de 1.10 pasan en la consola del navegador.

---

## Fase 2 — Datos mock y estado

- [x] 2.1 Semillas relativas a "hoy": 3 profesionales, 5 o 6 servicios (30, 45, 60 min), horario de lunes a viernes.
- [x] 2.2 Dos clientes, uno con email sin verificar (para `EMAIL_NOT_VERIFIED`) y un `ADMIN`.
- [x] 2.3 Unos 12 turnos con estados variados, incluyendo uno a 1 h 59 min y otro a 3 h de "ahora".
- [x] 2.4 1 o 2 bloqueos de ejemplo.
- [x] 2.5 Reloj simulado en el estado (`ahora`), con acciones `+1 h`, `+1 día` y reinicio.
- [x] 2.6 Reducer centralizado que invoca las funciones de la Fase 1 y devuelve errores de dominio sin mutar el estado. _(Hecho con variación: lo cubre `act()` con funciones de dominio puras, sin reducer.)_
- [x] 2.7 `Context` con `dispatch`, usuario activo, rol activo y cola de toasts.
- [x] 2.8 Acción "Reiniciar datos".

**Salida:** `store` funcional con una sola fuente de verdad.
**Hecho cuando:** despachar acciones desde la consola cambia el estado y respeta las reglas.

---

## Fase 3 — Componentes compartidos (`ui/`)

- [x] 3.1 Barra superior: selector Cliente/Administrador, selector de cliente activo, selector Profesional/ADMIN en vista Administrador, reloj simulado y botones de tiempo.
- [x] 3.2 Badges de estado (`CONFIRMADO`, `CANCELADO`, `COMPLETADO`, `AUSENTE`) con color y texto, no solo color.
- [x] 3.3 Modal reutilizable accesible (foco, `Esc`, etiquetas).
- [x] 3.4 Toasts para éxito y para errores de dominio con su código.
- [x] 3.5 Panel lateral colapsable de "Bandeja simulada" (emails de confirmación y cancelación).
- [x] 3.6 Layout responsive con gutters de 16 px y sin scroll horizontal.

**Salida:** estructura de la aplicación con navegación por rol.
**Hecho cuando:** alternar el rol cambia la vista y la barra muestra el contexto correcto.

---

## Fase 4 — Vista Cliente (Flujo 1)

- [x] 4.1 Selector de servicio, profesional y fecha (limitado al horizonte de 60 días) (HU-01).
- [x] 4.2 Grilla de slots libres calculada por `computeSlots`, con estado vacío cuando no hay.
- [x] 4.3 Modal de confirmación con resumen y formulario de contacto editable con validación (HU-02, RN-03).
- [x] 4.4 Envío de la reserva por el reducer, con deshabilitado del botón durante el envío para evitar doble clic (ERR-02.3).
- [x] 4.5 Pantalla de confirmación con servicio, profesional, inicio y fin, y aviso de la política de cancelación (HU-03).
- [x] 4.6 "Mis turnos": próximos e historial, solo del cliente activo (RBAC-02).
- [x] 4.7 Botón Cancelar deshabilitado con tooltip a menos de 2 h, y mensaje `CANCELLATION_WINDOW_EXPIRED` si se fuerza (HU-04).
- [x] 4.8 Mensajes claros para `SLOT_UNAVAILABLE`, `INVALID_CONTACT`, `EMAIL_NOT_VERIFIED`, `INVALID_TIME_RANGE`, y acción "Reenviar verificación".

**Salida:** flujo completo de reserva, confirmación y cancelación del cliente.
**Hecho cuando:** un cliente reserva, ve el turno en "Mis turnos" y el slot desaparece de la grilla.

---

## Fase 5 — Vista Administrador (Flujo 2)

- [x] 5.1 Agenda día/semana y vista de lista, filtrada por profesional según el rol (PROFESIONAL ve lo suyo, ADMIN ve todo) (HU-05).
- [x] 5.2 Detalle del turno con datos de contacto del cliente (RBAC-04).
- [x] 5.3 Acciones sobre turnos: cancelar (modal con motivo obligatorio), completar (desde `inicio`), marcar ausente (desde `fin`), con habilitación según el estado (HU-07, RN-06).
- [x] 5.4 Gestión de bloqueos: crear, listar, quitar; validación de rango y de pasado (HU-06, EC-06.4).
- [x] 5.5 Flujo de conflicto de bloqueo: lista los turnos afectados y pide confirmación con motivo antes de cancelarlos (ERR-06.1, EC-06.2).
- [x] 5.6 Métricas: turnos por período, tasa de cancelación con desglose por quién canceló, tasa de ausentismo, ocupación y top servicios (spec §5).
- [x] 5.7 Panel de auditoría de eventos (RN-08).
- [x] 5.8 Permisos: un PROFESIONAL no puede actuar sobre la agenda ajena; muestra el resultado de RBAC-02.

**Salida:** gestión completa de la agenda por el Administrador.
**Hecho cuando:** una cancelación o bloqueo hecho aquí se refleja de inmediato en la vista Cliente.

---

## Fase 6 — Integración y pulido

- [ ] 6.1 Verificar que las acciones de una vista impactan en la otra sin recargar (requisito 5).
- [ ] 6.2 Revisar el contraste, el foco por teclado, las etiquetas y los estados vacíos.
- [ ] 6.3 Revisar modo oscuro y ancho móvil (375 px).
- [ ] 6.4 Eliminar logs de depuración y código muerto; confirmar que la UI no contiene lógica de reglas.

**Salida:** prototipo estable y consistente.
**Hecho cuando:** ningún error en consola y navegación completa sin pasos rotos.

---

## Fase 7 — Verificación contra el spec

Probar en el navegador integrado y registrar el resultado observado:

- [ ] 7.1 Doble reserva: solapamiento parcial devuelve `SLOT_UNAVAILABLE` (spec §8.1, ERR-02.1).
- [x] 7.2 Concurrencia simulada: dos clientes sobre el mismo slot, solo uno se confirma (spec §8.2, EC-02.2).
- [x] 7.3 Contigüidad: 10:00–10:30 y 10:30–11:00 se aceptan (spec §8.3).
- [x] 7.4 Cancelación dentro de ventana (3 h) aceptada y slot liberado (spec §8.4).
- [x] 7.5 Cancelación a 1 h 59 min rechazada con `CANCELLATION_WINDOW_EXPIRED` (spec §8.5).
- [ ] 7.6 Contacto inválido y email sin verificar bloquean la reserva (spec §8.6, ERR-02.4, ERR-02.5).
- [ ] 7.7 Aislamiento entre clientes en "Mis turnos" (spec §8.7).
- [ ] 7.8 Bloqueo con conflicto lista los turnos y no se crea sin confirmar (spec §8.8, ERR-06.1).
- [ ] 7.9 Administrador cancela fuera de ventana con motivo y notifica al cliente (HU-07).
- [ ] 7.10 Avance del reloj: transiciones a `COMPLETADO`/`AUSENTE` y estados terminales no cancelables (ERR-07.2, ERR-07.3).
- [ ] 7.11 Doble clic en reservar no duplica turnos ni correos (ERR-02.3, EC-03.3).

**Salida:** tabla escenario ↔ resultado observado (pasa / falla).
**Hecho cuando:** todos los escenarios pasan, o las fallas están corregidas y vueltas a probar.

---

## Fase 8 — Publicación y cierre

- [x] 8.1 Publicar el Artifact con título corto, icono genérico y descripción de una oración.
- [ ] 8.2 Entregar el link y la tabla de la Fase 7.
- [x] 8.3 Listar las desviaciones o límites conocidos respecto del spec (por ejemplo, Q-01 fuera de alcance).
- [ ] 8.4 Completar la columna "Código" de la trazabilidad del spec §10.

**Salida:** link del Artifact y reporte de verificación.
**Hecho cuando:** el usuario puede abrir el prototipo y recorrer ambos flujos.

---

## Resumen de dependencias (Parte A)

```
F0 Preparación → F1 Dominio → F2 Estado → F3 UI compartida → F4 Cliente ┐
                                                           → F5 Admin   ┴→ F6 Integración → F7 Verificación → F8 Publicación
```

F4 y F5 pueden avanzar en paralelo una vez cerrada la Fase 3, porque ambas consumen el mismo `store` y no se tocan entre sí.

---

# PARTE B — Arquitectura desacoplada (Fase 2 del curso)

Base: [plan.md](plan.md) v2.0.1 y [spec.md](spec.md) v0.2.1 (INV-03, §11, criterios 9 a 13, decisiones D-06 a D-09).

**Ramas:** el código del backend (`backend/`) se desarrolla en la rama `backend`; la documentación (`spec.md`, `plan.md`, `tareas.md`, `README.md`) y `index.html` continúan en `main`. Las tareas marcadas `[x]` de B0 a B3 corresponden a código que está en la rama `backend`.

**Reglas de trabajo de esta parte:**
- **Grounding:** no se crean tablas, campos, endpoints ni códigos de error que no estén en spec §4.1, §7 y §11 (plan §7).
- **Frontend:** se modifica `index.html` en el lugar; el catálogo, los profesionales y los horarios siguen como datos mock (D-08).
- **Orden SDD:** si una tarea requiere algo que el spec no dice, se detiene y se actualiza primero el spec.
- Las referencias a la Parte A («tarea 1.3», etc.) apuntan a código existente en `index.html` que sirve de modelo.

**Decisión del 2026-11-06 — el backend sigue el spec, no los nombres simplificados del pedido de `main.py`.** El pedido original usaba nombres que no figuran en el spec. Se aplican estas equivalencias y **no** se crea nada de la columna izquierda:

| Pedido de `main.py` | Se usa (spec) | Fuente |
|---|---|---|
| Tabla `turnos` con `cliente_nombre`, `cliente_email`, `servicio`, `fecha_hora`, `estado` | Tabla `turno` con `cliente_id`, `profesional_id`, `servicio_id`, `inicio`, `fin`, `estado`, …; el nombre y el email del cliente viven en `usuario` | spec §4.1 |
| `HORARIO_NO_DISPONIBLE` (409) | `SLOT_UNAVAILABLE` (409) | spec §7 |
| `CANCELACION_FUERA_DE_VENTANA` (409) | `CANCELLATION_WINDOW_EXPIRED` (409) | spec §7 |
| Estado `CANCELADO_CLIENTE` | `CANCELADO`; quién canceló queda en `cancelado_por_id` | spec §4.1 y RN-06 |
| `main.py` único | `main.py` más `dominio.py`, `db.py`, `schema.sql` y `seed.py` | plan §5 |

---

## Fase B0 — Preparación

- [x] B0.1 Crear `backend/` con la estructura de plan §5 (`main.py`, `dominio.py`, `db.py`, `schema.sql`, `seed.py`, `tests/`).
- [x] B0.2 Crear `backend/requirements.txt` con `fastapi`, `uvicorn` y `pytest`, y un entorno virtual local fuera del control de versiones.
- [x] B0.3 Agregar `turnos.db` y el entorno virtual al `.gitignore`.
- [x] B0.4 Definir las constantes de configuración del spec en un solo lugar: `CANCELLATION_WINDOW_HOURS = 2`, antelación 1 h, horizonte 60 días, grilla 15 min.
- [ ] B0.5 Hacer un inventario de `index.html`: qué funciones y vistas tocan turnos (reservar, cancelar, completar, ausente, bloqueo con cancelación en cascada) y cuáles quedan como mock local.
- [x] B0.6 Definir la zona horaria de operación (spec §1.4) como configuración: variable `ZONA_HORARIA`, por defecto `America/Argentina/Buenos_Aires`. Se usa solo para interpretar `HorarioLaboral`; todos los instantes se guardan en UTC.
- [x] B0.7 Documentar el comando de arranque con recarga automática (`uvicorn main:app --reload --port 8000`, ejecutado desde `backend/`) y la URL de Swagger UI (`http://localhost:8000/docs`).

**Salida:** esqueleto del backend y lista de cambios previstos en `index.html`.
**Hecho cuando:** `uvicorn` arranca una app vacía en el puerto 8000. _(Falta B0.5, el inventario de `index.html`.)_

---

## Fase B1 — Capa 3: esquema y datos iniciales (INV-03)

- [x] B1.1 Escribir `schema.sql` con las 6 tablas de spec §4.1 (`usuario`, `servicio`, `turno`, `horario_laboral`, `bloqueo`, `auditoria_evento`) y **exactamente** los atributos del spec.
- [x] B1.2 Agregar los `CHECK` de spec §11.5: `rol`, `estado`, `duracion_min` entre 15 y 480, `dia_semana` entre 0 y 6, `fin > inicio`.
- [x] B1.3 Agregar las claves foráneas, sin `ON DELETE CASCADE` sobre `turno` (spec §4.3).
- [x] B1.4 Agregar el *trigger* anti-solapamiento de `turno` para `estado = 'CONFIRMADO'` por `profesional_id`, con intervalos `[inicio, fin)` (INV-02, contigüidad válida).
- [x] B1.5 Escribir `seed.py`: 3 profesionales, 5 o 6 servicios, 2 clientes (uno con email sin verificar), 1 `ADMIN`, horarios de lunes a viernes, 1 o 2 bloqueos y unos 12 turnos con estados variados, incluyendo uno a 1 h 59 min y otro a 3 h de la carga. `id` fijos y fechas relativas a «hoy». `password_hash` con un valor no verificable.
- [x] B1.6 Verificar que el *trigger* rechaza un `INSERT` solapado hecho directamente en SQL y acepta uno contiguo (criterio 13 y criterio 3).
- [x] B1.7 Crear el esquema automáticamente al iniciar el servidor (`CREATE … IF NOT EXISTS`, desde el evento de arranque de FastAPI) y cargar los datos iniciales solo si `usuario` está vacía. Así `turnos.db` se genera sola y sobrevive a los reinicios (INV-03).
- [x] B1.8 Aclarar en spec §4.1 la convención de `HorarioLaboral.dia_semana` (0 = domingo … 6 = sábado, la misma de `index.html`), porque el spec solo dice «0–6».

**Salida:** `turnos.db` generable con un comando.
**Hecho cuando:** el criterio 13 pasa y el esquema no tiene ninguna tabla ni columna fuera de spec §4.1.

---

## Fase B2 — Capa 2: dominio en Python

- [x] B2.1 `ahora` como parámetro de toda función que dependa del tiempo (D-09).
- [x] B2.2 INV-02: `overlaps` con intervalos `[inicio, fin)` y contigüidad válida; solapamiento con turnos del profesional, con turnos del mismo cliente, con bloqueos y fuera del horario laboral (modelo: tareas 1.1 a 1.3).
- [x] B2.3 INV-01: `can_client_cancel` con la ventana de 2 h y límite exacto permitido (modelo: tarea 1.5).
- [x] B2.4 RN-03: validación de nombre, email, teléfono y email verificado (modelo: tarea 1.4).
- [x] B2.5 RN-04: antelación mínima, grilla, horizonte y cálculo de `fin` en el servidor.
- [x] B2.6 RN-06: transiciones permitidas y estados terminales.
- [x] B2.7 Pruebas unitarias del dominio que cubren la autoverificación pendiente 1.10 (solapamiento parcial, contiguo, 1 h 59 min, 2 h exactas, bloqueo).

**Salida:** `dominio.py` sin dependencias de FastAPI ni de SQLite.
**Hecho cuando:** las pruebas unitarias del dominio pasan.

---

## Fase B3 — Capa 2: acceso a datos y endpoints (spec §11)

- [x] B3.1 `db.py`: una conexión por solicitud con `PRAGMA foreign_keys = ON`, y un manejador de transacciones `BEGIN IMMEDIATE … COMMIT/ROLLBACK`.
- [x] B3.2 `GET /api/turnos` con los filtros opcionales `cliente_id`, `profesional_id` y `estado`, ordenado por `inicio`.
- [x] B3.3 `POST /api/turnos` con el orden de evaluación de spec §11.4: existencia (404), contacto (422/403), tiempo (422), disponibilidad (409). Inserta el `Turno` y el `AuditoriaEvento` `TURNO_CREADO` en la misma transacción.
- [x] B3.4 `POST /api/turnos/{id}/cancelar`: acceso (404), estado (409), ventana INV-01 para el cliente (409), motivo obligatorio para `PROFESIONAL`/`ADMIN` (`422` sin código de dominio, D-07). Actualiza el `Turno` e inserta `TURNO_CANCELADO` en la misma transacción.
- [x] B3.5 Traducir los errores a `{"error": "<CÓDIGO>", "mensaje": "…"}` con el HTTP del catálogo de spec §7; la violación del *trigger* se traduce a `SLOT_UNAVAILABLE`; un fallo de persistencia responde `500` sin persistir nada.
- [x] B3.6 CORS con `CORSMiddleware` (`allow_origins=["*"]`, solo para desarrollo, sin credenciales) y servidor en el puerto 8000.
- [x] B3.7 Pruebas de la API con el cliente de prueba de FastAPI y una base de datos en archivo temporal: criterios 1 a 7, 10, 11 y 12 (más 9 y 13 en B5). _(Criterio 8: no aplica a la Fase 2, porque crear bloqueos no tiene endpoint en spec §11. Se cubre en la Parte A.)_ Resultado: 33 pruebas en `backend/tests/` pasan.
- [x] B3.8 Tipado estricto: anotaciones en todo el backend, modelos Pydantic para la entrada y la salida, y `mypy --strict` sin errores.
- [ ] B3.9 Verificar los 3 endpoints en vivo en Swagger UI (`http://localhost:8000/docs`) con los datos de `seed.py`. _(Verificado por HTTP con `curl`, pero en el puerto 8765: en esta máquina el 8000 estaba ocupado por otro proceso. Falta probarlo a mano en el navegador.)_

**Salida:** backend funcional con los 3 endpoints.
**Hecho cuando:** las pruebas de B3.7 pasan y ningún endpoint, campo ni código de error excede spec §11 y §7.

---

## Fase B4 — Capa 1: `index.html` consume la API

- [ ] B4.1 Definir en `index.html` la URL base `http://localhost:8000` en una sola constante.
- [ ] B4.2 Reemplazar la fuente de verdad de los turnos: cargar con `GET /api/turnos` al iniciar y después de cada escritura.
- [ ] B4.3 Reserva: el modal de confirmación llama a `POST /api/turnos` con `cliente_id`, `servicio_id` e `inicio`; no envía `fin` ni `profesional_id`.
- [ ] B4.4 Cancelación: el cliente y el Administrador llaman a `POST /api/turnos/{id}/cancelar` con `actor_id` y, cuando corresponde, `motivo_cancelacion`.
- [ ] B4.5 Mostrar los errores del backend con su código (`SLOT_UNAVAILABLE`, `CANCELLATION_WINDOW_EXPIRED`, `INVALID_CONTACT`, `EMAIL_NOT_VERIFIED`, `INVALID_TIME_RANGE`, `NOT_FOUND`, `INVALID_STATE_TRANSITION`) y un mensaje claro si el backend no responde.
- [ ] B4.6 Mantener el botón deshabilitado durante el envío para evitar el doble clic (ERR-02.3).
- [ ] B4.7 Conservar como mock local el catálogo, los profesionales y los horarios, con los mismos `id` que `seed.py` (D-08).
- [ ] B4.8 Según el inventario de B0.5: dejar como mock local lo que el contrato no cubre y evitar que modifique turnos de la API; las acciones que mutarían turnos fuera del contrato (completar, ausente, bloqueo con cancelación en cascada) se deshabilitan en la UI con un aviso. _(Criterio a confirmar al llegar a esta tarea.)_
- [ ] B4.9 Retirar del flujo de turnos el reloj simulado (D-09) y quitar el código muerto; la UI no debe contener reglas de negocio.

**Salida:** el flujo reservar → «Mis turnos» → cancelar funciona contra el backend.
**Hecho cuando:** recargar la página conserva los turnos creados y la consola no muestra errores.

---

## Fase B5 — Verificación contra el spec

Registrar el resultado observado de cada escenario (pasa / falla):

- [ ] B5.1 Criterios 1 a 7 de spec §8 contra la API (el 8 no aplica, ver B3.7) (cubre los pendientes de la Fase 7 de la Parte A: 7.1, 7.6, 7.7, 7.8, 7.9 y 7.11 en lo que el contrato incluye).
- [ ] B5.2 Criterio 9: crear un turno, detener y volver a iniciar el backend, y comprobar que el turno sigue (INV-03).
- [ ] B5.3 Criterio 10: forzar un fallo en la escritura de `auditoria_evento` y comprobar el `ROLLBACK`.
- [ ] B5.4 Criterio 11: dos `POST /api/turnos` simultáneos por el mismo slot; uno `201` y uno `409`.
- [ ] B5.5 Criterio 12: cancelación a 3 h aceptada y a 1 h 59 min rechazada con la fila intacta.
- [ ] B5.6 Criterio 13: `INSERT` directo solapado rechazado por la base de datos.
- [ ] B5.7 Revisión del frontend: consola sin errores, modo oscuro y ancho móvil de 375 px.

**Salida:** tabla escenario ↔ resultado observado.
**Hecho cuando:** todos los escenarios pasan, o las fallas están corregidas y vueltas a probar.

---

## Fase B6 — Cierre

- [ ] B6.1 Completar la columna «Código» de la trazabilidad de spec §10 (cubre la tarea 8.4 de la Parte A).
- [ ] B6.2 Actualizar `README.md` (cómo arrancar el backend y abrir `index.html`; el README actual dice que no hace falta backend) y `guia-de-uso.md`.
- [ ] B6.3 Listar las desviaciones y límites conocidos: sin autenticación (D-06), catálogo mock (D-08), reloj real (D-09), CORS abierto.

**Salida:** documentación al día y reporte de verificación.
**Hecho cuando:** otra persona puede clonar el repositorio, arrancar el backend, abrir `index.html` y recorrer el flujo.

---

## Resumen de dependencias (Parte B)

```
B0 Preparación → B1 Esquema → B2 Dominio → B3 Endpoints → B4 Frontend → B5 Verificación → B6 Cierre
```

B1 y B2 pueden avanzar en paralelo: el dominio no depende de la base de datos hasta B3.
