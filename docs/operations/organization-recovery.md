# Cierre y recuperación de clientes

## Estado de entrega

Actualizado el 14 de octubre de 2026 por decisión del propietario: cierre y
eliminación automática habilitados por defecto (`CRM_ORG_CLOSURE_ENABLED=true`,
`CRM_ORG_PURGE_ENABLED=true`). El cierre congela los cambios inmediatamente y
permite consultar/exportar durante 30 días. Al vencer el plazo se bloquea el acceso
y el siguiente ciclo del scheduler elimina los datos activos de la organización.
La verificación de backups no es una condición para ejecutar ese borrado.

La eliminación definitiva también elimina las cuentas de acceso de sus miembros
y propietario cuando ya no tienen ninguna membresía ni son propietarios de otra
organización. Se borran el email, el hash de contraseña, los tokens de sesión y
los tokens antiguos de acceso; la foto de perfil se añade a la cola de borrado
de archivos. Las cuentas compartidas y los operadores de la plataforma se
conservan. Durante los 30 días de recuperación no se eliminan las credenciales.
Después del borrado, una invitación nueva al mismo email crea una identidad nueva
y pide establecer contraseña. No recupera datos de la organización eliminada.

Este cambio se aplica a las purgas futuras. No realiza un barrido global de
usuarios huérfanos ni modifica cuentas conservadas por eliminaciones anteriores;
esas correcciones requieren revisar individualmente sus membresías actuales.

El despliegue en Render es manual. Si hay valores explícitos anteriores en `false`,
cambiarlos a `true` en API, Worker y Scheduler. Desplegar primero API con las
migraciones, luego Worker, Scheduler y Web con el mismo commit. El interruptor de
purga se conserva para una pausa operativa de emergencia, no para posponer el plazo.

## Si el cliente vuelve dentro de los 30 días

1. Entrar como propietario de la organización o de la plataforma en la organización del cliente.
2. Abrir Settings → Organization → Organization access. Revisar la fecha límite.
3. Pulsar Cancel closure and reactivate. En el modal, escribir el nombre exacto
   de la organización y confirmar la reactivación. El inicio del cierre usa el
   mismo patrón: botón Close organization y confirmación dentro del modal.
4. Confirmar que desaparece el aviso de solo lectura y que los registros y
   miembros siguen disponibles con sus permisos anteriores.
5. Pedir a cada usuario que reconecte Google. Reemitir las invitaciones que sigan
   siendo necesarias: las pendientes se cancelaron al cerrar.

Esto cancela la eliminación programada; no requiere restaurar un backup. La
reactivación no reenvía avisos de formularios cancelados. Si se vuelve a iniciar
el cierre, comienza un nuevo plazo de 30 días y se registra otro evento.
El propietario de cada organización puede ejecutar estas acciones únicamente para
su organización. El propietario de la plataforma conserva acceso a todas. Ser
administrador o tener permisos de configuración no otorga este control.

## Al alcanzar la fecha límite

La aplicación rechaza la reactivación y el acceso a los datos de la organización.
El scheduler revisa los cierres una vez al día, a las 04:00 UTC. El acceso termina
al vencer los 30 días; el borrado se ejecuta en la siguiente revisión diaria
(hasta 24 horas después), sujeto a disponibilidad del worker y reintentos.
El borrado de archivos utiliza una cola persistente y reintentos separados. Un
fallo de almacenamiento no se presenta como eliminación completa.

La orden `python manage.py purge_closed_organizations` solo informa candidatos.
`--execute` requiere el interruptor de purga habilitado y nunca permite adelantar
el plazo. Los trabajos antiguos de archivos sin organización deben drenarse antes.
No utilizar un borrado de prefijos de S3: `media/` pertenece a varias organizaciones.

Al vencer los 30 días, el cierre es definitivo. No ofrecer ni realizar recuperación de los datos de la organización desde HDM, sea automática o manual. Si el cliente vuelve
después de eliminarse su organización, acordar una cuenta nueva y, si corresponde,
importar una exportación que el cliente haya conservado. No recuperar datos que
debían eliminarse desde un backup general ni afectar a otros clientes.

## Recuperación técnica ante una avería

Es un procedimiento diferente de recuperar comercialmente a un cliente:

1. Restaurar en un entorno aislado autorizado, sin correo, workers ni integraciones.
2. Validar esquema, aislamiento RLS, registros, archivos y claves de cifrado.
3. Reaplicar cierres y eliminaciones posteriores al backup usando una copia
   independiente y actualizada del registro mínimo de eliminación.
4. Verificar que ningún cliente eliminado vuelve a quedar accesible, antes de
   habilitar tráfico o trabajos. Cambiar producción solo mediante el procedimiento
   aprobado de recuperación.

`OrganizationClosure` y `OrganizationLifecycleEvent` sobreviven al borrado del
tenant, pero están en la misma base de datos: **no son por sí solos un registro
independiente ante una restauración antigua**. Su conservación externa y el
procedimiento de reaplicación deben completarse antes de restaurar un backup a producción.

## Pendientes operativos independientes del borrado activo

- Restauración aislada de Render comprobada; confirmar disponibilidad real de PITR.
- Preservación independiente del registro de cierres y eliminaciones y ensayo de
  reaplicación al restaurar. Definir acceso y retención del registro mínimo.
- Alertas sobre errores de purga, cierres vencidos y archivos pendientes; responsables
  y procedimiento para excepciones legales. No existe un flujo por tenant de legal hold.
- Inventario de versiones S3 elegibles y aprobación de su expiración irreversible.
  La regla propuesta permanece desactivada y no instalada.
- La aceptación legal versionada se activa por separado con `CRM_LEGAL_VERSION`.

Las pruebas locales usan datos ficticios y no demuestran recuperación de producción.
La copia local de desarrollo no es un backup de clientes.

## Validación local inicial del 12 de octubre

- 54 pruebas en PostgreSQL aislado aprobadas, incluyendo concurrencia, aislamiento
  entre organizaciones, relaciones protegidas y archivos compartidos.
- 442 pruebas relacionadas en SQLite aprobadas; tras el ajuste final, las 11 pruebas
  del ciclo de cierre/recuperación aplicables a SQLite volvieron a pasar.
- 48 pruebas de frontend aprobadas; Svelte check sin errores ni advertencias; build
  de producción aprobado. Ruff y lint del frontend sin errores (6 advertencias
  preexistentes de bucles en Organization settings).
- Panel local comprobado con sesión del propietario: cierre deshabilitado como
  corresponde al estado de activación. No se cerró la organización demo en el navegador.
- 14 páginas legales verificadas; documentación EN/ES mantiene estado de borrador.
- Recursos PostgreSQL temporales de las pruebas eliminados; servicios existentes
  y laboratorio preservados. Sin commit, push ni despliegue.

## Controles simplificados y alcance actualizado

- Organization muestra una fila con Close organization o Cancel closure and
  reactivate según el estado. La confirmación del nombre queda dentro de un modal.
- El modal conserva una explicación breve del plazo de 30 días y del efecto de
  reactivar. No se presenta como eliminación inmediata ni irreversible.
- Acceso para el propietario real de la organización (Org.owner) con membresía
  activa, o para el propietario de la plataforma. Un administrador sin propiedad
  no recibe este permiso; tampoco un propietario de otra organización.
- La API vuelve a comprobar usuario, propiedad y membresía antes de modificar el
  estado. La confirmación del nombre se valida bajo bloqueo.
- Desde el 14 de octubre, la purga de datos activos está habilitada por defecto.
  La regla de expiración de versiones antiguas en S3 es independiente y no fue
  aplicada por este cambio. La conservación de copias no habilita recuperación
  comercial de una organización cerrada.
