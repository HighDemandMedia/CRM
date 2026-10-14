# Revisión de backups y eliminación — 12 de octubre de 2026

## Resultado

Revisión técnica realizada sobre la configuración online y el código local del CRM principal. **La política de eliminación aún no está lista para activarse.** El plan de base de datos ya fue actualizado por el propietario, pero la recuperación aún inicializa; falta probar una restauración aislada y completar los controles operativos. El cierre y la reactivación se implementaron y probaron localmente; el control de cierre/cancelación quedó disponible para el propietario y la eliminación definitiva sigue desactivada. No se modificó la infraestructura online.

## Evidencia actual

| Componente | Evidencia observada | Consecuencia |
| --- | --- | --- |
| Render PostgreSQL `hdm-crm-staging-db` | Plan de pago `0.1c-256mb`, PostgreSQL 16, 1 GB, 8.24% utilizado | Ya no figura como Free. La advertencia previa de vencimiento dejó de aparecer en Info. |
| Recuperación de Render | Panel anuncia 3 días; botón Restore deshabilitado por inicialización de PITR | Ventana configurada, todavía no comprobada como recuperable. No hay evidencia de restauración exitosa. |
| Exportaciones Render | Create export disponible; panel indica al menos 7 días de conservación | No se creó ni descargó una copia durante esta revisión. La documentación publica 7 días; no prometer borrado físico exacto a esa hora. |
| S3 `hdm-crm-staging-queue`, us-east-1 | Versionado habilitado; cifrado SSE-S3; Object Lock deshabilitado | Borrar el objeto activo puede dejar versiones recuperables. Versionado no equivale a un backup independiente. |
| Ciclo de vida S3 | Cero reglas; carpeta raíz `media/`; cero reglas de replicación y cero inventarios | No existe expiración automática de versiones antiguas. El prefijo propuesto coincide con el almacenamiento del CRM. |
| AWS Backup, misma cuenta y us-east-1 | 0 recursos protegidos, 0 planes; bóveda Default con 0 puntos de recuperación | No se observan copias adicionales gestionadas allí. No certifica otras cuentas o regiones. |
| Copia local de desarrollo | El propietario confirma que solo contiene datos ficticios/demo | No se considera backup de clientes. No se inspeccionaron ni borraron archivos personales. |

Fuentes operativas: consola Render, páginas Info/Plan/Recovery del servicio indicado; consola S3, Objects/Properties/Management del bucket indicado; AWS Backup, Protected resources/Vaults/Backup plans en us-east-1. No se revelaron conexiones ni secretos.

## Retención acordada y alcance

1. El propietario de la plataforma puede iniciar el cierre de cualquier organización. El propietario de cada organización puede iniciar el de la suya; otros administradores y miembros no pueden.
2. Durante los siguientes 30 días: consulta y exportación con los permisos existentes; sin creación/edición, nuevos formularios ni sincronización.
3. Antes de vencer el plazo, solo el propietario puede reactivar conservando los registros; Google debe reconectarse. Después del plazo no hay reactivación automática.
4. Después: eliminación programada de los datos activos de esa organización, con reintentos y verificación de archivos pendientes.
5. S3: versiones no actuales elegibles para eliminación 30 días después de convertirse en no actuales. Se mantiene la regla propuesta **Disabled**, sin instalar. Nunca elimina por antigüedad un archivo todavía activo.
6. Backups de base de datos: seguir el ciclo del proveedor, actualmente ventana PITR de 3 días y exportaciones publicadas por 7 días. Una restauración debe reaplicar las eliminaciones antes de volver a producción.

No se debe anunciar «todo se elimina exactamente a los 60 días»: un fallo de limpieza desplaza el inicio de retención de un archivo, S3 procesa asíncronamente y las versiones ya antiguas pueden resultar elegibles inmediatamente al activar una regla. El plazo de 30 días de S3 se calcula desde cada sustitución/borrado, no desde la activación de la regla.

La propuesta `s3-noncurrent-retention.proposed.json` aplica al prefijo compartido `media/` de todas las organizaciones. Antes de activarla, inventariar versiones elegibles y aprobar el efecto irreversible sobre versiones de más de 30 días. No aplicar la configuración sustituyendo otras reglas que pudieran crearse mientras tanto.

## Hallazgos iniciales del código (antes de los ajustes)

### Alta prioridad: falta el ciclo de cierre

`backend/common/models.py` define `Org.is_active`, pero no fecha de cierre, fecha límite de exportación ni estados de purga. `backend/common/middleware/get_company.py` bloquea todo acceso cuando la organización está inactiva. Por tanto, `is_active=False` no implementa la ventana de consulta/exportación.

Se necesita un estado explícito y transaccional de cierre, autorización exclusiva del propietario, auditoría y bloqueo de escrituras en UI/API/formularios/trabajos. Debe mantenerse lectura, descarga y exportación sin ampliar permisos. Las rutas de autenticación y preferencias personales requieren reglas explícitas; un bloqueo indiscriminado de todos los POST rompería algunos flujos permitidos.

### Alta prioridad: limpieza parcial de archivos

`backend/common/attachment_cleanup.py` registra únicamente `Attachments` mediante `post_delete`, conserva trabajos independientes de la organización y reintenta el borrado de almacenamiento. `backend/crm/celery.py` programa el reintento cada cinco minutos. Esto es reutilizable, pero no prueba su ejecución actual en Render.

No se encontró limpieza equivalente para `Org.logo`, `CommentFiles.comment_file` ni archivos históricos de `Document`. La existencia de un modelo heredado no implica reincorporar su módulo al frontend. Un cierre debe inventariar datos históricos que aún existan. Las imágenes de usuarios compartidos requieren comprobar otras organizaciones antes de borrarlas.

Las rutas de archivos no están particionadas por organización: adjuntos usan fecha/UUID, logos y comentarios tienen prefijos compartidos. **Nunca borrar `media/` ni deducir un prefijo de organización** para purgar un cliente. La lista de claves debe salir de registros de esa organización y mantenerse hasta completar la limpieza.

### Alta prioridad: trabajos e integraciones

El scheduler Google selecciona organizaciones activas, pero el trabajo `sync_google_connection` no revalida `org.is_active` al seleccionar la conexión. No existe aún estado de cierre que impida un trabajo previamente encolado o en curso. Los trabajos genéricos de correo tampoco tienen un contrato de cancelación por cierre. El cierre debe detener ingreso y envío, invalidar conexiones pendientes y evitar que una tarea vuelva a crear datos ya purgados.

Borrar copias de Gmail/Calendar dentro del CRM no autoriza a borrar originales de la cuenta Google del usuario. La eliminación del CRM debe separar copias locales, credenciales y contenido externo. No se realizaron llamadas de eliminación ni revocación a Google.

### Alta prioridad: purga y recuperación

Hay relaciones protegidas (`CRMRole`, anfitrión de citas y creador de invitaciones), usuarios compartidos y aislamiento RLS. Un `Org.delete()` genérico no debe asumirse suficiente. Se requiere orden de borrado probado, preservación de usuarios que pertenecen a otras organizaciones, manejo de referencias genéricas, y registro de eliminación fuera del conjunto que se purga.

Ese registro debe permitir reaplicar cierres y eliminaciones después de restaurar un backup anterior. Las evidencias contractuales y excepciones legales requieren un alcance y plazo explícito, minimizando los datos conservados.

## Ensayo de recuperación pendiente

No se ha ejecutado una restauración: crear una instancia de recuperación puede generar cargos y los datos reales necesitan un entorno restringido. No utilizar la base principal ni la demo actual como destino.

1. Esperar a que PITR esté disponible y comprobar una fecha recuperable concreta.
2. Restaurar en una instancia aislada; mantener workers, scheduler, envíos de correo y sincronización externa desactivados.
3. Conservar fuera del repositorio y del chat las claves de cifrado necesarias; comprobar que se puede recuperar la configuración sin revelar tokens.
4. Validar esquema, roles RLS, recuentos por organización, relaciones y lectura de adjuntos; probar con dos organizaciones sin cruces de datos.
5. Recuperar una versión de archivo de prueba sin sobrescribir el original. No purgar archivos reales para demostrar el mecanismo.
6. Medir pérdida recuperable y tiempo total. La ventana de tres días es retención, no una garantía de tres días de pérdida ni del tiempo de recuperación.
7. Registrar resultados y limpiar el entorno de prueba mediante el procedimiento aprobado. No cambiar conexiones de producción durante el ensayo.

## Criterios para activar

- PITR disponible y restauración aislada verificada.
- Cierre de 30 días implementado con pruebas de permisos, exportación, límites de fecha y trabajos concurrentes.
- Purga y cola de archivos resistentes a fallos, con alertas por retrasos.
- Inventario y aprobación antes de activar la regla S3 de 30 días.
- Revisión final de documentos EN/ES, sin afirmar procesos todavía pendientes.

## Riesgo adicional fuera de esta revisión

Render muestra conexiones externas permitidas desde `0.0.0.0/0`. La autenticación de PostgreSQL sigue existiendo, pero conviene restringir la exposición a las IP necesarias o deshabilitar acceso externo si no se utiliza. No se modificó la red para evitar interrumpir conexiones existentes.

## Validación y límites

La inspección online fue de solo lectura. Después se implementaron localmente los ajustes de cierre, recuperación, aislamiento de trabajos y limpieza de archivos descritos en el [procedimiento de recuperación](organization-recovery.md). Se aplicaron las migraciones aditivas únicamente a la base local de desarrollo.

Validación: 442 pruebas de backend SQLite aprobadas (2 omitidas y 2 de PostgreSQL excluidas); 54 pruebas en una base PostgreSQL aislada, con rol sin superusuario, aprobadas. Incluyen recuperación antes del límite, rechazo después del límite, aislamiento de archivos compartidos, relaciones protegidas, permisos y espera de trabajos concurrentes. Ninguna prueba utiliza datos de clientes online.

El JSON de S3 continúa desactivado, con prefijo `media/`, retención no actual de 30 días y sin expiración por antigüedad de archivos activos. No hubo eliminación de datos reales, restauración online, exportación de producción, commit, push ni despliegue. El ensayo de recuperación y la activación online siguen pendientes.

Referencias oficiales: [Render: recuperación y backups](https://render.com/docs/postgresql-backups), [S3: eliminación de versiones](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html), [S3: expiración y procesamiento](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html).
