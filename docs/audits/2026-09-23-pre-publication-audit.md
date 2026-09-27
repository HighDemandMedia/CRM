# Auditoría previa a publicación — High Demand Media CRM

**Fecha:** 23 de septiembre de 2026
**Repositorio:** `/Users/humberto/Documents/CRM/Django-CRM-master`
**Estado auditado:** rama `main`, base `94f3f8b`, incluyendo los cambios locales todavía sin commit.
**Dictamen:** la licencia base permite el uso comercial y la publicación del fork; **el entorno actual no está listo para abrirse a clientes en Internet**.

## 1. Resumen ejecutivo

La base es aprovechable. El frontend compila, las migraciones no presentan cambios pendientes de generar y las siete pruebas específicas de PostgreSQL/RLS pasaron usando un usuario sin privilegios para saltarse el aislamiento. Hay controles reales en el backend para organizaciones, roles, registros y acciones; no dependen únicamente de esconder botones.

El problema principal para publicar no es rehacer el CRM: es cerrar la preparación de producción, reconciliar la suite de pruebas con las nuevas reglas del producto, actualizar dependencias y completar la documentación de licencias. El entorno observado usa servidores de desarrollo, configuración local de seguridad y correo de pruebas. Además, el arranque contempla un administrador con contraseña predeterminada si no se configura otra.

| Decisión | Resultado |
| --- | --- |
| Seguir desarrollando y mostrar una demo local con datos ficticios | Sí |
| Comercializar el fork bajo la licencia base MIT | Sí, conservando avisos y cumpliendo las licencias de terceros |
| Afirmar que todo el stack está bajo MIT | No |
| Publicar directamente el Compose actual como producción | No |
| Abrir a clientes con datos reales hoy | No recomendado |
| Certificar capacidad para un millón de usuarios | No hay pruebas que lo sustenten |
| Afirmar que no existen vulnerabilidades | Esta auditoría no permite esa afirmación |

No se cambió la lógica de la aplicación, no se hizo commit/push ni se desplegó. Las pruebas se ejecutaron sobre bases de pruebas; la instancia PostgreSQL temporal se eliminó al terminar. No se enviaron correos a clientes.

## 2. Alcance y límites

Se inventarió el repositorio, con 1.985 archivos versionados, 738 archivos Python en el backend y 728 archivos bajo `frontend/src`. Se revisaron manualmente rutas críticas de autenticación, organizaciones, RBAC, credenciales API, calendario, reportes, archivos/PDF, configuración, contenedores, publicación y licencias. Se incluyeron los cambios locales recientes de Help y permisos.

Se ejecutaron las suites disponibles, compilación y comprobación del frontend, análisis estático Python, verificación de migraciones, diagnóstico Django de despliegue, consultas de aislamiento PostgreSQL, auditorías de dependencias e inventario de licencias. Se contrastaron alertas y condiciones con fuentes oficiales.

**No equivale a leer y demostrar formalmente cada línea ni a un pentest externo completo.** No se realizó una revisión exhaustiva de todo el historial Git, un escaneo del sistema operativo de las imágenes, una prueba de carga, una restauración de producción ni una validación real de Google OAuth/SMTP/S3 bajo un dominio público. El móvil se inspeccionó parcialmente; no se compiló ni certificó. No se verificaron protecciones de rama ni secretos configurados en GitHub. No se ejecutó una pasada completa de ESLint/Prettier del frontend; sus comprobaciones fueron Svelte check, pruebas y compilación.

Los resultados corresponden a este estado local, no únicamente al commit base. Será necesario identificar el commit final que llegue a producción y repetir sus comprobaciones.

## 3. Resultados de comprobaciones

| Comprobación | Resultado | Interpretación |
| --- | --- | --- |
| Backend, suite general con SQLite | **4.585 pasan; 29 fallan; 18 omitidas; 7 deseleccionadas** | No está verde; mezcla diferencias de especificación, fallos del entorno de pruebas y asuntos abiertos |
| PostgreSQL, pruebas marcadas `postgres_only` | **7 pasan** | Incluyen aislamiento de portales, tokens y tablas de pipeline; rol sin superusuario ni BYPASSRLS |
| Frontend, Vitest | **668 pasan; 4 fallan**, 672 pruebas | Fallos en expectativas antiguas de etapas e historial; requieren reconciliación |
| Frontend, compilación de producción | **Correcta** | Compilan cliente y servidor con adapter-node |
| Svelte check | **0 errores; 0 advertencias** | Comprobación estática correcta |
| Migraciones, detección de cambios | **No changes detected** | No se detectaron cambios de modelos sin migración; no sustituye probar una actualización con datos reales |
| Django `check --deploy` en configuración actual | **229 avisos: 4 de seguridad y 225 del esquema API** | No son 229 vulnerabilidades; los cuatro de seguridad impiden usar esta configuración sin ajustes |
| Ruff | **272 hallazgos en 93 archivos** | Mayormente imports y estilo; también imports/variables sin usar |
| Formato Python | **148 archivos requieren formato; 601 conformes** | Deuda de mantenimiento, no una brecha de seguridad por sí misma |
| Auditoría de paquetes JavaScript | **0 vulnerabilidades conocidas reportadas** | Resultado de la base de avisos consultada, no garantía absoluta |
| Auditoría de paquetes Python instalados | **89 paquetes; 1 aviso en WeasyPrint 69.0** | La consulta manual del proveedor encontró además un segundo aviso aplicable a esa versión |

La suite Python se ejecutó sin cobertura porque la configuración de cobertura del directorio superior no está montada en el contenedor actual. No se atribuye un porcentaje de cobertura a esta auditoría.

## 4. Hallazgos prioritarios

**P1:** cerrar antes de abrir producción o de ofrecer la función afectada. **P2:** corregir o documentar una decisión explícita antes de ampliar el uso. **P3:** mantenimiento. La prioridad de despliegue no significa que se haya demostrado una explotación.

### A01 — P1: el arranque actual es de desarrollo

**Confirmado.** [Compose](/Users/humberto/Documents/CRM/Django-CRM-master/docker-compose.yml:94) selecciona el frontend de desarrollo y monta código fuente. [El entrypoint](/Users/humberto/Documents/CRM/Django-CRM-master/docker/backend/entrypoint.sh:33) usa `runserver`. El [Dockerfile del backend](/Users/humberto/Documents/CRM/Django-CRM-master/Dockerfile) no define un usuario no privilegiado ni un comando de producción. El frontend sí dispone de una etapa de producción con usuario `node`, pero Compose no la utiliza.

**Impacto:** rendimiento, aislamiento y comportamiento de desarrollo inapropiados para un servicio público.

**Cierre:** preparar una configuración independiente de producción: frontend compilado, servidor WSGI/ASGI apropiado, backend sin root, sin montajes de código, proxy HTTPS, comprobaciones de salud y migraciones ejecutadas de forma controlada. Validar un arranque desde cero y una actualización. La [guía oficial de Django](https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/) desaconseja usar el servidor de desarrollo en producción.

### A02 — P1: puertos internos publicados y configuración HTTP local

**Confirmado.** [Compose](/Users/humberto/Documents/CRM/Django-CRM-master/docker-compose.yml:17) publica PostgreSQL `5432` y Redis `6379` sin limitar la dirección de escucha. La configuración de Redis mostrada no añade autenticación. También se publican directamente los puertos de aplicación.

El entorno actual tiene `DEBUG=True`, CORS global habilitado, cookies Django sin atributo secure, sin redirección HTTPS desde Django y sin cabecera de proxy SSL configurada. `check --deploy` señala W008, W012, W016 y W018.

**Impacto:** si se sube tal cual a un servidor accesible, puede exponer servicios internos y manejar sesiones sobre un transporte/configuración inadecuados. No se ha demostrado que tu ordenador esté actualmente expuesto a Internet.

**Cierre:** DB/Redis en red privada; publicar únicamente el proxy; restringir hosts y orígenes; configurar HTTPS, cookies y proxy de confianza. Verificar el entorno efectivo, no solo un archivo de ejemplo. La redirección puede estar en el proxy si se prueba correctamente.

### A03 — P1: administrador predeterminado y secretos de desarrollo

**Confirmado.** [create_default_admin.py](/Users/humberto/Documents/CRM/Django-CRM-master/backend/common/management/commands/create_default_admin.py:17) crea un superusuario Django y usa una contraseña predeterminada si falta `ADMIN_PASSWORD`. Compose ejecuta ese comando automáticamente. `.env.docker` está versionado con valores de desarrollo.

El superusuario global de Django no debe confundirse con el Super Admin de una organización.

**Cierre:** producción debe rechazar secretos ausentes y nunca crear un administrador con una contraseña conocida. Provisionar la administración de forma explícita; generar secretos nuevos fuera del repositorio; excluir cuentas demo/locales del entorno de clientes. No se encontraron credenciales reales comprometidas mediante la búsqueda limitada realizada, pero eso no sustituye escanear todo el historial Git antes de publicar el repositorio.

### A04 — P1: actualizar WeasyPrint antes de publicar PDF

**Confirmado:** versión instalada **69.0**. El auditor Python detectó **CVE-2026-55073 / GHSA-jf6q-chmf-3h3v**, relacionado con parámetros que pueden eludir un URL fetcher personalizado. Los dos puntos actuales de [generación PDF](/Users/humberto/Documents/CRM/Django-CRM-master/backend/invoices/pdf.py:542) pasan objetos CSS con el fetcher restringido y no pasan `xmp_metadata`; no se confirmó una ruta explotable por ese mecanismo en estas llamadas.

La revisión del proveedor encontró además **GHSA-r543-q48m-4c9j**, que permite llegar al intérprete Ghostscript mediante imágenes EPS. La versión 70.0 corrige ambos problemas. **Ghostscript no está instalado en el contenedor backend observado**, por lo que no se confirmó esa cadena de ejecución allí. El fetcher admite data URI; no conviene depender únicamente de la ausencia actual de Ghostscript. Fuentes: [aviso de parámetros PDF](https://github.com/Kozea/WeasyPrint/security/advisories/GHSA-jf6q-chmf-3h3v), [aviso de imágenes EPS](https://github.com/Kozea/WeasyPrint/security/advisories/GHSA-r543-q48m-4c9j) y [versión de seguridad 70.0](https://github.com/Kozea/WeasyPrint/releases/tag/v70.0).

**Cierre:** actualizar a una versión corregida compatible, regenerar el lockfile, repetir pruebas PDF y limitar recursos del renderizador. Mantener restricciones de red/archivos y revisar redirecciones del host permitido. No se ejecutaron cargas maliciosas contra los datos del CRM.

### A05 — P1: pruebas funcionales todavía en rojo

**Confirmado:** 29 fallos de backend y 4 de frontend. No equivalen a 33 errores del producto. Varias pruebas aún esperan campos obligatorios generales, eventos de notas en Activity o privilegios administrativos que contradicen los cambios que solicitaste.

**Cierre:** actualizar pruebas únicamente cuando la nueva especificación esté confirmada; corregir los fallos reales; mantener las pruebas de límites de organización, permisos y etapas. No se debe borrar o ignorar una prueba solo para poner CI en verde. El desglose está en la sección 6.

### A06 — P1: dominio y correo de producción aún no están preparados

**Confirmado.** [server_settings.py](/Users/humberto/Documents/CRM/Django-CRM-master/backend/crm/server_settings.py:134) conserva `SESSION_COOKIE_DOMAIN = '.bottlecrm.io'`; afecta a sesiones Django en el dominio propio. El runtime actual envía a Mailpit, con remitente local. Esto sirve para pruebas, no demuestra entrega a buzones reales.

**Cierre:** usar dominio propio, configurar `ORIGIN` del frontend y callbacks OAuth, cookies y URLs públicas; configurar SMTP/SES y un remitente autorizado. Probar invitación, código de acceso, recuperación de sesión y Help de extremo a extremo. Verificar DNS de correo y entrega efectiva. No activar enlaces de acceso local en producción.

### A07 — P1 para lanzamiento: recuperación, operación y datos reales no validados

**Brecha de validación**, no afirmación de que no pueda configurarse. No se realizó una restauración de backup, un rollback de despliegue, una prueba de recuperación de archivos ni una comprobación de alertas en un entorno productivo.

**Cierre:** backup cifrado de PostgreSQL y archivos, retención y restauración probada; monitorizar web, workers, scheduler y errores; comprobar trabajos retrasados/reintentos y evitar dos schedulers ejecutando lo mismo. Preparar una organización limpia; mantener la demo separada con datos ficticios. Definir quién responde ante una caída y cuánto dato se admite perder.

### A08 — P2; P1 antes de ofrecer API: catálogo de scopes desactualizado

**Confirmado por prueba.** [common/scopes.py](/Users/humberto/Documents/CRM/Django-CRM-master/backend/common/scopes.py:51) no incluye ocho recursos que existen en las rutas: `help`, `permissions`, `pipeline-settings`, `property-layout`, `record-associations`, `record-delete`, `reports` y `sales-appointments`.

**Impacto:** no se pueden expresar correctamente permisos API específicos para esos recursos; un token limitado puede no acceder a una función necesaria. No se demostró que esto permita saltarse RBAC. Usar un token global para evitar el problema ampliaría innecesariamente su alcance.

**Cierre:** actualizar el catálogo y comprobar cada recurso con credenciales permitidas y denegadas; revisar el comportamiento heredado de tokens sin scopes antes de distribuir integraciones.

### A09 — P2: cerrar el inventario de excepciones RLS

**Confirmado:** el usuario efectivo de la aplicación es `crm_user`, sin superusuario ni BYPASSRLS. De 73 tablas con `org_id`, 66 tienen RLS activado. Las siete restantes son `cases_ticketsequence`, `common_organizationinvitation`, `personal_access_token`, `portal_access_token`, `portal_login_token`, `profile` y `security_audit_log`.

**No se interpreta esta lista como siete filtraciones.** Algunas tablas participan en autenticación o acceso global y requieren una estrategia diferente. Se observan filtros explícitos por organización, por ejemplo en invitaciones. Las pruebas RLS ejecutadas pasaron.

**Cierre:** documentar por qué cada excepción es necesaria y añadir comprobaciones entre organizaciones para sus operaciones de lectura/escritura. Revisar también el fallback heredado de perfiles sin un conjunto de permisos configurado. La defensa debe seguir funcionando aunque un futuro endpoint olvide filtrar.

### A10 — P2: CI y publicación conservan supuestos del proyecto original

**Confirmado.** [tests.yml](/Users/humberto/Documents/CRM/Django-CRM-master/.github/workflows/tests.yml:20) filtra pull requests a `master`, pero esta rama es `main`. Sí ejecuta determinados checks al hacer push en cualquier rama, por lo que no significa ausencia total de CI. Los filtros de archivos no cubren toda la configuración de despliegue.

[publish.yml](/Users/humberto/Documents/CRM/Django-CRM-master/.github/workflows/publish.yml) conserva el destino PyPI `django-crm` y nombres heredados. Eso no demuestra que el fork tenga permiso para publicar allí; debe ajustarse antes de crear releases.

**Cierre:** checks obligatorios para `main`, cobertura de cambios Docker/configuración, namespace propio o deshabilitación del flujo PyPI si no se necesita; secretos y entornos del fork verificados. No se comprobó la configuración remota de branch protection.

### A11 — P2: privacidad de telemetría y servicios externos

**Confirmado en código, condicionado a que se habilite Sentry.** El backend configura `send_default_pii=True` y trazas al 100%. El frontend también permite PII, replay del 10% de sesiones y del 100% de sesiones con errores. La activación del frontend depende del DSN.

**Cierre:** usar un proyecto propio, revisar qué campos se envían, aplicar redacción de datos/tokens y definir retención y muestreo. Las fuentes se cargan desde Google Fonts; decidir si se alojan localmente. No se demostró una transferencia indebida de datos durante esta revisión.

### A12 — P2: módulos pendientes siguen siendo superficie del producto

El distintivo Review es una indicación visual. La demo tiene restricciones específicas, pero el distintivo por sí mismo no desactiva endpoints para organizaciones normales.

**Cierre:** definir el alcance de la primera versión y deshabilitar de forma consistente UI/API de funciones que no se van a ofrecer. Es especialmente relevante para módulos heredados de facturación, portal, documentos y funcionalidades no adaptadas. No es necesario terminar todos para lanzar un CRM más acotado.

### A13 — P2/P3: rendimiento y mantenimiento

**Confirmado:** la prueba de Goals aumenta de 10 a 17 consultas al aumentar registros. En Tasks las dos pruebas hacen 13 consultas en lugar de 12: es un incremento fijo observado, no evidencia de N+1 por fila. En serialización de eventos hay comprobaciones de permisos por evento/asistente que conviene medir con calendarios grandes.

**Cierre:** corregir el crecimiento en Goals o dejar el módulo fuera del lanzamiento; medir consultas y latencia en listados, reportes y calendarios con volúmenes representativos. Resolver Ruff/formato y las advertencias del esquema API. No hay benchmark que permita prometer una escala concreta.

### A14 — P2 antes de distribución: avisos de terceros y configuración móvil

La licencia MIT original está en la raíz. Los Dockerfiles no copian explícitamente ese archivo a los artefactos finales de backend/frontend. No se encontró un inventario consolidado `THIRD_PARTY_NOTICES`.

El móvil aún apunta al proyecto Firebase `bottlecrm-io`. Su API key es un identificador de proyecto y no debe tratarse automáticamente como una contraseña filtrada; aun así, no se debe publicar una app de tu marca usando el proyecto ajeno. Véase la [documentación de Firebase](https://firebase.google.com/docs/projects/api-keys).

**Cierre:** generar inventario final de componentes y avisos para los artefactos distribuidos; mantener atribuciones; configurar proyectos y credenciales propios. El móvil queda fuera del visto bueno de esta auditoría.

## 5. Autenticación, autorización y aislamiento

### Controles positivos observados

- Organización obtenida del JWT firmado y membresía validada; no se acepta libremente un `org_id` enviado por el cliente como prueba de acceso.
- Contexto RLS y zona horaria limpiados al finalizar la petición, importante para conexiones y workers reutilizados.
- PostgreSQL utiliza un rol que no puede saltarse RLS; pruebas específicas ejecutadas en PostgreSQL real y aislado.
- Permisos propios/equipo/organización y acciones aplicados en backend para los objetos principales; cobertura adicional en calendario, reportes, asociaciones, archivos y administración de roles.
- Protección de la jerarquía de administradores y del creador de la organización; cambios de conjuntos de permisos generan auditoría.
- Códigos de acceso con hash, caducidad y uso único; límite de intentos y bloqueo de fila al verificar. Refresh tokens con rotación/invalidación.
- Restricciones para que credenciales API no creen otras credenciales arbitrariamente.
- Acceso local de desarrollo condicionado por configuración local/DEBUG; no se interpretó ese comando como un bypass público universal.
- El renderizador PDF tiene un fetcher restrictivo para red y archivos. No se encontraron usos activos de `{@html}` en el barrido del frontend; las coincidencias fueron comentarios preventivos.

### Lo que falta comprobar para autorizar el lanzamiento

Ejecutar la matriz final con Super Admin, Admin, Manager, Member y un rol personalizado, tanto por UI como por API. Para cada objeto: ver/listar/buscar, crear, editar, eliminar, exportar, asociar y adjuntar. Incluir otro equipo, otra organización y un usuario desactivado; intentar las URLs directamente, no solo navegar por botones.

La solicitud de códigos limita por email; conviene añadir y probar protección por IP/global y límites atómicos para evitar abuso de envío usando muchas direcciones. Validar las integraciones Google reales y la revocación de acceso por usuario. Estas comprobaciones pendientes no son evidencia de una fuga ya ocurrida.

## 6. Interpretación de las pruebas que fallaron

| Grupo de backend | Cantidad | Evaluación |
| --- | ---: | --- |
| Campos generales obligatorios en Accounts, Cases, Tasks y propiedades múltiples | 4 | Expectativa antigua frente a propiedades opcionales; conservar validación por reglas de etapa |
| Correo CSAT que exige branding BottleCRM | 1 | Expectativa de marca antigua |
| Ventana de fechas en reporte de tiempo | 1 | Abierto: el test usa reloj real y el inicio se calcula antes del final; reproducir con reloj fijo y límites de día/zona horaria |
| Prohibición de referencias al audit log | 1 | El test detecta escritura desde roles; no demostró exposición del log. Ajustar la regla sin permitir lectura indebida |
| Directorio de documentación API ausente en contenedor | 1 | Montaje del entorno de pruebas; verificar también en CI |
| Detector de parámetros de rutas | 1 | Confunde selectores de módulo/tipo con IDs; revisar validación y detector |
| Disponibilidad de calendario | 1 | Cambió el alcance de acceso al host; confirmar contrato de respuesta y expectativa |
| Catálogo de scopes | 1 | Desajuste real de recursos, A08 |
| Usuarios, eliminación y privilegios administrativos | 7 | Rutas/semántica antiguas frente a nueva administración y Super Admin; reconciliar con pruebas actuales |
| Historial de contactos | 2 | Espera creación/notas como eventos frente a Activity centrada en cambios y notas separadas |
| Cierre de Deals exige importe/fecha por defecto | 6 | Expectativas anteriores; ahora dependen de reglas configuradas de etapa |
| Crecimiento de consultas en Goals | 1 | Regresión de consultas confirmada |
| Conteo fijo de consultas Tasks | 2 | 13 frente a 12; no crece entre las dos cantidades probadas |
| **Total** | **29** | Ningún fallo debe quedar sin resolución o explicación comprobada |

Frontend: dos pruebas esperan rechazar etapas por una lista fija antigua; ahora existen etapas configurables y debe comprobarse la validación real del backend. Otras dos esperan eventos de notas/archivos dentro del historial. Hay que asegurar que notas y archivos siguen visibles en sus secciones antes de actualizar esas expectativas.

## 7. Autoría, licencias y posibilidad de comercialización

### Código base

[LICENSE](/Users/humberto/Documents/CRM/Django-CRM-master/LICENSE) identifica **MIT, Copyright (c) 2017 MicroPyramid**. Esa licencia concede permiso para usar, modificar, distribuir y vender el software, condicionado a conservar el aviso de copyright y licencia. Para esos usos del código cubierto por MIT no hace falta solicitar una autorización adicional al autor. No exige publicar todas tus modificaciones ni mantener el branding visual de BottleCRM. Esto no concede derechos sobre marcas, logos o material que tenga otra licencia. Fuente: [texto MIT de OSI](https://opensource.org/license/mit).

Puedes usar High Demand Media como marca y añadir tu atribución por las modificaciones. Debe permanecer la atribución original donde corresponda; no conviene presentar el código base completo como si fuera de autoría exclusiva de High Demand Media. No se verificó documentalmente la titularidad del logo aportado ni posibles acuerdos externos de colaboradores.

### Dependencias: no todo es MIT

Se inventariaron 332 combinaciones de nombre/versión JavaScript instaladas. El inventario local puede incluir versiones de desarrollo o antiguas y no sustituye el inventario del artefacto final. Cuatro paquetes sin metadato de licencia (`runed` y `svelte-toolbelt`, dos versiones cada uno) sí contienen un LICENSE MIT.

| Componente/familia observada | Licencia | Acción relevante |
| --- | --- | --- |
| Base Django-CRM | MIT | Mantener copyright y licencia originales |
| Mayoría de JS/Python | MIT, BSD, ISC, Apache y otras | Conservar avisos aplicables según distribución |
| Psycopg, binary y pool 3.3.5 | LGPL-3.0 | Revisar obligaciones de biblioteca al redistribuir imágenes/binarios; no asumir que obliga automáticamente a abrir todo el CRM |
| Lightning CSS | MPL-2.0 | Mantener avisos y cumplir obligaciones sobre archivos cubiertos cuando se distribuyan |
| caniuse-lite | CC-BY-4.0 | Mantener atribución de los datos cuando corresponda |
| Sentry CLI 2.58.6 y binario de plataforma | FSL-1.1-MIT | Herramienta de build; revisar uso permitido y distribución. No tratarla como MIT actual sin más |
| Redis observado **7.4.11** | **RSALv2 o SSPLv1** | Elegir/documentar licencia y uso; no asumir BSD por llamarse Redis |
| Imágenes base, sistema operativo, móvil y fuentes | Inventario final incompleto | Incluirlos en el inventario de la release antes de redistribuir paquetes/imágenes |

Redis confirma que 7.4 usa licencia dual RSALv2/SSPLv1. Su documentación distingue un producto que utiliza Redis de un servicio que compite ofreciendo su funcionalidad. El uso interno como caché/broker del CRM parece corresponder al primer caso; es una interpretación del uso observado, no una aprobación contractual de cualquier futura oferta. No seleccionar SSPL sin entender sus condiciones. Fuente: [licencias oficiales de Redis](https://redis.io/legal/licenses/).

La LGPL añade condiciones para distribuir una biblioteca o un trabajo combinado; el uso de Psycopg no convierte por sí solo todo el SaaS en código LGPL. Revisar la forma concreta de distribución. Fuente: [licencia de Psycopg](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt). La FSL distingue uso permitido de uso competitivo y contempla conversión posterior; consultar la versión incluida con la herramienta. Fuente: [Functional Source License](https://fsl.software/).

**Conclusión sobre derechos:** sí existe permiso base para comercializar; queda trabajo de cumplimiento del conjunto distribuido. Esta revisión técnica de licencias no certifica titularidad de todos los activos ni reemplaza una revisión jurídica si se van a distribuir binarios, vender licencias o firmar garantías a clientes.

## 8. Arquitectura y capacidad

La aplicación tiene un backend Django modular, frontend SvelteKit, PostgreSQL, Redis y workers/scheduler Celery. Separar estos procesos en contenedores es útil, pero no convierte cada dominio del CRM en un microservicio independiente. Para el primer lanzamiento no hace falta una reescritura ni Kubernetes: hace falta una configuración de producción operable y probada.

La cantidad de usuarios registrados no permite deducir la capacidad. Deben fijarse concurrencia, volumen de contactos/eventos/archivos, frecuencia de reportes y tiempos de respuesta aceptables. Medir con datos representativos, especialmente permisos, listados, calendarios, exportaciones y reportes por fecha. No se hizo una prueba que sustente el objetivo original de un millón de usuarios.

## 9. Secuencia recomendada para el primer lanzamiento

1. **Cerrar la versión a publicar.** Identificar los cambios locales, definir módulos habilitados y separar datos demo. Crear un commit de release solo cuando lo autorices.
2. **Corregir los bloqueos confirmados.** Eliminar el fallback de contraseña de producción, actualizar WeasyPrint, configurar dominio/correo y preparar el runtime productivo privado.
3. **Poner las comprobaciones en verde.** Resolver los 29+4 fallos según su causa; reparar scopes, CI de `main` y los checks pertinentes. Mantener PostgreSQL/RLS en CI.
4. **Completar licencias y secretos.** Inventario del artefacto final, avisos incluidos en imágenes, elección documentada de Redis, proyectos externos propios y escaneo del historial Git.
5. **Desplegar en staging privado.** Misma configuración e imágenes que producción, organización limpia, TLS y almacenamiento privado. Verificar correo, OAuth, formularios, archivos, etapas, merge, eliminación y reportes.
6. **Probar permisos, backup y recuperación.** Matriz de roles/equipos/organizaciones, restauración completa, rollback y alertas de workers/web.
7. **Piloto controlado.** Pocos usuarios, métricas y seguimiento de errores; después ampliar. Publicar solo cuando los criterios anteriores estén cumplidos o exista una excepción explícita y acotada para una función deshabilitada.

### Criterios de aceptación de la release

- Configuración productiva sin DEBUG ni accesos locales/demo, DB/Redis privados y secretos nuevos.
- Sin administrador predeterminado; jerarquía de organización y permisos probados.
- Dependencias con avisos relevantes corregidos; compilación y pruebas obligatorias en verde.
- Dominios/cookies/orígenes correctos; correos llegan a un buzón externo y OAuth usa proyectos propios.
- Notas, adjuntos, reportes y cambios de etapa funcionan con los permisos de cada rol.
- Restore y rollback demostrados; monitoreo operativo.
- Licencias/atribuciones incluidas, alcance de módulos definido y política de datos para clientes preparada.

## 10. Evidencia conservada

Los archivos están fuera del código de aplicación, en `/Users/humberto/Documents/CRM/work/`. Pueden contener nombres de rutas internas y detalles de pruebas; no están preparados como material público de marketing.

- [Backend: resultado completo](/Users/humberto/Documents/CRM/work/audit-backend-tests.log)
- [PostgreSQL/RLS: siete pruebas](/Users/humberto/Documents/CRM/work/audit-postgres-rls-tests.log)
- [Frontend: pruebas](/Users/humberto/Documents/CRM/work/audit-frontend-tests.log)
- [Frontend: compilación](/Users/humberto/Documents/CRM/work/audit-frontend-build.log)
- [Frontend: comprobación estática](/Users/humberto/Documents/CRM/work/audit-frontend-check.log)
- [Diagnóstico de despliegue](/Users/humberto/Documents/CRM/work/audit-deploy-check.log)
- [Migraciones](/Users/humberto/Documents/CRM/work/audit-migrations.log)
- [Ruff](/Users/humberto/Documents/CRM/work/audit-ruff.json)
- [Formato](/Users/humberto/Documents/CRM/work/audit-format.log)
- [Paquetes Python: auditoría](/Users/humberto/Documents/CRM/work/audit-pip.json)
- [Paquetes JavaScript: auditoría](/Users/humberto/Documents/CRM/work/audit-npm.json)
- [Inventario de licencias JavaScript](/Users/humberto/Documents/CRM/work/audit-js-licenses.json)
- [Resumen de configuración e inventario Python](/Users/humberto/Documents/CRM/work/audit-runtime.json)
- [Inventario de tablas RLS](/Users/humberto/Documents/CRM/work/audit-rls-tables.json)
- [Coincidencias del barrido limitado de secretos](/Users/humberto/Documents/CRM/work/audit-secret-patterns.json)

Este informe documenta hallazgos y comprobaciones al 23 de septiembre de 2026. No se modificaron las funciones auditadas para ocultar o corregir resultados durante la revisión.
