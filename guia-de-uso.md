# guia-de-uso.md — Turnos Pro: funcionalidades y guía de pruebas

| Campo | Valor |
|---|---|
| Aplicación | [index.html](index.html) (archivo único, se abre con doble clic) |
| Versión publicada | https://claude.ai/artifact/JUv3cgvTQv1i2vxf3DK5z2 (privada, la compartís desde el menú Share) |
| Base normativa | [spec.md](spec.md) · [historias-de-usuario.md](historias-de-usuario.md) |
| Requiere | Internet (React y Tailwind se cargan desde CDN). Todo el estado vive en memoria. |

> **Aviso (Fase 2).** Esta guía describe la versión de la **Fase 1**, con todo en memoria y reloj simulado. Desde la Fase 2 `index.html` guarda los turnos en SQLite a través del backend, y cambia lo siguiente:
>
> - **Requiere el backend levantado** (ver el [README](README.md#fase-2--backend-con-persistencia-real-en-construcción)). Sin él, la página muestra el aviso `API_UNAVAILABLE`.
> - **El reloj simulado ya no existe:** los botones `+1 min`, `+15 min`, `+1 h` y `+1 día` se retiraron y la barra muestra la *hora actual*. Las pruebas de esta guía que dependen de avanzar el reloj (por ejemplo las que usan `+1 min` o `+1 h`) **no se pueden hacer** en la interfaz.
> - **Los turnos de ejemplo cambiaron:** vienen del `seed.py` del backend y sus horarios son relativos al momento de la carga inicial, no a las 07:30.
> - **Reiniciar datos** solo reinicia lo local (emails, auditoría, bloqueos y servicios de ejemplo). Los turnos no se borran.
> - **Completar, Ausente, verificar email y bloquear un rango que tiene turnos** responden `NOT_IMPLEMENTED`: el contrato de la Fase 2 no tiene esos endpoints.
> - **Reservar y cancelar** funcionan contra la API y recargar con F5 conserva los datos. Los rechazos (`SLOT_UNAVAILABLE`, `CANCELLATION_WINDOW_EXPIRED`, etc.) vienen del backend.
>
> La guía se reescribirá completa en la tarea B6.2 de [tareas.md](tareas.md).

---

## 1. Qué es y cómo funciona

Turnos Pro es un prototipo de gestión de turnos. Tiene dos vistas sobre **los mismos datos**: lo que hacés en una se ve de inmediato en la otra.

Principio de diseño: **la pantalla nunca decide si algo está permitido**. Cada acción se envía a un módulo de dominio que aplica las reglas del spec y responde con un código de error (`SLOT_UNAVAILABLE`, `CANCELLATION_WINDOW_EXPIRED`, etc.). Por eso existe el **Modo auditoría**: habilita botones que la pantalla normalmente bloquea, para comprobar que el dominio rechaza igual la acción.

### Barra superior

| Control | Qué hace |
|---|---|
| **Vista Cliente / Vista Administrador** | Cambia de rol. |
| **Selector de usuario** | En Cliente: elige a Lucía, Martín o Sofía. En Administrador: elige Admin General o un profesional. |
| **Modo auditoría** | Habilita acciones normalmente deshabilitadas y muestra turnos fuera de tu alcance, para probar permisos y reglas. |
| **Reloj simulado** | Hora del sistema. Botones `+1 min`, `+15 min`, `+1 h`, `+1 día`. Todas las reglas de tiempo usan este reloj. |
| **Bandeja** | Panel con los emails simulados (confirmación, cancelación, verificación). Tiene el interruptor "Simular caída del servicio de email". |
| **Reiniciar datos** | Vuelve al estado inicial. Úsalo entre pruebas. |

### Datos iniciales

El reloj arranca a las **07:30 del primer día hábil** desde hoy (si hoy es fin de semana, el lunes). Ese día se llama **"hoy"** en esta guía. "Mañana" es el siguiente día hábil.

**Usuarios**

| Usuario | Rol | Nota |
|---|---|---|
| Lucía Fernández | Cliente | Email verificado |
| Martín Gómez | Cliente | **Email sin verificar** |
| Sofía Ruiz | Cliente | Email verificado |
| Admin General | ADMIN | Ve y gestiona todas las agendas |
| Dra. Ana Martínez | PROFESIONAL | Solo su agenda |
| Dr. Bruno Salas | PROFESIONAL | Solo su agenda |
| Lic. Carla Ibáñez | PROFESIONAL | Solo su agenda |

**Servicios y horarios** (lunes a viernes)

| Servicio | Profesional | Duración | Jornada del profesional |
|---|---|---|---|
| Consulta general | Ana | 30 min | 09:00–13:00 y 14:00–18:00 |
| Control anual | Ana | 60 min | igual |
| Sesión de terapia | Bruno | 45 min | 10:00–14:00 y 15:00–19:00 |
| Evaluación inicial | Bruno | 60 min | igual |
| Asesoría nutricional | Carla | 30 min | 09:00–13:00 |
| Plan alimentario | Carla | 45 min | igual |

**Turnos y bloqueos preparados para las pruebas**

| Cuándo | Turno / bloqueo | Para qué sirve |
|---|---|---|
| Hoy 09:30 | Lucía · Consulta general · Ana | Está a **exactamente 2 h**: límite de la regla de cancelación |
| Hoy 10:30 | Sofía · Asesoría nutricional · Carla | Está a 3 h: cancelable |
| Hoy 11:00 | Martín · Sesión de terapia · Bruno | |
| Hoy 15:00 | Lucía · Control anual · Ana | |
| Mañana 10:00 | Sofía · Consulta general · Ana | |
| Mañana 11:00 | Lucía · Evaluación inicial · Bruno | Se usa en la prueba de conflicto de bloqueo |
| Mañana 12:00–13:00 | Bloqueo de Ana ("Trámite personal") | |
| En 2 días hábiles 09:00 | Martín · Asesoría nutricional · Carla | |
| En 2 días hábiles 10:00–19:00 | Bloqueo de Bruno ("Capacitación") | |
| En 3 días hábiles 15:30 | Lucía · Control anual · Ana | |
| Días anteriores | 7 turnos completados, ausentes y cancelados | Alimentan las métricas y el historial |

---

## 2. Funcionalidades

### 2.1 Vista Cliente

1. **Perfil:** nombre, email, teléfono y estado de verificación. Si el email no está verificado aparece el botón **Verificar**, que manda un enlace a la Bandeja.
2. **Elegir servicio:** tarjetas con profesional, duración y precio de referencia. Los servicios desactivados aparecen como "no disponible" y no se pueden elegir.
3. **Elegir fecha y horario:** selector de fecha con flechas. Muestra solo los horarios **libres**, agrupados en Mañana y Tarde, cada 15 minutos. Excluye turnos confirmados, bloqueos, horario fuera de jornada, la antelación mínima de 1 h y todo lo posterior a 60 días.
4. **Confirmar reserva:** ventana con el resumen y el formulario de contacto (editable). Valida los datos y confirma o muestra el error.
5. **Pantalla de confirmación:** servicio, profesional, fecha, horario y hasta qué hora se puede cancelar. Se envía además un email a la Bandeja.
6. **Mis turnos:** pestañas **Próximos** e **Historial**. Cada turno confirmado indica hasta cuándo es cancelable. El botón **Cancelar** se bloquea (con candado) si faltan menos de 2 horas.

### 2.2 Vista Administrador

Muestra siempre quién está actuando y su alcance. **ADMIN** ve todas las agendas (con filtro por profesional). **PROFESIONAL** ve solo la suya.

1. **Agenda:** vistas Semana, Día y Lista (esta con filtro por estado). Los bloqueos se ven rayados. Al hacer clic en un turno se abre el detalle.
2. **Detalle del turno:** datos del cliente (solo dentro del alcance) y las acciones **Completar**, **Ausente** y **Cancelar…** (con motivo obligatorio). Cada acción se habilita según el estado del turno y el reloj.
3. **Métricas** (Semana, Mes o Todo): turnos del período, tasa de cancelación (con desglose por quién canceló), tasa de ausentismo, ocupación, turnos por día y servicios más reservados.
4. **Bloqueos:** crear un rango por profesional, con motivo. Si el rango pisa turnos confirmados, se abre una ventana de conflicto. Los bloqueos que se tocan se fusionan en uno. Se pueden eliminar.
5. **Servicios:** activar o desactivar. Un servicio con turnos futuros activos no se puede desactivar.
6. **Auditoría:** registro de quién hizo qué y cuándo.

---

## 3. Guía de pruebas paso a paso

> **Antes de cada prueba**, pulsá **Reiniciar datos** salvo que se indique lo contrario. Los códigos de error aparecen en un aviso verde/rojo abajo a la derecha, con su código y el número HTTP.

### Bloque A — Reserva (Flujo 1)

**A1. Reserva exitosa** · `HU-02`, `HU-03`
1. Vista Cliente, usuaria **Lucía**.
2. Elegí **Asesoría nutricional** (Carla). Fecha: mañana (flecha `>`).
3. Elegí el horario **10:00**.
4. Dejá los datos como están y pulsá **Confirmar turno**.
- **Esperado:** pantalla "Turno confirmado" con fecha, horario y hora límite de cancelación. En **Mis turnos → Próximos** aparece el turno. Ese horario desaparece de la grilla. En **Bandeja** hay un email "Turno confirmado".

**A2. El horario se refleja en la otra vista**
1. Tras A1, cambiá a **Vista Administrador** → Admin General → **Agenda**, semana actual.
- **Esperado:** el turno de Lucía está en la agenda de Carla de mañana.

**A3. Turnos contiguos son válidos** · `RN-02`
1. Lucía, **Consulta general** (30 min, Ana), mañana. Mirá la grilla: el turno de Sofía ocupa 10:00–10:30.
2. Reservá **10:30**.
- **Esperado:** se confirma (un turno que empieza justo cuando termina otro es válido).

**A4. Los horarios ocupados no se ofrecen** · `HU-01`
1. Lucía, **Consulta general**, mañana.
- **Esperado:** no aparecen **09:45, 10:00 ni 10:15**, porque un servicio de 30 min en cualquiera de esos inicios pisaría el turno de Sofía (10:00–10:30). Tampoco aparecen **11:45 a 12:45**, por el bloqueo de Ana de 12:00 a 13:00. Sí aparecen 09:00, 09:30, 10:30 y 11:00.

**A5. Datos de contacto inválidos** · `RN-03`, `ERR-02.4`
1. Lucía, cualquier servicio, cualquier horario libre.
2. En el teléfono escribí `123` y pulsá **Confirmar turno**.
- **Esperado:** `INVALID_CONTACT` con el mensaje bajo el campo Teléfono. No se crea el turno.
3. Probá también un email sin `@` o un nombre de una sola letra.

**A6. Email sin verificar** · `ERR-02.5`
1. Elegí a **Martín** (aparece "email sin verificar").
2. Intentá reservar cualquier horario libre.
- **Esperado:** `EMAIL_NOT_VERIFIED` con botones "Enviar enlace de verificación" y "Abrir bandeja".
3. Pulsá **Enviar enlace de verificación**, abrí la **Bandeja** y pulsá **Confirmar mi email**.
4. Volvé a pulsar **Confirmar turno**.
- **Esperado:** ahora se confirma.

**A7. Cambiar el email vuelve a exigir verificación**
1. Lucía, reservar un horario libre. En el email escribí `otro@mail.test`.
- **Esperado:** `EMAIL_NOT_VERIFIED` (el email nuevo no está verificado). Verificalo desde la Bandeja y reintentá.

**A8. Concurrencia: dos clientes, el mismo horario** · `RN-02`, `EC-02.2`
1. Lucía, un horario libre. En el modal abrí **Simulaciones de auditoría** y tildá "Otro cliente reserva este slot… antes que yo".
2. Pulsá **Confirmar turno**.
- **Esperado:** aviso "Sofía Ruiz reservó este horario un instante antes". Tu reserva falla con `SLOT_UNAVAILABLE`. Queda **un solo** turno en ese horario (verificalo en la agenda del Administrador).

**A9. Doble clic** · `ERR-02.3`
1. Lucía, un horario libre. Tildá "Enviar la reserva dos veces".
2. Pulsá **Confirmar turno**.
- **Esperado:** la primera reserva se confirma; la segunda es rechazada con `SLOT_UNAVAILABLE`. Hay un solo turno y un solo email de confirmación.

**A10. Un cliente no puede tener dos turnos a la vez** · `ERR-02.6`
1. Lucía tiene **mañana 11:00–12:00** con Bruno. Reservá con Ana (**Consulta general**) mañana a las **11:15**.
- **Esperado:** `SLOT_UNAVAILABLE` con el mensaje "Ya tenés un turno confirmado que se solapa".

**A11. Antelación mínima** · `RN-04`
1. Vista Cliente, fecha **hoy**, **Consulta general**.
- **Esperado:** el primer horario libre es 09:00 (el reloj marca 07:30).
2. Pulsá **+1 h** (08:30).
- **Esperado:** el horario de las 09:00 desaparece (faltan menos de 1 h).

**A12. Horizonte máximo de 60 días** · `EC-01.3`
1. Escribí en el campo de fecha una fecha de más de 60 días.
- **Esperado:** aviso `INVALID_TIME_RANGE` y sin horarios. Una fecha pasada da el mismo error.

**A13. Un servicio desactivado deja de ofrecerse** · `ERR-02.10`
1. Vista Administrador → **Lic. Carla Ibáñez** → **Servicios** → desactivar **Plan alimentario**.
2. Volvé a Vista Cliente.
- **Esperado:** el servicio figura como "no disponible" y no se puede elegir.

### Bloque B — Cancelación del cliente (Flujo 1)

**B1. Cancelación dentro de la ventana** · `HU-04`, `8.4`
1. Usuaria **Sofía**. Su turno de hoy 10:30 dice "Cancelable hasta las 08:30".
2. Pulsá **Cancelar** → **Sí, cancelar**.
- **Esperado:** pasa a **Historial** como CANCELADO. El horario vuelve a quedar libre y llega un email de cancelación.

**B2. Límite exacto de las 2 horas** · `EC-04.2`
1. Usuaria **Lucía**. Su turno de hoy 09:30 dice "faltan 2 h 0 min" y **Cancelar** está habilitado.
- **Esperado:** a exactamente 2 h se puede cancelar. **No lo canceles** todavía.

**B3. Una hora y 59 minutos: bloqueado** · `RN-01`, `8.5`
1. Siguiendo B2 (sin cancelar), pulsá **+1 min**.
- **Esperado:** el botón **Cancelar** del turno de las 09:30 pasa a estar bloqueado, con candado, y el texto indica que faltan menos de 2 horas.
2. Tildá **Modo auditoría** y pulsá **Cancelar** → **Sí, cancelar**.
- **Esperado:** el dominio rechaza con `CANCELLATION_WINDOW_EXPIRED` (HTTP 409). El turno sigue CONFIRMADO. Es la prueba de que la regla no depende de la pantalla.

**B4. No se puede ver ni cancelar turnos ajenos** · `RBAC-02`, `8.7`
1. Usuaria **Lucía**, **Modo auditoría** activado.
2. En el panel **Turnos ajenos (bypass de UI)** pulsá **Intentar cancelar** sobre cualquiera.
- **Esperado:** `NOT_FOUND` (HTTP 404). Responde igual que si el turno no existiera.

### Bloque C — Gestión de agenda y cancelación (Flujo 2)

**C1. Ver la agenda**
1. Vista Administrador → **Admin General** → **Agenda**.
2. Probá **Semana**, **Día** y **Lista**; navegá con las flechas y **Hoy**; en Lista filtrá por estado.
3. Cambiá el filtro de profesional.
- **Esperado:** cada vista muestra los turnos y bloqueos del alcance elegido.

**C2. Cancelar con motivo (dentro de la ventana normal)** · `HU-07`
1. Admin General → Agenda → turno de **Sofía mañana 10:00** → **Cancelar…**.
2. Dejá el motivo vacío y pulsá **Cancelar turno y notificar**.
- **Esperado:** `REASON_REQUIRED` (el motivo es obligatorio). El turno sigue CONFIRMADO.
3. Escribí "Imprevisto médico" y repetí.
- **Esperado:** el turno pasa a CANCELADO con ese motivo. En la **Bandeja** hay un email para Sofía con el motivo. En **Auditoría** hay un registro `TURNO_CANCELADO`. En la Vista Cliente (Sofía → Historial) se ve "Cancelado por el profesional · Imprevisto médico".

**C3. El Administrador cancela fuera de la ventana de 2 h** · `RN-01` (excepción)
1. Reiniciá datos y pulsá **+1 min** en el reloj, para que al turno de **Lucía hoy 09:30** le queden menos de 2 h.
2. Admin General → Agenda → abrí ese turno → **Cancelar…**. Aparece el aviso de que se aplica la excepción de RN-01.
3. Ingresá un motivo y confirmá.
- **Esperado:** se cancela aunque falten menos de 2 horas, y se notifica a Lucía.

**C4. Completar y marcar ausente según el reloj** · `RN-06`
1. Reiniciá datos. Admin General → turno de **Lucía hoy 09:30–10:00**.
- **Esperado:** **Completar** y **Ausente** están bloqueados (el turno no empezó).
2. Pulsá **+1 h** dos veces (09:30). **Completar** se habilita; **Ausente** sigue bloqueado.
3. Pulsá **+15 min** dos veces (10:00). Ahora **Ausente** se habilita.
4. Completá el turno.
- **Esperado:** estado COMPLETADO. Ya no admite más cambios.

**C5. Estados finales no se modifican** · `ERR-07.2`
1. **Modo auditoría** activado. Abrí un turno del pasado, por ejemplo uno COMPLETADO, y pulsá **Cancelar…** con un motivo.
- **Esperado:** `INVALID_STATE_TRANSITION` (HTTP 409).
2. Con el modo auditoría, intentá **Completar** un turno que aún no comenzó.
- **Esperado:** `INVALID_STATE_TRANSITION`.

**C6. Un profesional ve solo su agenda** · `RBAC-01`, `RBAC-04`
1. Elegí **Dra. Ana Martínez** como usuario.
- **Esperado:** el aviso dice "Alcance: solo tu agenda", no aparece el filtro de profesional, y solo se ven turnos de Ana.
2. Activá **Modo auditoría**.
- **Esperado:** aparecen también turnos de otros profesionales con la leyenda "Fuera de tu alcance". Al abrirlos, el cliente y el contacto dicen "Sin acceso (RBAC-04)".
3. Abrí uno de otro profesional → **Cancelar…** → escribí un motivo → confirmá.
- **Esperado:** `NOT_FOUND` (HTTP 404).

### Bloque D — Bloqueos y servicios

**D1. Crear un bloqueo libre y ver su efecto** · `HU-06`
1. Admin General → **Bloqueos**. Profesional: **Dra. Ana**. Elegí una fecha con horarios libres, por ejemplo mañana 14:00 a 16:00, motivo "Capacitación".
2. Pulsá **Crear bloqueo**.
- **Esperado:** aparece en "Bloqueos vigentes" y rayado en la agenda.
3. Vista Cliente → **Consulta general** → esa fecha.
- **Esperado:** no hay horarios entre 14:00 y 16:00.
4. Volvé y eliminá el bloqueo con el ícono de papelera.
- **Esperado:** los horarios vuelven a aparecer.

**D2. Conflicto de bloqueo con turnos** · `RN-05`, `8.8`
1. Admin General → **Bloqueos**. Profesional: **Dr. Bruno Salas**. Rango: mañana **10:30 a 12:30**, motivo "Reunión".
2. Pulsá **Crear bloqueo**.
- **Esperado:** se abre "Conflicto con turnos confirmados" con el turno de Lucía de las 11:00. **No** se creó el bloqueo.
3. Pulsá **No bloquear** y comprobá que no hay un bloqueo nuevo.
4. Repetí y pulsá **Cancelar turnos y bloquear**.
- **Esperado:** el turno de Lucía pasa a CANCELADO, se crea el bloqueo, y llega un email de cancelación a Lucía con el motivo.

**D3. Rangos inválidos** · `EC-06.4`
1. En **Bloqueos**, poné "Hasta" anterior o igual a "Desde".
- **Esperado:** `INVALID_TIME_RANGE`.
2. Poné un rango que ya pasó (por ejemplo, ayer).
- **Esperado:** `INVALID_TIME_RANGE`.

**D4. Bloqueos que se tocan se fusionan** · `EC-06.5`
1. Creá un bloqueo para Carla en un día libre, 10:00–12:00. Creá otro de 11:00–13:00.
- **Esperado:** en "Bloqueos vigentes" queda **uno solo**, de 10:00 a 13:00.

**D5. Un profesional no bloquea la agenda ajena**
1. Elegí a **Ana** como usuario. En **Bloqueos** el selector de profesional solo ofrece a Ana.

**D6. No se desactiva un servicio con turnos futuros** · `RN-07`
1. Elegí **Ana** → **Servicios** → **Desactivar** "Consulta general".
- **Esperado:** `SERVICE_HAS_ACTIVE_BOOKINGS` (HTTP 409).

### Bloque E — Métricas, auditoría y emails

**E1. Métricas**
1. Admin General → **Métricas**. Recorré **Semana actual**, **Mes actual** y **Todo**.
2. Anotá la "Tasa de cancelación". Cancelá un turno (C2) y volvé.
- **Esperado:** los números cambian y el desglose por quién canceló suma el turno nuevo.
3. Elegí **Ana** como usuario: las métricas se calculan solo con su agenda.

**E2. Auditoría** · `RN-08`
1. Realizá varias acciones (reservar, cancelar, bloquear) y abrí la pestaña **Auditoría**.
- **Esperado:** cada acción figura con instante, actor, rol, acción y detalle. Un profesional solo ve los eventos de su agenda.

**E3. Falla del servicio de email** · `ERR-03.1`
1. Abrí la **Bandeja** y tildá "Simular caída del servicio de email".
2. Reservá un turno con Lucía.
- **Esperado:** la reserva se confirma igual. El email aparece como **Pendiente · reintento**, y el botón Bandeja muestra "(1 pend.)".
3. Destildá la caída.
- **Esperado:** el email pasa a **Enviado**.

---

## 4. Escenarios del spec y dónde probarlos

| Escenario del spec (§8) | Prueba en la interfaz |
|---|---|
| 1. Doble reserva por solapamiento | A8 (y A10 para el mismo cliente) |
| 2. Concurrencia sobre el mismo slot | A8 |
| 3. Turnos contiguos | A3 |
| 4. Cancelación dentro de la ventana | B1 |
| 5. Cancelación fuera de la ventana | B3 |
| 6. Contacto inválido | A5, A6, A7 |
| 7. Aislamiento entre clientes | B4 |
| 8. Bloqueo con conflicto | D2 |

| Regla | Pruebas |
|---|---|
| RN-01 Ventana de cancelación | B2, B3, C3 |
| RN-02 Sin solapamiento | A3, A4, A8, A9, A10 |
| RN-03 Contacto válido | A5, A6, A7 |
| RN-04 Integridad temporal | A11, A12 |
| RN-05 Bloqueos | D1, D2, D4 |
| RN-06 Ciclo de vida | C4, C5 |
| RN-07 Catálogo | A13, D6 |
| RN-08 Auditoría | C2, E2 |
| RBAC | B4, C6, D5 |

---

## 5. Pruebas avanzadas desde la consola del navegador

Abrí las herramientas de desarrollo (F12) y usá la consola. La app expone `window.__store` con el estado y el dominio.

```js
// Ver el estado actual
__store.get().turnos.length

// Reservar saltándote la pantalla (horario fuera de grilla: INVALID_TIME_RANGE)
const g = __store.get(), D = __store.Domain, t = g.turnos.find(x => x.id === 't12');
const u = g.users.find(x => x.id === 'c1');
__store.act(D.bookAppointment, {
  actor: { id: 'c1', role: 'CLIENTE' }, clienteId: 'c1', servicioId: 's1',
  inicio: t.inicio + 7 * 60000,
  contacto: { nombre: u.nombre, email: u.email, telefono: u.telefono }
})
```

Las funciones del dominio disponibles en `__store.Domain` son: `computeSlots`, `bookAppointment`, `cancelAppointment`, `completeAppointment`, `markNoShow`, `createBlock`, `removeBlock`, `toggleService`, `sendVerification`, `verifyEmail`, `advanceClock`, `setEmailDown` y `computeMetrics`. Cada una devuelve `{ ok, data }` o `{ error: { code, http, message, details } }`.

---

## 6. Alcance y límites conocidos

- **No hay persistencia:** al recargar la página, el estado vuelve al inicial.
- **Sin reserva en nombre de un cliente:** el spec lo permite al ADMIN, pero el prototipo no lo implementa.
- **Sin cambio de horario laboral:** definir o reducir la jornada con turnos ya reservados (Q-01 de las historias) queda fuera. La jornada es fija en los datos.
- **Sin alta de servicios:** solo se activan o desactivan los existentes.
- **Emails simulados:** no se envía nada real. Se leen en la Bandeja.
- **El rol se elige con un selector:** no hay inicio de sesión real. Sirve para auditar permisos, no para autenticar.
- **La concurrencia es simulada:** el prototipo procesa las acciones una detrás de otra, lo que equivale a la garantía de atomicidad del spec. En un sistema real la garantía debe estar en la base de datos (restricción de exclusión por rango).
- **Códigos extra respecto al spec:** `SERVICE_UNAVAILABLE` (servicio desactivado, HTTP 409) y `REASON_REQUIRED` (motivo obligatorio, HTTP 422) no figuran en el catálogo de errores del spec §7. Conviene agregarlos.
