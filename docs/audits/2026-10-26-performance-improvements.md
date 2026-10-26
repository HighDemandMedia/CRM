# Mejoras de rendimiento: verificación local — 26 de octubre de 2026

Estado: cambios locales, sin commit, push ni despliegue. Baseline: `cbf032a75af1b8ff75fc97dfb0665f9fdf5e055c`.

## Implementación

- El contador adicional de Tickets solo se solicita en Analytics/Approvals, donde se muestra.
- Notificaciones agrupa navegación/foco durante 15 segundos desde una respuesta correcta. Abrir el panel y marcar leído fuerzan actualización; se conserva el sondeo visible de 45 segundos y el reinicio por usuario/organización.
- El editor de requisitos de etapa y su validación completa de teléfonos se cargan bajo demanda, con estados de carga, error y reintento. La validación de campos y del backend no se sustituye ni se elimina.
- El switch lista/pipeline responde visualmente al clic, se bloquea mientras carga y vuelve al estado confirmado si falla.
- Los formularios abren su contenedor inmediatamente, cargan componente/datos en paralelo y permiten cerrar mientras cargan. Una respuesta tardía no vuelve a abrir un panel cancelado.
- Tareas/Tickets heredan usuarios y etiquetas de sus layouts. La lista no llama a `parent()` salvo cuando el preset de tickets abiertos necesita etapas configuradas. Las etiquetas usan la respuesta compacta.
- La navegación principal y móvil incorporan el orden guardado antes de solicitar/precargar registros. Preferencias aisladas por organización/usuario; no se restaura pipeline ni filtros.

## Comparación

Dos builds de producción locales, mismo equipo, API, cuenta y registros ficticios. La versión anterior se preservó antes de editar. No se usó Vite de desarrollo para medir. Datos detallados en `2026-10-26-navigation-comparison.json`.

| Medición | Antes | Después | Diferencia |
|---|---:|---:|---:|
| Dependencias JS estáticas del layout, gzip local | 244.698 bytes | 131.005 bytes | −46,5% |
| Dependencias JS estáticas del layout, sin comprimir | 752.738 bytes | 361.382 bytes | −52,0% |
| Recorrido inicial, 15 cambios de módulo sin orden guardado | 75 solicitudes | 57 solicitudes | −24,0% |
| Recorrido final, 15 cambios de módulo con el mismo orden guardado | 87 solicitudes | 58 solicitudes | −33,3% |
| Cambio de búsqueda en Tickets | 6 solicitudes | 2 solicitudes | −66,7% |

El tamaño gzip es una estimación del grafo estático del layout (48 → 38 archivos), no el total transferido de cada página. Los editores se descargan cuando hacen falta y pueden quedar en la caché normal del navegador.

Recorrido final emparejado, ejecutado consecutivamente de 18:30:22.332 a 18:30:28.555 UTC, tres repeticiones por módulo. Ambos navegadores tenían orden por nombre ascendente en Contactos. Medianas de clic hasta contenido visible, **incluyen automatización**:

| Módulo | Antes | Después |
|---|---:|---:|
| Empresas | 186 ms | 158 ms |
| Negocios | 184 ms | 194 ms |
| Tareas | 187 ms | 179 ms |
| Tickets | 292 ms | 249 ms |
| Contactos | 242 ms | 184 ms |

Los tiempos variaron entre series; no son p95, INP, LCP ni una promesa de velocidad en Render. En Negocios no se demostró mejora de latencia. La reducción de consultas y del código inicial es más sólida que las diferencias pequeñas de milisegundos.

En el recorrido final, Contactos pasó de seis consultas de registros a tres (se elimina la segunda navegación por restaurar el orden). Tickets pasó de seis a tres. Las consultas de contexto se conservaron en los quince cambios de módulo. Todas las respuestas contadas fueron 200. El sondeo de notificaciones puede añadir una consulta según su ventana de actualización.

La primera comparación de apertura completa del formulario quedó prácticamente igual (mediana 311 → 308 ms). La mejora es mostrar el panel mientras llegan sus campos, no prometer que la API de creación responde más rápido.

## Verificación

- Frontend: **126 archivos, 1.032 pruebas aprobadas**.
- `pnpm check`: cero errores y cero advertencias.
- `pnpm lint`: Prettier y ESLint aprobados, cero advertencias permitidas.
- `pnpm build`: aprobado.
- Navegación real entre los cinco módulos, búsqueda y restauración de resultados, lista/pipeline, apertura/cancelación de formulario, cierre rápido, persistencia del orden y formulario responsive a 390×844 y 820×1180.
- La confirmación de resolución de ticket sigue exigiendo una nota; se canceló sin guardar.
- No se modificaron registros de clientes, reglas del backend, autenticación, roles ni infraestructura.

## Límites y seguimiento

- Antes de afirmar un beneficio en producción, desplegar Web y repetir el mismo recorrido en Render. No se hicieron pruebas de carga concurrente ni de cuentas grandes.
- El contexto de permisos/onboarding/cierre sigue fresco. No se añadió caché compartida de permisos ni datos entre organizaciones.
- Contactos/Empresas/Negocios todavía invocan `parent()` para configuración de etapas; esa llamada puede reejecutar los layouts del servidor. Su separación/versionado requiere otro cambio específico. El preset `all=0` sin estado explícito de Tickets también conserva esta llamada para respetar etapas personalizadas.
- Abrir directamente una URL sin parámetros todavía puede usar la restauración posterior de preferencias. La corrección anticipada cubre enlaces de la navegación principal y móvil.
- La interfaz diferida de requisitos de etapas se compiló y conserva el flujo anterior, pero no se completó una transición con campos personalizados obligatorios mediante la interfaz en esta sesión.
- El navegador registró una advertencia de History API en ambas versiones. No hubo errores de consola en la consulta revisada; queda pendiente localizar esa advertencia preexistente.
