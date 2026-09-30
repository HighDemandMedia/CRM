# Conectar formularios de una web al CRM

Cada organización configura sus formularios en **Settings → Channels & integrations → Web forms**. Un envío válido crea un **Contact** en esa organización y avisa al responsable y a los usuarios elegidos. Los clientes pueden usar este módulo; no requiere acceso a funciones en preview.

## Partes de la pantalla

- **Configure:** nombre interno, sitios conectados, campos que se guardarán, confirmación al visitante, responsable y avisos. Las etiquetas y la protección adicional contra spam son opcionales.
- **Connect to website:** elige entre conectar tu formulario actual o insertar uno construido por el CRM. Copia solo el código de la opción elegida.
- **Submissions:** revisa los envíos recibidos, si crearon un contacto o se asociaron a uno existente, y abre el contacto para darle seguimiento.
- **Save configuration:** guarda tus cambios. Cambiar de pestaña conserva lo escrito, pero no lo guarda.
- **Publish / Unpublish:** activa o detiene la recepción de nuevos envíos. Guarda antes de publicar; los contactos existentes se conservan al detenerla.

## Configuración

1. Un administrador crea un formulario y le pone un nombre reconocible, por ejemplo “Consulta de la página de servicios”.
2. Selecciona las propiedades que desea recibir. **Name** y **Email** son obligatorias. El ID, la organización y la etapa inicial los asigna el CRM.
3. En **Matching field on your website**, escribe el atributo `name` del campo de la web: si el HTML dice `<input name="your-email">`, escribe `your-email` junto a Email. Se pueden conectar propiedades personalizadas activas de Contact.
4. Elige el responsable, el origen y las etiquetas para los contactos nuevos. Activa los avisos en el CRM y por correo, y selecciona los destinatarios adicionales.
5. En **Website addresses**, añade el origen exacto del sitio, por ejemplo `https://example.com`. Añade también `https://www.example.com` si utilizas ambas versiones. No incluyas rutas. La lista autoriza al navegador; no sustituye las medidas antispam.
6. Guarda y publica. Los borradores no reciben envíos.
7. Copia **Connect to website → I already have a form** en la página. Pon `id="contact-form"` en el formulario, o cambia `data-form="#contact-form"` al selector que identifique exactamente ese formulario.
8. Envía una consulta de prueba y revisa **Submissions**, el contacto, la campana de notificaciones y el correo de los destinatarios.

El código mantiene el diseño del formulario, pero **se encarga de su envío**. Debes sustituir cualquier manejador de envío anterior. Si un formulario de una plataforma ya tiene procesamiento propio, integra el endpoint desde ese procesamiento; no añadas dos manejadores que compitan. El código se instala una sola vez por formulario.

También puedes copiar el iframe o el script del CRM para añadir un formulario nuevo a una página.

## Qué ocurre al recibir un envío

- Los datos pasan por las validaciones del CRM. Se ignoran propiedades no configuradas; no se pueden asignar permisos, organización, responsables ni citas desde el sitio.
- Si el correo no existe en esa organización, se crea un contacto en la etapa inicial, con el origen, responsable y etiquetas del formulario.
- Si ya existe, se vincula el envío a ese contacto. **No se sustituyen sus datos, etapa ni responsable**. El mensaje se añade como comentario, identificado con el nombre del formulario.
- Se guarda el envío en el historial del formulario. Solo los administradores pueden consultar sus datos completos.
- Se avisa al responsable configurado, a los responsables actuales del contacto existente y a los usuarios adicionales seleccionados. Deben estar activos, pertenecer a la organización y tener permiso para ver ese contacto. La preferencia personal de avisos en el CRM se respeta.
- Los correos se envían individualmente desde el remitente del sistema que ya utiliza el CRM. No es necesario que cada destinatario conecte su Gmail.
- Los avisos en el CRM se guardan junto con el contacto. El correo se procesa en segundo plano; el scheduler recupera envíos pendientes cada cinco minutos si hubo una interrupción.

## Límites y protección

- El conector solo recoge los campos mapeados del formulario seleccionado. No recoge contraseñas, archivos ni campos ocultos. Usa propiedades de texto, selecciones y casillas apropiadas al tipo de propiedad del CRM.
- Incluye un campo señuelo y límites de frecuencia. Puedes configurar Cloudflare Turnstile por formulario; autoriza también los dominios de tu web en Turnstile.
- Si falla la entrega, se conservan los datos escritos y se muestra un error. Cada envío lleva un identificador reutilizado al reintentar: los reintentos no generan otra entrada ni otro aviso dentro del CRM.
- Dos consultas distintas del mismo correo sí generan dos entradas de historial. La respuesta pública no revela si el contacto ya existía.
- Los formularios existentes que creaban Leads conservan su destino. Los nuevos creados desde la interfaz crean Contacts.
- “Views” y la conversión corresponden a los formularios incrustados del CRM. Los envíos de HTML externo cuentan como submissions, pero el conector no mide vistas de la página.
- La página debe permitir cargar el script desde el servidor API y hacer conexiones a él si utiliza una política CSP. La verificación real del dominio y de su configuración se realiza al instalarlo allí.

## Integración desde código propio

El editor muestra el endpoint público de ese formulario. Acepta `POST` con un objeto JSON cuyos nombres son las propiedades del CRM (`first_name`, `email`, `description`, etc.), no los alias de HTML. El conector hace esa traducción automáticamente.

Incluye `request_id` como UUID nuevo por consulta y reutilízalo solo en reintentos de la misma consulta. Si Turnstile está activo, incluye `cf-turnstile-response`. Envía un encabezado `Origin` permitido. Este endpoint no utiliza credenciales privadas del CRM: no pongas tokens de usuario en una web pública.

Una respuesta HTTP 200 con `status: "ok"` confirma la recepción. Una respuesta 400 contiene errores de validación; 403 indica origen no permitido; 404 puede indicar que el formulario está sin publicar; 429 pide esperar antes de reintentar. No des por recibido un envío si falla la conexión.

## Despliegue

Los cambios requieren la migración `webforms.0003`, desplegar **API, Worker, Scheduler y Web** con el mismo código, y mantener los servicios de correo y cola existentes. No requieren nuevas credenciales ni variables de entorno. La migración no cambia el destino de formularios antiguos ni reenvía sus correos históricos.

Después del despliegue queda instalar el código en cada web y hacer una prueba real. Las pruebas locales no confirman por sí mismas la configuración de Render, Google ni la página externa.
