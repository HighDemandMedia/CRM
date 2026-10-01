# CRM principal y laboratorio local

Estado: separación local preparada el 30 de septiembre de 2026. No publicada en GitHub ni desplegada en Render.

## Distribución

| Proyecto | Ubicación | Propósito |
| --- | --- | --- |
| CRM principal | `Django-CRM-master` | Producto que se mantiene y despliega para las organizaciones |
| Laboratorio | `../HDM-CRM-Lab` | Copia independiente con las funciones Review y los cambios locales que existían antes de separarlas |

El principal conserva Today, contactos, empresas, negocios, calendario, tareas, tickets, informes, adjuntos, notificaciones, usuarios, permisos, propiedades, pipelines, etiquetas, formularios web, integraciones Google y ayuda.

Leads, Documents, facturación/presupuestos, Timesheet, Goals, administración de tokens y la configuración avanzada de tickets se consultan y desarrollan en el laboratorio. Se retiraron del principal sus pantallas y los endpoints de administración correspondientes, las consultas adicionales de navegación/búsqueda y sus tareas periódicas. Un propietario tampoco obtiene una excepción para abrir las rutas retiradas.

Documents es el módulo separado de gestión documental. Los **adjuntos de contactos, empresas, negocios y tickets permanecen en el CRM**.

## Abrir el laboratorio

1. Abrir Docker Desktop.
2. Ejecutar `../HDM-CRM-Lab/INICIAR-LAB.command`.
3. Entrar en <http://127.0.0.1:5183>.
4. Usar `ADMIN_EMAIL` y `ADMIN_PASSWORD` de `../HDM-CRM-Lab/.env.lab`. Son credenciales ficticias locales, independientes de las de producción.

Para detenerlo conservando sus datos:

```sh
cd ../HDM-CRM-Lab
docker compose -f compose.lab.yml stop
```

Siempre usar `compose.lab.yml`. El compose original se conserva únicamente como referencia de la copia histórica.

El laboratorio tiene PostgreSQL, Redis, worker, scheduler y almacenamiento propios. La red de los servicios no tiene salida externa. Un proxy permite acceder desde este equipo, únicamente por `127.0.0.1`, a la interfaz (5183) y API (8013). No se copiaron las credenciales de producción. Los correos usan el backend de consola; Google y AWS no están conectados. La descarga inicial de imágenes y dependencias sí requiere Internet.

Los 216 archivos retirados se verificaron contra la copia original. El código retirado se puede cotejar con `lab-extraction.json` y los hashes de `../HDM-CRM-Lab/LAB-SNAPSHOT.json`. La copia incluye los cambios pendientes anteriores, pero excluye secretos, dependencias instaladas y archivos de usuarios. No tiene remoto Git ni workflows de despliegue.

## Compatibilidad que se conserva

No se eliminaron tablas ni datos, ni se crearon migraciones destructivas. Algunos modelos y aplicaciones de Django continúan instalados porque las migraciones y relaciones existentes los necesitan. También se conservan:

- Productos utilizados por las líneas de negocios.
- Registros de formularios antiguos y sus relaciones históricas.
- Portal de tickets, CSAT y reglas compartidas de tickets ya almacenadas.
- Referencias históricas en actividades, relaciones y verificaciones de eliminación.
- Alias de la tarea genérica `leads.tasks.send_email` para procesar correos que ya estuvieran en cola durante un despliegue posterior.

Esto separa las funciones del producto y sus trabajos programados; no pretende borrar de golpe todo el esquema histórico. Extraer esas relaciones requeriría otra migración con revisión de los datos existentes. La guía de uso del CRM dentro de Help permanece disponible.

## Verificación

- 426 pruebas seleccionadas del backend aprobadas; dos omitidas por requerir PostgreSQL.
- 89 pruebas aprobadas con PostgreSQL real y un usuario sin privilegios de superusuario: aislamiento de módulos, recordatorios y formularios de contactos.
- Pruebas adicionales de Today, correos, empresas y tickets: 216 aprobadas, una omitida y tres fallos anteriores, reproducidos también en la copia del laboratorio.
- Interfaz: 399 pruebas aprobadas y cuatro fallos anteriores en historial/pipeline de contactos, ya identificados por la auditoría previa.
- Comprobación Svelte: cero errores y cero advertencias. Build de frontend y construcción de imagen Docker aprobados. Django inicia en la imagen reducida; no hay cambios nuevos de esquema por esta separación.
- Regresión final después de limpiar imports: 104 pruebas aprobadas.
- Ruff en los archivos Python afectados: sin errores. ESLint en los archivos afectados: sin errores; quedan advertencias de claves de listas y enlaces de la interfaz existente.
- Laboratorio: acceso HTTP y autenticación local comprobados; Leads, Documents, Invoices, Timesheet y Goals responden con sus páginas, sin pantalla de error. La API también responde con autenticación.

Los fallos previos de empresas corresponden al permiso para eliminar adjuntos, texto de confirmación y validación de una propiedad obligatoria. Esta separación no los corrige. El informe anterior permanece en `docs/audits/2026-09-30-senior-engineering-audit.md`.

No se ha medido una mejora de latencia en Render. La reducción comprobada es de código de pantallas/API, consultas auxiliares, trabajos programados y dependencias PDF; no garantiza por sí sola resolver los problemas de rendimiento anteriores.

## Publicación posterior

Cuando se autorice publicar, revisar y confirmar únicamente el repositorio principal. La carpeta hermana del laboratorio queda fuera del contexto de build y de ese repositorio. Revisar por separado los cambios de recordatorios que ya estaban pendientes.

Antes del despliegue, comprobar que no quedan trabajos Review en ejecución o pendientes en la cola compartida; no vaciar toda la cola. Desplegar API, worker, scheduler y web con la misma revisión y verificar acceso, formularios, adjuntos y recordatorios online. Los datos y conexiones del laboratorio no deben copiarse a Render.

Para recuperar en el futuro una función Review, portarla mediante un cambio acotado, con sus pruebas y permisos. No sustituir el principal por toda la copia del laboratorio.
