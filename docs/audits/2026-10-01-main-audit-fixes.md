# Cierre técnico de correcciones del main local

Fecha: 1 de octubre de 2026.

Alcance: correcciones de M01–M10 de la [auditoría del main](2026-09-30-main-senior-engineering-audit.md), aplicadas en `Django-CRM-master`, rama `main`, sobre el árbol de trabajo existente. La referencia Git de partida es `fd6e619300f2c39e1f58cdbffbc9d4fa2633cee3`. Este informe no acredita cambios publicados en GitHub ni desplegados en Render.

Se conservaron los cambios previos de separación del laboratorio y recordatorios. Por ello, el diff completo frente a Git incluye trabajo anterior a estas correcciones. El laboratorio local permanece separado.

## Correcciones

| Hallazgo | Resultado implementado |
| --- | --- |
| M01 · Bloqueos SQL y permisos | Las consultas de autorización usan una subconsulta de IDs. La consulta exterior puede bloquear filas sin `DISTINCT`, conservando organización y alcance propio/equipo. Verificado con PostgreSQL y un rol sin capacidad de evadir RLS. |
| M02 · Pruebas y controles de calidad | Se actualizaron contratos de propiedades opcionales, reglas de etapas, eliminación de adjuntos y administración de miembros. Las pruebas exclusivas de endpoints retirados se conservaron en el laboratorio antes de retirarlas del main. Los permisos denegados siguen cubiertos; las pruebas positivas de borrado otorgan explícitamente el permiso necesario. Formato y errores de lint corregidos. |
| M03 · Dependencias | PyJWT actualizado a 2.15.1, urllib3 a 2.8.0, brace-expansion a 5.0.12 y devalue a 5.9.4. Los análisis de los árboles bloqueados no devolvieron avisos conocidos. Esto no es una garantía de ausencia de vulnerabilidades desconocidas. |
| M04 · Integridad de adjuntos | El borrado del registro guarda una orden persistente de limpieza en la misma transacción. El archivo se elimina después del commit; los fallos del almacenamiento o broker conservan el trabajo para reintento. Las relaciones genéricas de los cinco objetos principales incluyen sus adjuntos al eliminar el padre. Los archivos nuevos usan claves UUID para que un reintento antiguo no borre una nueva carga del mismo nombre. |
| M05 · Caché compartida | La comprobación de arranque alojado exige Redis mediante `CACHE_URL`. Se mantiene el modo local en memoria para desarrollo. Requiere configurar Render antes del siguiente despliegue. |
| M06 · Integraciones y transacciones | Calendar realiza las llamadas HTTP fuera de los bloqueos de base de datos y conserva la huella exacta de lo enviado. Una edición simultánea queda pendiente para la siguiente sincronización. El correo de formularios usa una reserva temporal con identificador y vencimiento; el envío ocurre fuera de la transacción. |
| M07 · Respuestas y tiempos de espera | La capa compartida de peticiones tiene límites de tiempo, trata respuestas JSON incompletas como error de servicio y distingue respuestas vacías válidas. No reintenta automáticamente escrituras cuyo resultado pueda ser incierto. Se acotaron también renovación de sesión y cambio de organización. |
| M08 · Contexto de organización en CORS | La consulta pública de origen usa contexto transaccional temporal y restaura el contexto anterior, incluso si falla. Probado con PostgreSQL. |
| M09 · Formularios existentes | El conector reconoce formularios insertados después de cargar la página y evita manejadores duplicados. La guía distingue copia de mejor esfuerzo, modo administrado y envío desde el servidor con reintentos. Ya no promete que copiar un submit confirma el procesamiento del formulario original. |
| M10 · CI e imagen | CodeQL contempla main y JavaScript/TypeScript. Los filtros de CI incluyen los archivos Docker y los controles de RLS/lint no quedan ocultos por un fallo previo. Se añadió cobertura de flujos críticos con rol sujeto a RLS. La versión de pnpm de CI coincide con Docker. La imagen backend de producción no hereda las herramientas de desarrollo ni copia directorios de pruebas. |

## Verificación

Resultados finales y límites de cada comprobación:

- Backend completo con SQLite: **3.510 aprobadas**. Los casos específicos de PostgreSQL se verifican por separado.
- Backend completo con PostgreSQL, comprobación de compatibilidad SQL con rol temporal que permite preparar fixtures: **3.514 aprobadas, 7 omitidas**. Este resultado no se usa como prueba de RLS; las pruebas de seguridad siguientes usan un rol restringido.
- PostgreSQL, flujos críticos con rol sin `SUPERUSER` ni `BYPASSRLS`: **197 aprobadas**. Esta selección incluye permisos, autenticación, Google, reportes, adjuntos, asociaciones, borrado y formularios.
- Pruebas marcadas específicamente para PostgreSQL bajo rol sujeto a RLS: **12 aprobadas**. Se corrigió además una prueba antigua que aceptaba cualquier excepción: ahora exige el rechazo específico por política de filas y no oculta errores de esquema o de aserción.
- Restablecimiento de contexto de organización al reutilizar conexiones PostgreSQL: **3 aprobadas**.
- Frontend: **407 aprobadas**, 64 archivos de pruebas.
- Svelte: **0 errores y 0 advertencias**. Build de producción aprobado.
- Ruff y comprobación de formato backend: aprobados. Prettier aprobado. ESLint: **0 errores y 280 advertencias preexistentes**.
- Modelos y migraciones: comprobación de migraciones faltantes aprobada.
- Imagen Docker backend: construida; comprobación Django aprobada; usuario sin root; `pytest` y `ruff` ausentes.
- Imagen Docker frontend: construida con el lockfile actualizado y pnpm fijado por Docker.
- Servicios locales: API, Worker y Scheduler en ejecución; `/healthz/` y la página local de login responden **200**.
- Dependencias Python de producción y árbol completo frontend: sin avisos conocidos en los análisis ejecutados.
- `git diff --check`: aprobado. La búsqueda de patrones de credenciales en líneas añadidas no encontró coincidencias; no sustituye un escáner exhaustivo de secretos.

Las selecciones backend se solapan; no deben sumarse como pruebas únicas. Las integraciones se verificaron con proveedores simulados. No se enviaron correos de prueba ni se modificaron eventos reales como parte de esta corrección.

## Antes de desplegar

1. En Render, añadir **`CACHE_URL`** al grupo **`hdm-crm-staging-core`**, con la URL interna del servicio Key Value. Debe estar disponible para API, Worker y Scheduler y no tener un valor distinto que la sobrescriba en cada servicio. No añadir estas credenciales al frontend ni al repositorio.
2. Revisar y publicar el conjunto de cambios autorizado. La publicación no se realizó en esta intervención.
3. Ejecutar la fase de release de la API para aplicar las migraciones. Las nuevas de esta corrección son `common.0069_pending_file_deletion`, `common.0070_unique_attachment_storage_keys` y `webforms.0005_email_delivery_claim`; se conserva la dependencia de `common.0068_reminder_delivery` del trabajo anterior.
4. Desplegar API y después Worker, Scheduler y Web con la misma revisión. Mantener una única instancia de Scheduler. Los procesos nuevos de fondo comprueban que las migraciones estén aplicadas.
5. Verificar online: login, edición por un miembro con permiso de equipo, borrado de adjuntos y reintento de limpieza, submit de formulario, correo y sincronización real con Google.

Las migraciones añaden tablas/campos y cambian la generación de claves de archivos futuros; no mueven ni renombran los archivos existentes. El guard de arranque rechazará el entorno alojado si falta Redis compartido.

Las migraciones pendientes se aplicaron satisfactoriamente a la base de datos **local**, incluida la de recordatorios anterior. No se aplicaron a Render desde esta intervención.
Worker y Scheduler locales se reiniciaron para cargar las nuevas tareas.

## Límites y seguimiento

- Las 280 advertencias ESLint corresponden a trabajo pendiente de mantenimiento; no se desactivaron las reglas para ocultarlas.
- Una entrega de correo aceptada por el proveedor seguida de un fallo antes de confirmar en la base de datos todavía puede repetirse. El identificador de reserva evita envíos concurrentes ordinarios, pero no ofrece entrega exactamente una vez.
- La copia de formularios en el navegador sigue siendo de mejor esfuerzo. Para confirmar la entrega después del procesamiento original, usar integración del servidor con idempotencia y reintentos. Formularios dentro de otro iframe o Shadow DOM requieren integración en ese contexto.
- La limpieza de adjuntos cubre los borrados futuros. No se eliminaron posibles huérfanos históricos de S3 ni se alteraron datos de producción.
- La configuración, los recursos y el funcionamiento real de Render/Google/S3 deben verificarse después del despliegue. Los resultados locales no certifican por sí solos el entorno online.
- No se ejecutó CodeQL en GitHub ni un análisis de vulnerabilidades del sistema operativo de las imágenes. Se verificaron su construcción y las dependencias de aplicación; la protección de ramas y los permisos efectivos de los workflows siguen pendientes de comprobar online.

## Referencias de seguridad consultadas

- [PyJWT: validación de firma al reutilizar opciones](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-gvp8-978c-rx2q).
- [urllib3: aviso de seguridad](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g).
- [brace-expansion: aviso de seguridad](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-q2hr-2g5m-vwhr).
- [devalue: serialización de memoria compartida](https://github.com/sveltejs/devalue/security/advisories/GHSA-j22f-vq7h-c4qm).

Configuración operativa detallada: [Render staging](../self-hosting/render-staging.md).
