# Auditoría de rendimiento de HDM CRM — 26 de octubre de 2026

## Resultado

Hay oportunidades concretas para reducir consultas repetidas y carga inicial, y mejorar la respuesta visual durante las transiciones. No se observó saturación sostenida de Web, API o PostgreSQL en la ventana medida. No está demostrada una regresión respecto a la versión anterior: falta una comparación equivalente antes/después y una traza de navegador que separe red, ejecución y renderizado.

Esta auditoría no modifica código funcional, configuración de producción ni registros de clientes. No se realizó prueba de carga contra producción.

## Alcance y método

- Código revisado: `cbf032a75af1b8ff75fc97dfb0665f9fdf5e055c`.
- Producción autenticada: Contactos, Empresas, Negocios, Tareas y Tickets; cambio de Contactos de lista a pipeline.
- Render: métricas de CPU/memoria y conexiones de PostgreSQL; registros de solicitudes y errores de Web/API. Ventana principal: 17:45–18:04 UTC.
- Tres recorridos de cinco módulos, con correlación de logs entre 17:57:26 y 17:57:50 UTC. Organización con pocos registros; no representa cuentas grandes ni múltiples usuarios concurrentes.
- Revisión del grafo de imports del build local y del flujo UI → carga de SvelteKit → API.

Los primeros tiempos de navegador de aproximadamente 3,2 segundos incluían la espera de la herramienta de automatización y se descartan como benchmark. Una segunda comprobación detectó cuatro destinos visibles aproximadamente a los 290–333 ms; la comprobación de Negocios terminó antes de completar la navegación y se excluye. Estos valores siguen incluyendo automatización y no equivalen a INP, LCP ni un p95 de usuarios reales.

## Mediciones verificadas

Duración de procesamiento de API registrada por Gunicorn (`%(L)s`), sin sumar red, cola previa al worker o renderizado del navegador:

| Endpoint | Muestras | Mediana | Máximo |
|---|---:|---:|---:|
| Contactos | 3 | 94 ms | 881 ms |
| Empresas | 3 | 83 ms | 88 ms |
| Negocios | 3 | 66 ms | 80 ms |
| Tareas | 3 | 20 ms | 64 ms |
| Tickets | 6 | 21 ms | 80 ms |
| Contexto de organización | 15 | 33 ms | 159 ms |
| Usuarios/equipos | 15 | 66 ms | 116 ms |
| Etiquetas | 12 | 20 ms | 110 ms |
| Notificaciones | 15 | 14 ms | 297 ms |

Las 75 solicitudes de esa muestra devolvieron 200. Tickets realizó dos consultas por visita. No se encontraron entradas de nivel `error` para Web/API en la consulta 17:50–18:04 UTC; esto no demuestra ausencia absoluta de errores.

Métricas muestreadas de las instancias nuevas tras el despliegue:

| Recurso | CPU observada respecto al límite | Memoria observada respecto al límite |
|---|---:|---:|
| API | hasta aproximadamente 9,1% | hasta aproximadamente 30,2% |
| Web | hasta aproximadamente 1,2% | hasta aproximadamente 11,7% |
| PostgreSQL | aproximadamente 6,5–24% | aproximadamente 21,5–27,1% |

PostgreSQL tuvo 2–4 conexiones activas. Son puntos agregados, no máximos instantáneos ni prueba de capacidad. Render no devolvió métricas `http_latency`; no hay p95 de plataforma disponible en esta revisión. La consulta SQL directa del conector fue rechazada por la restricción de acceso externo: se conservó esa protección y no se inspeccionaron planes SQL ni esperas internas.

## Hallazgos y cambios recomendados

### 1. Consultas repetidas al navegar — prioridad alta

`frontend/src/routes/(app)/+layout.server.js` vuelve a consultar `/org/ui-context/` cuando cambia el pathname. Esto incluye permisos y controles necesarios de onboarding/cierre, pero también configuración de propiedades y pipelines. Los layouts de Contactos/Empresas/Negocios vuelven a solicitar catálogos al entrar en cada módulo. Tareas carga usuarios en su page loader, por lo que también debe revisarse su comportamiento al filtrar.

En los 15 cambios de módulo hubo 15 consultas de contexto, 15 de usuarios y 12 de etiquetas, además de los registros.

**Propuesta:** separar o versionar catálogos no sensibles y reutilizarlos durante la sesión; invalidar al modificar etiquetas, equipos, pipelines o propiedades. Mantener comprobaciones frescas de acceso, cierre y onboarding, autorización de API y aislamiento por organización/usuario. No introducir caché global de permisos ni compartir datos entre cuentas. Validar revocación de permisos y cambio de organización antes de liberar.

### 2. Conteo adicional de Tickets — prioridad alta, alcance pequeño

El layout general solicita otra lista de tickets con `limit=1` para un contador. La cola principal ya carga los registros; el Sidebar actual no muestra ese contador. `SectionTabs` todavía lo utiliza en subpáginas como Analytics/Approvals.

**Propuesta:** no pedir el contador extra en la cola/detalle cuando no se representa; conservarlo donde se muestra, o reutilizar un total equivalente de la respuesta existente. Los filtros del contador y de la lista pueden ser diferentes: no intercambiar totales sin comprobar su semántica.

### 3. Notificaciones en cada navegación — prioridad media

`frontend/src/lib/v2/components/NotificationBell.svelte` refresca al montar, cada 45 segundos con pestaña visible, al recuperar foco/visibilidad, al abrir el panel y después de navegar. La muestra registró 15 consultas para 15 cambios de módulo.

**Propuesta:** agrupar disparadores y reutilizar brevemente el resultado reciente, conservando actualización al abrir el panel y tras mutaciones relevantes. Esto reduce tráfico auxiliar; no debe presentarse como único causante de la espera principal.

### 4. Código de teléfonos en el arranque general — prioridad media

Imports estáticos: layout → `StageTransitionLayer` → `StageRequirementField` → `PhoneInput` → validación `libphonenumber-js/max`.

El grafo estático del layout contiene 48 archivos JS: 752.738 bytes sin comprimir, aproximadamente 244.698 bytes comprimidos con gzip local. Un chunk con lógica/metadatos de teléfonos pesa 219.007 bytes sin comprimir, aproximadamente 58.448 bytes gzip. El chunk contiene más que los metadatos; todo su peso no es ahorro garantizado.

Estos números describen el build, no bytes realmente transferidos en cada navegación. Los archivos se pueden almacenar en caché. No se está atribuyendo al inicio el tamaño de todos los módulos de la aplicación.

**Propuesta:** cargar bajo demanda el editor de requisitos de etapa y otros editores pesados, revisando los demás importadores antes de estimar ahorro. Conservar validación internacional completa y validación de backend; no sustituirla por una regex para ahorrar peso. Comparar el grafo de imports y primera apertura de formularios después del cambio.

### 5. Respuesta visual de vistas y formularios — prioridad alta de UX

`ViewToggle.svelte` deriva su posición de la vista confirmada por el servidor; durante la solicitud se deshabilita y permanece en la posición anterior. Esto se observó en producción. `CreateLayer.svelte` espera datos y componente antes de abrir el panel; mientras tanto solo muestra “Opening form…”.

**Propuesta:** mostrar inmediatamente la intención y el estado de carga, manteniendo coherencia entre contenido y vista. Abrir el contenedor del formulario con un estado de carga antes de recibir sus campos. Ante error, restaurar la vista previa y permitir reintentar. Respetar navegación rápida, cancelación, foco y movimiento reducido. No simular que los datos ya llegaron.

### 6. Restauración de preferencias después de cargar — prioridad media

`list-view-preference.svelte.js` restaura parámetros guardados mediante `goto` desde un efecto después de entrar por una URL sin parámetros. En ese caso puede producir una segunda carga y un salto visual. Es un hallazgo de código condicionado a preferencias guardadas, no una duplicación reproducida en la muestra principal.

**Propuesta:** resolver los parámetros antes de solicitar los registros, conservando la regla de abrir en lista por defecto y el aislamiento de preferencias por cuenta/usuario. Añadir una prueba que compruebe una sola carga efectiva al volver al módulo.

## Qué ya está bien

- Listas paginadas y respuestas compactas; no descargar todos los registros para mostrar una página.
- Cargas independientes en paralelo en varios loaders.
- Formularios de creación con imports dinámicos.
- Precarga de navegación habilitada en el body.
- Web/API/PostgreSQL en la misma región de Render.

## Orden de implementación y verificación

1. Eliminar el conteo innecesario de Tickets y agrupar refrescos de notificaciones. Medir solicitudes por acción.
2. Mejorar los estados inmediatos del switch/panel, sin ocultar errores ni cambiar reglas de negocio.
3. Reducir imports iniciales y resolver preferencias sin segunda navegación.
4. Reutilizar catálogos con invalidación explícita y pruebas de permisos/cambio de organización.
5. Instrumentar duración Web/API y consultas lentas para explicar el pico de Contactos. No añadir índices o ampliar hardware sin localizar la espera.
6. Repetir recorridos con caché fría/caliente, lista↔pipeline, filtros, formularios y diferentes roles. Usar una demo local de build de producción con datos representativos para carga/concurrencia; evitar carga sintética en cuentas de clientes.

Criterios: menos peticiones redundantes, mismo acceso y datos, sin doble navegación al restaurar preferencias, feedback inmediato de carga y comparación de mediana/p95 con muestra suficiente. No prometer una reducción porcentual antes de implementar y medir.

## Referencias

- [SvelteKit: rendimiento](https://svelte.dev/docs/kit/performance): carga selectiva, datos no esenciales, navegación e instrumentación.
- [SvelteKit: carga de datos](https://svelte.dev/docs/kit/load): dependencias, invalidación y consideraciones de autenticación.
- Contexto histórico del proyecto: `docs/operations/navigation-performance.md` y `docs/self-hosting/page-load-performance.md`. Sus mediciones antiguas no son un baseline equivalente a esta auditoría.
