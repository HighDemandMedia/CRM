# Auditoría Senior Engineering — CRM principal

Seguimiento: [correcciones y verificación del 1 de octubre](2026-10-01-main-audit-fixes.md). Los resultados siguientes se conservan como evidencia del estado auditado originalmente.

Fecha: 30 de septiembre de 2026. Repositorio: `HighDemandMedia/CRM`, rama `main`, HEAD `fd6e619300f2c39e1f58cdbffbc9d4fa2633cee3`, **incluyendo los cambios locales pendientes** de separación del laboratorio y recordatorios. Este informe describe ese árbol local; no acredita lo que está desplegado en Render.

## Dictamen

**Mantener el CRM en pruebas controladas. No aprobar todavía su apertura a clientes reales ni publicar esta revisión sin estabilización.** La arquitectura es adecuada para continuar: no hace falta reescribirla ni convertirla en microservicios. Hay un defecto funcional reproducido en PostgreSQL que afecta a usuarios con permisos configurados, riesgos en el ciclo de vida de adjuntos y una validación automatizada que todavía no permite aprobar una publicación con confianza.

La separación de Review funciona en los límites comprobados: sus rutas administrativas ya no están disponibles, ni siquiera para el owner, y sus trabajos programados se retiraron. Eso reduce superficie y trabajo innecesario, pero no corrige automáticamente los problemas del producto activo.

No se demostró una fuga entre organizaciones ni un bypass de autenticación durante esta revisión. Eso no equivale a certificar que no existen vulnerabilidades.

## Analysis — Alcance y arquitectura

Backend monolítico modular Django 6.1.1 / DRF 3.18.0, frontend separado Svelte 5.57.0 / SvelteKit 2.70.3 / Vite 8.2.2. API, Celery Worker y Scheduler comparten dominio y base de datos. PostgreSQL 16.15 local, psycopg 3.3.5, Redis y almacenamiento configurable para adjuntos; Gmail y Calendar son proveedores externos. Son procesos/contenedores separados, no microservicios independientes.

Se revisaron autenticación, invitaciones, permisos, aislamiento, contactos, empresas, negocios, tareas, calendario, informes, adjuntos, notificaciones, formularios web, Google, migraciones, dependencias y configuración de CI/despliegue. Se siguieron rutas UI → API → dominio → persistencia donde correspondía. La lectura manual fue orientada a riesgo, no una inspección de cada línea.

Fuera de la certificación: aplicación móvil, funcionalidad interna del laboratorio, configuración real de Render/AWS/Google, rendimiento bajo carga online, recuperación de backups, auditoría jurídica de licencias y pentest externo. No se enviaron correos ni se modificaron registros de producción.

Los modelos y migraciones históricos permanecen para conservar datos y compatibilidad. La extracción es una separación de producto, rutas y trabajos; no significa que se haya borrado toda referencia histórica. El laboratorio está fuera del repositorio/contexto de build principal.

## Verification — Resultados nuevos

| Comprobación | Resultado |
|---|---|
| Backend completo, SQLite | **3.474 pasan, 236 fallan, 21 omitidas** |
| Frontend, Vitest | **399 pasan, 4 fallan**, de 403 |
| PostgreSQL sin superusuario/BYPASSRLS: distribución, recordatorios y formularios de contacto | **89 pasan** |
| PostgreSQL sin superusuario/BYPASSRLS: roles, permisos ampliados, contraseñas, Google, informes, adjuntos, borrado y asociaciones | **141 pasan, 12 fallan** |
| Selección existente `postgres_only` | **4 pasan, 1 falla**: el caso de token/Leads encuentra la ruta retirada |
| Limpieza de conexiones PostgreSQL reutilizadas | **3 pasan** |
| Reproducciones adicionales de fallos de adjuntos, con almacenamiento en memoria | **2 confirman los defectos** descritos en M04 |
| Preflight CORS, PostgreSQL local | Confirma que queda contexto de organización en la conexión; se limpia al terminar la prueba |
| Svelte check | **0 errores, 0 advertencias** |
| Build de producción frontend | **Pasa** |
| `makemigrations --check --dry-run` | **No changes detected** |
| Ruff | **280 hallazgos**: 111 imports, 154 estilo/ubicación y 15 código sin uso |
| Ruff format | **171 archivos** necesitan formato; 540 conformes |
| ESLint | **5 errores, 280 advertencias** |
| Dependencias Python, export congelado sin desarrollo + pip-audit | **69 paquetes, 16 avisos en 2 paquetes** |
| Dependencias frontend, lockfile contra registro oficial npm | **299 nombres, 3 avisos en brace-expansion** |

Las selecciones se solapan: no sumar sus aprobados como pruebas únicas. Las pruebas de Google simulan al proveedor; no verifican una autorización real ni entrega online. La comprobación de migraciones compara modelos y archivos, no confirma que Render haya aplicado la migración de recordatorios. El build Docker aprobado durante la separación anterior es evidencia previa; esta auditoría reejecutó el build frontend, no reconstruyó todas las imágenes.

### Interpretación de los fallos

- Muchos casos todavía llaman a Leads, Solutions, tokens o configuración avanzada retirada. Hay 158 comparaciones explícitas que reciben 404 donde esperaban otro código, pero no se presupone que todas sean inocuas.
- Otros esperan reglas antiguas: borrar por ser quien subió el adjunto, marca BottleCRM en correos, propiedades obligatorias al crear, cierre de negocios e historial. Deben reconciliarse con las reglas actuales, sin debilitar permisos para conseguir verde.
- Dos pruebas de consultas de tareas esperan 12 y observan 13, tanto con pocas como con más filas. Ese resultado **no prueba un N+1**.
- El test que señala `SecurityAuditLog` en `role_views.py` detecta una referencia nueva; la inspección encontró escrituras de auditoría con organización explícita, no una lectura expuesta a clientes.
- En la selección PostgreSQL ampliada, **6 fallos reproducen SQL incompatible en flujos activos** (M01). Los otros 6 corresponden a preparación/lectura de pruebas sin restaurar correctamente el contexto RLS: cinco intentan crear datos de otra organización y uno lee la conexión Google después de que la tarea limpie el contexto. No demuestran que Calendar o Google hayan perdido esos datos.

## Hallazgos priorizados

P1: bloquear publicación a clientes hasta resolver/verificar. P2: estabilización antes de ampliar uso. P3: mantenimiento o definición pendiente. Son prioridades de ingeniería, no puntuaciones CVSS.

### M01 · P1 · Usuarios con permisos configurados pueden recibir 500 al editar contactos o cancelar citas

**Reproducido en PostgreSQL.** `common.rbac.scoped()` y `calendar_scoped()` añaden `DISTINCT` para alcances propio/equipo. Después, `Contact.save()` y la actualización de citas aplican `select_for_update()` sobre esas consultas. PostgreSQL rechaza esa combinación; SQLite no ejecuta ese bloqueo y las pruebas equivalentes allí pasan. [Restricción documentada por PostgreSQL](https://www.postgresql.org/docs/current/sql-select.html#SQL-DISTINCT).

Evidencia: `backend/common/rbac.py:216`, `:264`, `:590`; `backend/contacts/models.py:151`; `backend/common/views/sales_appointment_views.py:542`. Reproducciones: `test_manager_can_open_and_edit_teammates_contact`, `test_manager_owner_assignment_is_limited_to_team`, `test_replace_contact_preserves_omitted_owner`, dos variantes de `test_specific_actions_cannot_bypass_via_standard_edit` y `test_calendar_create_cancel_and_delegate_are_separate`.

**Impacto:** una cuenta administradora puede funcionar y ocultar que un miembro/manager autorizado no puede completar una operación cotidiana. No es un problema que se solucione aumentando recursos de Render.

**Corrección propuesta:** mantener autorización y filtro de organización, obtener el conjunto permitido mediante subconsulta/`Exists`, y bloquear filas de una consulta exterior sin `DISTINCT`. Revisar también los bloqueos de empresas, asociaciones, movimientos de tareas/negocios y borrado de registros: usan patrones relacionados, aunque no se reprodujeron todos en esta revisión. No quitar el filtro de permisos para solucionar el SQL.

**Cierre:** casos anteriores en verde con PostgreSQL y rol sin BYPASSRLS, incluyendo denegaciones, concurrencia y los alcances propio/equipo/organización.

### M02 · P1 · La validación global todavía no es un criterio fiable para publicar

**Confirmado por ejecución.** Persisten fallos de pruebas, lint y formato. La limpieza trasladó funciones, pero dejó casos de prueba que todavía las esperan. El caso PostgreSQL del token contra Leads falla antes de comprobar su propósito. El workflow contiene un trabajo PostgreSQL completo: no falta por completo ese motor en CI; falta recuperar una ejecución global verde y comprobar que sea obligatoria para publicar.

Evidencia: `.github/workflows/tests.yml:188`, `:206`, `:223`, `:331`; `backend/common/tests/test_pat_auth.py:163`. Los cuatro fallos frontend están en historial de contactos y contratos de etapas de contactos.

**Corrección propuesta:** clasificar fallos por contrato retirado, fixture y defecto; mover las pruebas exclusivas de Review al laboratorio, conservar en main pruebas de rutas cerradas y mantener todas las denegaciones de permisos. Ejecutar las pruebas de RLS en un trabajo independiente para que otros fallos no impidan su ejecución. Exigir checks antes de integrar/desplegar.

**Cierre:** pruebas del producto activo, lint, formato y builds verdes; excepciones documentadas y limitadas, no omisiones generales.

### M03 · P1 · Dependencias bloqueadas con avisos públicos sin resolver

**Escaneo actualizado en esta auditoría; explotación en el CRM no demostrada.**

| Paquete | Versión | Avisos | Versiones de corrección indicadas |
|---|---|---:|---|
| PyJWT | 2.13.0 | 13 | 2.14.0 para la mayoría, 2.15.0 para otro; un aviso no declara corrección |
| urllib3 | 2.7.0 | 3 | 2.8.0 |
| brace-expansion | 5.0.9 | 3 | Cubrir los tres rangos requiere al menos 5.0.12 en esta rama |

Evidencia: `backend/uv.lock:1326`, `:1706`; `frontend/pnpm-lock.yaml`, `frontend/pnpm-workspace.yaml:5`. Los identificadores exactos están en el JSON de evidencia.

El CRM fija HS256 (`backend/crm/settings.py:495`), por lo que no coincide con la configuración de mezcla de algoritmos del aviso de confusión JWK. No se afirma un bypass de login. [Aviso de PyJWT](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-w2cx-738m-mc7w). Los otros paquetes incluyen avisos de disponibilidad; la presencia en el árbol no demuestra una entrada explotable públicamente. [urllib3](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g), [brace-expansion](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-q2hr-2g5m-vwhr).

**Corrección propuesta:** actualizar locks de forma controlada, verificar aplicabilidad del aviso sin versión corregida y repetir login, refresh, OAuth, HTTP externo y build. Registrar mitigaciones justificadas; no asumir que actualizar elimina todos los riesgos.

### M04 · P2 · El ciclo de eliminación de adjuntos no es consistente

**Dos defectos reproducidos con datos ficticios y almacenamiento en memoria:**

1. La eliminación individual borra los bytes antes de borrar la fila. Al simular un fallo de base de datos después, la fila permanece y el archivo ya no existe.
2. La API de borrado confirmado de un contacto responde correctamente, pero permanece su fila de adjunto, con `content_object=None`, y también el archivo. La relación genérica no incorpora automáticamente esos adjuntos al recolector.

Evidencia: `backend/common/views/attachment_views.py:113`, `:133`; `backend/common/views/record_delete_views.py:75`, `:124`; `backend/common/models.py:489`. Un adjunto sin padre se deniega al descargar, por lo que este resultado no demuestra exposición pública; sí retención inesperada, archivos inaccesibles y falta de conciliación.

**Corrección propuesta:** una política compartida de eliminación, con intención persistente, procesamiento tras confirmar la transacción, reintentos e idempotencia. Incluir adjuntos en las consecuencias del borrado de su padre. Un simple `on_commit` sin registro durable no resuelve la pérdida de un trabajo tras un reinicio.

**Cierre:** pruebas de caída de storage, fallo/rollback de DB, borrado de padre, reintento y concurrencia; política explícita para versiones/retención de S3.

### M05 · P2 · La caché compartida no se exige al arrancar

Sin `CACHE_URL`, `backend/crm/settings.py:386` usa `LocMemCache`; `check_hosted_config.py:10` no lo rechaza. Los límites de login y formularios dependen de esa caché. Configurar el broker de Celery no configura la caché de Django. La caché local es por proceso. [Documentación de Django](https://docs.djangoproject.com/en/6.1/topics/cache/#local-memory-caching).

**Alcance:** confirmado en código, no se leyó la variable efectiva de Render. Existe documentación de `CACHE_URL` en la referencia y guía de formularios; falta exigir/coherenciar la configuración hospedada.

**Corrección y cierre:** caché Redis compartida, prefijos/capacidad definidos y validación de arranque; comprobar el mismo contador desde dos procesos. No confundir throttling de aplicación con protección perimetral contra abuso.

### M06 · P2 · Transacciones de base de datos esperan a proveedores externos

`backend/common/google_sync.py:297` mantiene bloqueos de conexión y cita mientras consulta/modifica Google; las peticiones admiten 20 segundos de espera (`google_integration.py:247`). `backend/webforms/tasks.py:34` mantiene bloqueada la entrega durante el envío de correo.

**Impacto:** contención al editar, conexiones ocupadas y menor capacidad del worker. Es un riesgo localizado, no una medición de la causa exacta de latencia online.

**Corrección y cierre:** reservar trabajo en una transacción breve, llamar al proveedor fuera de ella y confirmar con generación/versión. Conservar IDs externos estables y protección contra duplicados. Probar proveedor lento, edición simultánea, desconexión y respuesta perdida.

### M07 · P2 · Algunas esperas críticas de la interfaz no tienen plazo de aplicación

`frontend/src/lib/api-helpers.js:71` usa `fetch` sin señal de cancelación/plazo. `frontend/src/hooks.server.js:124` y `:156` refrescan sesión/cambian organización con Axios sin timeout configurado. El login sí tiene plazos; estas rutas no reutilizan ese control.

**Impacto:** con una API lenta o conexión incompleta, la navegación puede esperar hasta límites de red/plataforma, en lugar de devolver un error recuperable en un tiempo definido. No se provocó una caída real de Render para comprobarlo.

**Corrección y cierre:** plazos y cancelación compartidos por clase de operación, error recuperable y reintentos solo cuando sean seguros. Cubrir API que no responde, respuesta vacía, refresh concurrente y recuperación. Nunca reintentar automáticamente una escritura que podría haberse completado.

### M08 · P2 · El preflight de formularios deja contexto RLS en su conexión

**Reproducido en PostgreSQL:** una petición OPTIONS mediante `CorsMiddleware`, con IDs ficticios, respondió 200 y dejó `app.current_org` con el valor de la URL. `backend/webforms/cors.py:53` asigna contexto de sesión y no restaura el previo; CORS puede terminar antes del middleware interno de limpieza.

Las tres pruebas del reset del pool pasan. **No se demostró una fuga entre peticiones.** La función depende de una limpieza posterior y no cumple por sí misma el contrato de restauración.

**Corrección y cierre:** restaurar el contexto previo en `finally`; probar OPTIONS, POST, excepciones y reutilización. No desactivar RLS ni cambiar a un rol privilegiado.

### M09 · P2 · El conector de formularios existentes y su guía prometen cosas distintas

En modo `copy`, `backend/webforms/templates/webforms/connect.js:49` captura el intento de submit y envía al CRM sin esperar la aceptación del procesamiento original. Una web puede rechazarlo después, o guardar el envío y perder la copia CRM. Se enlaza una vez al cargar el documento; un formulario añadido posteriormente no queda conectado automáticamente.

`docs/integrations/website-contact-forms.md:24` todavía indica reemplazar el manejador anterior. Eso contradice el modo de copia y puede llevar a quitar el correo o la página de agradecimiento de la web original.

**Corrección propuesta:** tres contratos explícitos: formulario CRM, copia de un formulario HTML sencillo con límites claros, y API/webhook desde el procesamiento exitoso para entrega fiable. Mantener instrucciones de instalación concretas en UI y explicaciones completas en la base de conocimiento.

**Cierre:** probar rechazo original, redirección, doble clic, fallo CRM, formulario dinámico y verificación antispam, conservando correo y agradecimiento originales. No afirmar compatibilidad universal con cualquier formulario o iframe.

### M10 · P2 · CI, análisis de seguridad e imagen no están alineados con main

- `.github/workflows/codeql-analysis.yml:26` y `:29` filtran `master`, no `main`, para push/PR. Tiene ejecución programada, así que no se afirma que nunca corra, pero no cubre cada cambio de main mediante esos disparadores. Solo analiza Python.
- CI fija pnpm 10 (`tests.yml:319`), Docker 11.17.0 (`frontend/Dockerfile:27`).
- Los filtros del workflow principal omiten el Dockerfile raíz y compose; un cambio exclusivo allí puede no activar ese workflow.
- `Dockerfile:23` ejecuta `uv sync` sin `--no-dev`; la etapa runtime hereda development (`:34`). El grupo dev está incluido por defecto: pytest/ruff entran en la imagen definida. [Documentación de uv](https://docs.astral.sh/uv/concepts/projects/sync/#syncing-development-dependencies). Los tests backend también se copian. No es por sí solo una vulnerabilidad explotable, pero contradice el objetivo de distribuir solo lo necesario.
- CI conserva instalación de librerías de WeasyPrint tras retirar PDF del principal.

**Corrección y cierre:** fijar herramientas coherentes, cubrir main y archivos de despliegue, separar dependencias de producción/desarrollo, construir y escanear las imágenes publicables. Conservar una etapa de desarrollo con sus herramientas y las migraciones históricas necesarias. Revisar branch protection y condición de despliegue en las plataformas; no se comprobaron sus valores online.

## Controles que pasan o conviene conservar

- PostgreSQL con rol sin superusuario ni BYPASSRLS para probar aislamiento; reset del pool y filtros explícitos por organización.
- Autenticación por contraseña, invitaciones y cambio de contraseña: los 28 casos de su archivo pasan también en la selección PostgreSQL.
- Los 22 casos de informes, 18 de permisos de adjuntos y 13 de borrado confirmado pasan en esa selección PostgreSQL. Los informes limitan campos/intervalos desde el servidor y protegen exportación CSV.
- Separación de visibilidad y acciones: leer un registro no implica eliminar sus archivos; el permiso se valida en backend.
- OAuth con estado/PKCE, tokens cifrados y privacidad de correo por conexión de usuario; conservar los casos negativos y de generación de conexión.
- Formularios por organización, validación/mapeo permitido, idempotencia y entrega de avisos con registro persistente de pendientes.
- Recordatorios con registro de entrega para evitar duplicados y comprobación de visibilidad; 13 pruebas pasan en PostgreSQL. Falta verificación de entrega online y recuperación tras interrupciones reales.
- Descargas autorizadas según el padre, archivos descargables como adjunto y nombres/size limit centralizados. La configuración S3 versionada usa URLs firmadas y evita sobreescritura; no se verificaron políticas efectivas de AWS.
- Producción definida con usuario no root y conservación de LICENSE. Quitar branding del producto no autoriza eliminar avisos legales del código original.

## Remaining Issues — Límites y deuda que requieren decisión

1. **Historial frente a auditoría:** `contacts/signals.py:16` descarta CREATE, DELETE y notas/adjuntos; la interfaz separa contenido e historial. Aunque sea una decisión de presentación, no debe describirse ese historial como una auditoría completa. Decidir una política de registro/retención independiente de lo que muestra cada pestaña. No se cambió esta regla sin confirmar el contrato.
2. **Observabilidad:** `/healthz/` sirve una plantilla (`crm/urls.py:31`); acredita vida HTTP, no DB, cola o entrega. Definir readiness y supervisión de worker/scheduler con alertas, sin hacer depender toda la disponibilidad de una caída temporal de Google.
3. **Rendimiento real:** las pruebas de consultas compactas pasan, pero no se midieron p50/p95, memoria, CPU, conexiones ni cola con volumen representativo en Render. No recomendaría subir el plan ni prometer fluidez basándome solo en el tamaño actual de la base.
4. **Recuperación y almacenamiento:** demostrar restauración de PostgreSQL, políticas de S3, retención/borrado, recuperación de cola y consistencia de variables/clave de cifrado entre API y Worker. La antigüedad de los mensajes de esta conversación no confirma el plan actual contratado.
5. **Mantenibilidad:** `common/models.py`, `contacts/views.py` y `auth_views.py` superan las mil líneas; hay formatos/estilos mezclados y convivencia de permisos antiguos con roles configurados. Refactorizar por flujo al estabilizar, sin reescritura masiva ni eliminación apresurada de compatibilidad.
6. **Seguridad pendiente de ampliar:** escaneo de secretos de todo el historial Git, imagen/SO, validación completa de restauración de sesiones entre múltiples instancias Web y pruebas de penetración. No se certificó ausencia total de secretos a partir de esta lectura.
7. **Accesibilidad y uso:** Svelte check no sustituye una revisión con teclado/lector de pantalla ni pruebas de navegador de todos los formularios. No se ejecutó una campaña E2E completa en esta auditoría.

## Plan de estabilización y criterio de cierre

| Orden | Trabajo | Evidencia exigida |
|---|---|---|
| 1 | Corregir M01 y revisar los bloqueos equivalentes | PostgreSQL: operaciones autorizadas pasan y denegaciones siguen protegidas |
| 2 | Recuperar CI del principal y actualizar dependencias | Suites/linters/builds verdes; avisos tratados y controles exigidos |
| 3 | Corregir ciclo de archivos, contexto RLS y caché | Fallos parciales, aislamiento y contadores compartidos probados |
| 4 | Acotar esperas/rediseñar transacciones de integraciones | Tests concurrentes y de interrupción, sin duplicados indebidos |
| 5 | Alinear conector HTML, UI y documentación | Prueba con formulario existente conservando su comportamiento |
| 6 | Revisar imágenes, despliegue y operación | Misma revisión en servicios, migraciones aplicadas, restore y smoke tests online |

Antes de admitir clientes, verificar en staging: owner y miembros propios/equipo/organización; dos organizaciones sin acceso cruzado; invitación y contraseña; contacto/empresa/negocio/tarea/ticket; creación, edición y cancelación de cita; Gmail/Calendar reales; adjuntos y borrado; formulario con aviso; recordatorio; informe/exportación; recuperación ante proveedor lento.

## Implementation — Entregables de esta revisión

Solo documentación de auditoría y evidencia: este informe y `2026-09-30-main-senior-engineering-evidence.json`. Se preservaron los cambios pendientes del usuario. No se corrigieron funciones, cambiaron dependencias, hicieron commits, enviaron correos ni desplegaron servicios. Las bases/roles de prueba PostgreSQL se eliminaron al finalizar; las reproducciones de archivos usaron almacenamiento en memoria.

Este documento actualiza el alcance del informe anterior. Goals y el borrado del módulo Documents pasan al laboratorio; no se presentan como problemas de rutas activas de main. La inconsistencia de adjuntos sí permanece en el producto principal y ahora tiene reproducciones adicionales.
