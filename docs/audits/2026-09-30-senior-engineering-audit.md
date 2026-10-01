# Auditoría Senior Engineering — High Demand Media CRM

Fecha: 30 de septiembre de 2026. Base: `fd6e619300f2c39e1f58cdbffbc9d4fa2633cee3`, rama `main`, incluyendo los cambios locales pendientes de recordatorios y notificaciones.

## Dictamen

**No recomendaría abrir todavía el CRM a clientes reales como servicio de producción.** La arquitectura sirve para continuar el proyecto; no hay evidencia que justifique reescribirlo o convertirlo en microservicios. Primero hay que recuperar una validación automatizada fiable, atender las dependencias señaladas y cerrar las comprobaciones operativas de producción.

La aplicación compila y tiene controles importantes de permisos y separación de organizaciones. Sin embargo, la suite completa y los controles de lint no pasan. Además, hay riesgos concretos en configuración compartida, sincronización externa y conservación de archivos. No se demostró una intrusión, una fuga entre organizaciones ni una vulnerabilidad crítica explotable en producción durante esta revisión.

Esta es una auditoría de código, configuración versionada y pruebas locales. **No certifica la configuración actual de Render, AWS o Google**, ni sustituye una prueba de penetración independiente.

## Analysis — Arquitectura y alcance

El CRM es un **backend monolítico modular**, con frontend separado y procesos desplegables independientes. API, Worker y Scheduler comparten código y base de datos: tener contenedores distintos no los convierte en microservicios autónomos.

| Capa | Implementación revisada | Responsabilidad |
|---|---|---|
| Interfaz y servidor web | Svelte 5.57, SvelteKit 2.70, Node 24 en Docker | Navegación, formularios, sesiones y llamadas a API |
| API y dominio | Python 3.12, Django 6.1.1, Django REST Framework | Validación, permisos, operaciones CRM e integraciones |
| Datos | PostgreSQL; pruebas generales en SQLite | Persistencia y aislamiento mediante RLS |
| Procesos asíncronos | Celery 5.6.3 y Redis/Key Value | Correos, sincronización y tareas programadas |
| Adjuntos | Almacenamiento configurable, S3 para despliegue previsto | Archivos separados de la base de datos |
| Servicios externos | Gmail, Google Calendar y formularios públicos | Comunicaciones y captación de contactos |

Se siguieron flujos de autenticación, roles, informes, adjuntos, formularios públicos y sincronización desde sus entradas hasta sus validaciones/persistencia. Se revisaron también migraciones, configuración de despliegue, dependencias y CI. La lectura manual fue orientada al riesgo, no línea por línea de todo el repositorio. La aplicación móvil y cada módulo Preview no recibieron una auditoría funcional completa.

## Verification — Resultados ejecutados

| Comprobación | Resultado | Interpretación |
|---|---:|---|
| Backend, suite completa SQLite | **3.972 aprobadas, 859 fallidas, 27 omitidas** | No existe una base global de regresión en verde |
| Frontend, Vitest | **743 aprobadas, 4 fallidas** | 2 archivos de pruebas fallan |
| PostgreSQL con rol local sin superusuario ni BYPASSRLS, selección `postgres_only` | **6 aprobadas, 1 fallida** | La fallida recibe 403 por Preview antes de comprobar el aislamiento de Leads |
| Limpieza del contexto en el pool PostgreSQL | **3 aprobadas** | El hook de limpieza funciona en los casos ejercitados |
| Svelte check | **0 errores, 0 advertencias** | Comprobación estática aprobada |
| Build de producción frontend | **Aprobado** | Compilar no acredita los flujos ni el rendimiento online |
| Migraciones pendientes respecto a modelos | **No changes detected** | El cambio local ya incluye su migración; no significa que Render la haya aplicado |
| Ruff | **287 hallazgos** | 116 de imports, 154 de formato/ubicación de sentencias y 17 de código sin uso |
| ESLint | **9 errores y 290 advertencias** | El control de calidad definido en CI no pasa |
| Dependencias Python bloqueadas, sin desarrollo | **79 paquetes; 16 avisos en 2 paquetes** | Requieren evaluación y actualización controlada |
| Registro oficial npm, versiones del lockfile | **299 nombres de paquetes; 3 avisos en brace-expansion** | Incluye herramientas de desarrollo; no equivale a 3 ataques remotos al CRM |

El escaneo Python utilizó una exportación congelada del lockfile y `pip-audit`. La consulta npm utilizó el endpoint oficial de avisos en lote, después de que `pnpm audit` no completara en el entorno disponible. No se instalaron ni actualizaron dependencias del proyecto. El rol y la base desechables de las pruebas PostgreSQL se eliminaron al terminar.

**Lectura correcta de los fallos:** 696 comparaciones del backend recibieron 403 donde esperaban otro código. Hay incompatibilidades con los nuevos permisos y el bloqueo de Preview, expectativas antiguas de eliminación de adjuntos y cambios deliberados en propiedades/pipelines. No corresponde contar cada prueba fallida como un defecto de producto. Tampoco corresponde modificar todas las expectativas para conseguir verde sin revisar la regla de negocio.

Los cuatro fallos del frontend se concentran en etapas de contactos e historial de notas/adjuntos. Debe actualizarse el contrato esperado según los pipelines configurables y las pestañas actuales; esas pruebas por sí solas no demuestran pérdida de datos.

## Hallazgos priorizados

Prioridad: **P1** antes de admitir clientes reales; **P2** siguiente bloque de estabilización; **P3** mantenimiento planificado. La prioridad es de remediación del CRM, no una puntuación CVSS.

### A01 · P1 · La validación global no sirve todavía como criterio de publicación

**Confirmado por ejecución.** El backend tiene 859 pruebas fallidas, el frontend cuatro y ambos linters encuentran errores. El workflow exige estos controles, pero el estado local auditado no los supera. No se verificó si GitHub exige ese workflow antes de integrar cambios o si Render espera su resultado.

Evidencia: `.github/workflows/tests.yml:208`, `:331`; resultados completos resumidos arriba. Por ejemplo, la prueba PostgreSQL `common/tests/test_pat_auth.py:163` queda bloqueada por Preview: no llega a demostrar que el token aísla datos en ese flujo.

**Riesgo:** una regresión nueva queda mezclada con centenares de fallos conocidos, y un despliegue exitoso puede dar una sensación equivocada de validación.

**Acción:** clasificar cada grupo en contrato obsoleto, fixture incorrecta o defecto real. Conservar pruebas negativas de permisos; no desactivar Preview globalmente ni relajar autorizaciones para hacerlas pasar. Adaptar el caso de aislamiento a un recurso disponible o a un principal autorizado para el recurso. Exigir checks y pruebas críticas verdes para publicar.

**Cierre:** suite, lint y build aprobados, con excepciones explícitas y acotadas si alguna prueba depende de infraestructura externa.

### A02 · P1 · Dependencias bloqueadas con avisos públicos pendientes

**Confirmado por los registros consultados; explotación en el CRM no demostrada.**

| Paquete bloqueado | Avisos | Remediación que señalan los registros |
|---|---:|---|
| PyJWT 2.13.0 | 13 | La mayoría indica 2.14.0; uno 2.15.0; otro no declara versión corregida |
| urllib3 2.7.0 | 3 | 2.8.0 |
| brace-expansion 5.0.9 | 3 | Cubrir los tres rangos exige al menos 5.0.12 en esa rama |

Evidencia: `backend/uv.lock:1471`, `:1884`; `frontend/pnpm-lock.yaml:758`; `frontend/pnpm-workspace.yaml`. El override de brace-expansion se había añadido para un aviso anterior, pero su versión bloqueada ya está incluida en avisos posteriores.

El CRM fija HS256 con una clave del servidor (`backend/crm/settings.py:495`). Esto **no coincide** con las condiciones de algunos avisos de confusión de algoritmos, que requieren mezclar algoritmos simétricos y asimétricos y usar claves públicas como secretos. No se debe presentar como un bypass de login confirmado. [Aviso del mantenedor de PyJWT](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-w2cx-738m-mc7w).

El aviso sobre reutilizar un diccionario mutable de opciones no declara una versión corregida en el registro consultado; hay que revisar la ruta efectiva de SimpleJWT y verificar claims, no suponer que una actualización elimina todos los avisos. [Aviso del mantenedor](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-gvp8-978c-rx2q).

Los avisos de urllib3 incluyen problemas de disponibilidad bajo respuestas/proxies específicos. El aviso de brace-expansion depende de procesar patrones no confiables y aparece asociado a herramientas del árbol frontend; no se acreditó su exposición a entradas públicas del CRM. [urllib3](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g), [brace-expansion](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-q2hr-2g5m-vwhr).

**Acción:** actualizar mediante los gestores y regenerar locks; repetir autenticación, refresh, OAuth, llamadas externas y build. Documentar la aplicabilidad de cada excepción pendiente. Añadir escaneo periódico de dependencias e imágenes.

**Cierre:** sin avisos aplicables sin tratar, o con mitigación comprobada y aceptación explícita del riesgo. El inventario exacto de identificadores queda en el JSON adjunto a este informe.

### A03 · P2 · El despliegue permite una caché distinta por proceso

**Confirmado en código y guía; configuración efectiva de Render no comprobada.** Si falta `CACHE_URL`, `backend/crm/settings.py:386` utiliza LocMemCache. La guía principal de staging configura el broker de Celery pero no incluye `CACHE_URL`, y `check_hosted_config.py:10` no exige un backend compartido.

**Riesgo:** los contadores de límites de solicitudes varían entre procesos y se reinician con ellos. Configurar `CELERY_BROKER_URL` no configura automáticamente la caché de Django. Django documenta que la caché local es por proceso. [Documentación de Django](https://docs.djangoproject.com/en/6.1/topics/cache/).

**Acción:** configurar una caché Redis compartida con prefijos y capacidad apropiados; distinguir políticas de caché de las de una cola de trabajos. Validarla al arrancar en entorno hospedado. Los límites de DRF deben complementarse con protección perimetral para abuso, no considerarse una defensa absoluta.

**Cierre:** dos procesos comparten el mismo contador y la guía permite reproducir la configuración.

### A04 · P2 · Google Calendar mantiene bloqueos mientras espera la red

**Confirmado por trazado de código.** En `backend/common/google_sync.py:297`, la sincronización abre una transacción, bloquea conexión y cita con `select_for_update` y luego hace solicitudes a Google. Cada solicitud puede esperar 20 segundos (`google_integration.py:235`).

**Riesgo:** contención al editar esa cita o conexión mientras sincroniza, transacciones largas y consumo de conexiones/trabajadores. No demuestra que esta sea la única causa de lentitud en Render, pero sí una causa posible localizada en el código.

**Acción:** reservar brevemente el trabajo, llamar a Google fuera de la transacción y guardar el resultado con comprobación de generación/versión. Conservar los IDs externos estables y el manejo de conflictos existentes. Aplicar el mismo análisis al envío de avisos web, que también mantiene una transacción durante una entrega externa (`webforms/tasks.py:34`).

**Cierre:** una respuesta lenta del proveedor no mantiene una fila de cita bloqueada; pruebas concurrentes cubren edición, desconexión y reintentos sin duplicación.

### A05 · P2 · La comprobación CORS deja contexto RLS en su conexión

**Reproducido localmente en PostgreSQL.** `backend/webforms/cors.py:53` asigna `app.current_org` a nivel de sesión y no restaura el valor anterior. CorsMiddleware está por fuera del middleware que limpia RLS (`backend/crm/settings.py:93`). Una petición OPTIONS puede terminar allí sin ejecutar la limpieza interior.

Con CORS restrictivo, una petición de comprobación a un formulario de UUID ficticio dejó ese UUID en `current_setting('app.current_org', true)` después de responder 200. No se creó ni modificó ningún registro. Se limpió el contexto al terminar la comprobación.

**Alcance:** el hook del pool sí limpia al devolver la conexión, y sus tres pruebas pasaron. Por eso **no se afirma una fuga entre solicitudes o entre organizaciones**. El defecto es que esta función introduce estado de sesión sin restaurarlo y depende de una defensa posterior. PostgreSQL confirma que `set_config(..., false)` tiene duración de sesión. [Documentación de PostgreSQL](https://www.postgresql.org/docs/17/functions-admin.html).

**Acción:** encapsular el cambio con restauración en `finally`, respetando cualquier contexto anterior. Probar OPTIONS, POST, UUID inválido, excepción y reutilización de conexión.

### A06 · P2 · El conector HTML copia intentos, no confirmaciones del formulario original

**Confirmado en implementación.** `backend/webforms/templates/webforms/connect.js:49` escucha `submit` en captura y, en modo `copy`, envía al CRM sin esperar el resultado del procesamiento original. La instalación se resuelve al cargar el documento (`:129`).

**Riesgo funcional:** la web puede rechazar el envío y el CRM ya haber creado el contacto; también puede confirmarse el envío original y fallar la copia al CRM. Formularios insertados después, iframes ajenos y plataformas con envío propio requieren otro mecanismo. `keepalive` no equivale a una cola durable.

**Acción:** presentar tres opciones claras: formulario nuevo del CRM; HTML sencillo con copia y límites explícitos; webhook/API desde el procesamiento exitoso para integraciones que requieran fiabilidad. Un modo que copia el intento puede ser válido, pero debe llamarse y documentarse así. Añadir diagnóstico de conexión y estado de entrega sin interferir con el correo ni la página de agradecimiento originales.

**Cierre:** pruebas con rechazo original, fallo CRM, redirección inmediata, doble clic y formulario dinámico; resultado y reintento visibles donde corresponda.

### A07 · P2 · Borrar un documento no borra su archivo almacenado

**Confirmado por código; no se borraron archivos reales.** `backend/common/views/document_views.py:345` elimina únicamente la fila. El modelo `Document` no añade limpieza del archivo y no se encontró un receptor de eliminación que lo haga. Django FileField no elimina automáticamente el objeto de almacenamiento al borrar el registro.

En cambio, el flujo de adjuntos (`attachment_views.py:113`) intenta borrar primero el archivo y después la fila, dentro de una transacción de base de datos. Esa transacción no puede revertir una eliminación ya ejecutada en S3 si falla el paso posterior.

**Riesgo:** documentos huérfanos y retención/coste inesperados; en el segundo caso, una fila podría quedar apuntando a un archivo ya eliminado tras un fallo parcial. Documents está en Preview, por lo que su exposición actual es menor.

**Acción:** establecer una política común de borrado con estado persistente, reintentos e idempotencia; mantener autorización por registro. Definir aparte versionado y retención de S3: eliminar el objeto actual no necesariamente elimina versiones históricas.

**Cierre:** pruebas de fallo de almacenamiento y de base de datos, reintentos y reconciliación de huérfanos.

### A08 · P2 · CI y Docker no reproducen exactamente el mismo entorno

**Confirmado.** `.github/workflows/tests.yml:319` configura pnpm 10; `frontend/Dockerfile:27` configura 11.17.0. Además, el filtro de rutas del workflow no incluye el Dockerfile raíz ni docker-compose: un cambio exclusivo allí no activa esta suite.

**Acción:** fijar una sola versión del gestor, incluir archivos de despliegue relevantes y construir las imágenes en CI. Antes de publicar, verificar que Web, API, Worker y Scheduler usan la revisión prevista y que las migraciones se ejecutan en el orden definido.

**Cierre:** un cambio de Dockerfile dispara validación; CI y el despliegue consumen el mismo lock con el mismo gestor.

### A09 · P3 · La lista de Goals conserva consultas adicionales por fila

**Reproducido por la prueba existente.** `test_listing_more_goals_does_not_cost_more_queries` mide 10 consultas con tres metas y 17 al ampliar el conjunto a doce. La paginación limita el resultado, por lo que no se deben interpretar esos números como doce filas necesariamente serializadas.

`goal_views.py:66` precarga persona, usuario y equipo; `SalesGoalSerializer` utiliza `ProfileSerializer`, cuyos campos adicionales leen organización/rol (`common/serializer.py:715`, `common/models.py:301`). El cálculo de progreso ya está agrupado: no hay que reemplazarlo a ciegas por otro cálculo.

**Acción:** capturar las consultas de la serialización y precargar sus relaciones efectivas, conservando el cálculo agrupado. Revisar después el coste de recorrer todos los negocios del intervalo para cada meta. Goals está en Preview.

**Cierre:** número de consultas estable al crecer la página y resultados de metas iguales.

### A10 · P3 · La documentación de formularios contradice el modo actual

**Confirmado.** `docs/integrations/website-contact-forms.md` indica sustituir el manejador de envío anterior y que el conector se encarga del envío. El modo `copy` actual conserva ese manejador. El documento también promete mostrar errores de entrega sin distinguir el modo de copia, que oculta su estado visual.

**Riesgo:** una organización puede quitar el correo o la redirección de su web siguiendo la guía, reproduciendo el tipo de problema ya observado durante la integración del sitio de HDM.

**Acción:** una sola guía por modo de conexión; pasos breves en la interfaz y límites/ejemplos en la base de conocimiento. Probar las instrucciones con una página HTML mínima conservando envío y agradecimiento originales.

## Controles que conviene conservar

- Verificación del JWT y resolución de organización en backend; la decodificación local del frontend no sustituye esa verificación.
- Separación entre owner de plataforma, creador de organización y permisos de registros. No hacer depender esta separación solamente de ocultar menús.
- Validación de estado del usuario/organización y de membresía revocada en middleware. La revisión de tokens personales debe considerar ese middleware además de su autenticador.
- Contexto RLS por organización, limpieza en `finally` y hook de limpieza del pool. Las pruebas PostgreSQL deben seguir usando un rol que no pueda eludir RLS.
- Registro por invitación y comprobación de configuración hospedada; cookies seguras y restricciones de hosts/orígenes.
- OAuth con estado/PKCE y tokens cifrados; generación de conexión e IDs estables para reintentos de Calendar.
- Formularios limitados por organización, mapeo permitido, idempotencia del envío, destinatarios autorizados y reintentos de correo.
- Autorización de eliminación de adjuntos por permiso del registro padre, no solamente por haber subido el archivo.
- Restricciones del cargador de recursos de PDF para evitar lectura arbitraria de archivos/URLs.
- Contenedores de producción sin usuario root y conservación de LICENSE. No se revisó la licencia de cada dependencia ni se emite un dictamen jurídico.

## Remaining Issues — Deuda y comprobaciones pendientes

**Permisos heredados.** `rbac.scoped()` y `require()` mantienen una vía de compatibilidad para usuarios sin `access_role`. Las migraciones y las altas principales asignan Member, pero un perfil incompleto puede recibir reglas diferentes a uno configurado. No se encontró una ruta pública que permita quitarse el rol. Conviene inventariar perfiles incompletos y migrar a denegación por defecto, con pruebas de altas, invitaciones, democión y scripts administrativos.

**Observabilidad.** `/healthz/` devuelve una plantilla y confirma vida del proceso, no la disponibilidad de PostgreSQL, Redis, correo o sincronización. Hace falta distinguir liveness de readiness, medir antigüedad de trabajos, fallos de proveedor y última ejecución del scheduler. Un chequeo externo de correo no debe enviar mensajes en cada health check.

**Rendimiento online.** Esta auditoría no midió p50/p95 de navegación autenticada, CPU/RAM de Render, saturación del pool, espera de Redis ni latencia a PostgreSQL/S3. No puede concluir que subir el plan de Render resuelva el problema. Medir primero páginas críticas con datos representativos y concurrencia controlada; después dimensionar.

**Backups y restauración.** No se verificaron plan activo, copias recuperables de PostgreSQL, versionado/retención de S3, permisos IAM, expiración de recursos de staging ni recuperación de la cola. Antes de clientes reales: restauración ensayada en otro entorno, tiempo objetivo de recuperación y pérdida máxima de datos aceptable documentados.

**Secretos.** No se inspeccionaron los valores de Render ni se realizó un escaneo exhaustivo de todo el historial Git. La existencia de variables de ejemplo/desarrollo versionadas no demuestra filtración de credenciales de producción. Completar el inventario y el escaneo sin copiar secretos al informe.

**Recordatorios pendientes.** La copia local incluye migración 0068, recibos de entrega y avisos en interfaz. El build actual y las pruebas generales los incluyen, pero no se verificó su funcionamiento online ni que estuvieran desplegados. Validar zonas horarias, permisos, cancelaciones y reinicio de Worker/Scheduler en staging antes de anunciarlos como disponibles.

**Mantenibilidad.** Hay mezcla de convenciones antiguas y nuevas en errores HTTP, permisos y validación. Conviene consolidarlas por flujo al corregirlo, no hacer un refactor transversal mientras la suite completa está fallando. La separación modular actual permite esa mejora incremental.

## Plan — Orden de remediación

1. **Restablecer confianza de publicación:** clasificar fallos, corregir fixtures/contratos y defectos reales; lint y suite crítica verdes; revisar bloqueo de merges y despliegues.
2. **Dependencias y configuración:** actualizar locks con pruebas, evaluar avisos restantes y verificar caché compartida, rol de base de datos y coherencia de variables entre servicios.
3. **Concurrencia y datos:** sacar solicitudes externas de transacciones largas, corregir el alcance del contexto CORS y unificar el ciclo de borrado de archivos.
4. **Formularios y rendimiento:** definir claramente copia frente a entrega confirmada, alinear guía/UI, cerrar pruebas de integración y eliminar consultas por fila.
5. **Ensayo de producción:** restaurar backup, medir carga representativa y completar recorrido por dos organizaciones sin cruces de datos.

El recorrido final debe incluir: invitación y contraseña; permisos propios/equipo/organización; contacto y adjuntos; formularios y sus avisos; cita y sincronización bidireccional; tareas y recordatorios; informes/exportación; cierre de sesión y revocación de acceso. Los envíos reales y cambios externos se ensayan con cuentas/datos de prueba definidos.

## Implementation — Cambios de esta auditoría

Solo se añadieron este informe y su resumen de evidencia. No se corrigió código funcional, no se actualizaron dependencias del proyecto, no se hizo commit/push ni se desplegó. Se conservaron los cambios de recordatorios que ya estaban en el árbol de trabajo.

Evidencia resumida: `2026-09-30-senior-engineering-evidence.json`, en esta misma carpeta. Los logs locales de ejecución están bajo `/tmp/crm-senior-*`; son temporales y no deben tomarse como archivo permanente del proyecto.
