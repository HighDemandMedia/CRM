# Acceso personal y creación de organizaciones

Actualizado: 24 de septiembre de 2026.

## Crear una cuenta

Abre `/register`. Introduce nombre, email, nombre de organización y una contraseña personal de al menos 10 caracteres. La contraseña se confirma y valida en el servidor; no se guarda en texto plano ni se devuelve al navegador.

El registro crea una organización nueva. Su creador es Super Admin **de esa organización**, no superusuario global de Django. La zona horaria se toma del navegador y se puede cambiar después. La creación de usuario, organización y membresía es una sola transacción.

Por ahora el registro normal no exige un código enviado por email. Esto no debe interpretarse como verificación de propiedad de la dirección. Antes de abrir registro público masivo hay que configurar correo real y revisar verificación/abuso de registro. `PASSWORD_REGISTRATION_ENABLED=false` cierra el registro público; las invitaciones válidas siguen funcionando.

## Entrar e invitar

En `/login` utiliza email y contraseña. Una sola organización activa se selecciona automáticamente; si perteneces a varias, eliges una. El formulario no concede acceso por escribir el nombre o ID de una organización.

Los usuarios adicionales reciben una invitación. El enlace ofrece entrar con una cuenta existente o crear una cuenta nueva con contraseña. El nuevo usuario debe usar el email de la invitación y recibe exactamente la organización y el rol concedidos. El token se consume al registrarse; no se crea una organización adicional.

Un email existente no puede registrarse otra vez ni cambiar su contraseña desde el registro. No se sobrescriben cuentas anteriores ni se asigna una contraseña compartida a toda la organización.

## Contraseña y recuperación

En Profile → Personal information aparece Set your password o Change password. Si ya existe una contraseña utilizable se solicita la actual. Las cuentas previas que entraban por correo pueden usar un enlace de acceso verificado y establecer su contraseña allí.

En `/login`, la opción de recuperación envía un enlace por email. Tras verificarlo hay una ventana de 10 minutos para cambiar la contraseña sin conocer la anterior. El permiso de recuperación está dentro del token firmado y caduca aunque se cambie de organización o se renueve la sesión. No se puede obtener enviando un campo desde el navegador.

Cambiar la contraseña invalida los refresh tokens anteriores. Además, los JWT incorporan la huella del hash de contraseña, y el backend rechaza los tokens previos al cambio. Las sesiones anteriores a esta actualización también necesitarán entrar nuevamente.

En desarrollo los correos llegan a Mailpit (`http://localhost:8025`); registro e inicio de sesión con contraseña no requieren correo. Para recuperación e invitaciones fuera de tu computadora hace falta SMTP/SES real.

## Limpieza de servicios heredados

- Eliminados Google Analytics, Sentry y grabación de sesiones. Retiradas las dependencias Sentry y su CLI del frontend/backend.
- La fuente Manrope se sirve desde el propio CRM; ya no se solicita a Google Fonts.
- Retirados el enlace a la app de BottleCRM y los datos de financiación del proyecto original.
- Eliminados los workflows de publicación del paquete original. La CI permanece y contempla `main`.
- Cookies Django sin dominio fijo de BottleCRM; pueden usar `SESSION_COOKIE_DOMAIN` si el despliegue lo necesita.
- WeasyPrint actualizado a 70 con fetcher adaptado; sin redirecciones a hosts no autorizados. Retirada la dependencia directa sin uso `cairocffi`.
- En el código móvil se eliminó Firebase/Crashlytics, su configuración de proyecto y los servidores predeterminados ajenos. Una compilación release móvil requiere `API_BASE_URL` propio. La app móvil no se compiló: este cambio entrega el acceso nuevo para la web.

Se conservan PostgreSQL, Redis/Celery, almacenamiento, correo y las librerías necesarias para las funciones existentes. Las licencias originales, atribuciones, migraciones históricas y algunas claves internas de compatibilidad se mantienen; no son conexiones activas a BottleCRM. El LICENSE MIT se incluye también en los artefactos Docker.

Esto no completa por sí solo los restantes bloqueos de producción del informe de auditoría.

## Verificación de esta entrega

- 452 pruebas de autenticación, invitaciones, almacenamiento y facturas: aprobadas.
- 18 pruebas de acceso ejecutadas también con PostgreSQL y usuario sin privilegios de superusuario: aprobadas.
- 3 pruebas de sesión/cookies del frontend: aprobadas.
- Revisión de Svelte: cero errores y advertencias; compilación de producción correcta.
- Generación real de PDF y bloqueo de URL interna: verificados.
- La suite general del frontend mantiene cuatro fallos anteriores del informe de auditoría (pipeline e historial de contactos); no se presentan como corregidos por este cambio.
