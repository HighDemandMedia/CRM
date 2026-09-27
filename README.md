# High Demand Media CRM

CRM de High Demand Media, adaptado sobre Django-CRM Community.

## Acceso

Usa email y contraseña personal en `/login`. En `/register`, el nombre, email, contraseña y organización crean una cuenta nueva. El creador es Super Admin de su organización; no es administrador global de Django. Los usuarios adicionales se incorporan por invitación.

Las cuentas existentes pueden establecer o cambiar su contraseña en Profile. Si olvidaste la contraseña, usa la recuperación por enlace de correo. En desarrollo, los correos se reciben en Mailpit.

## Desarrollo local

`docker compose up --build` inicia el entorno de desarrollo. Este Compose no es una configuración lista para producción. Consulta `docs/access/password-login.md` y el informe en `docs/audits/`.

## Licencia y autoría

Basado en Django-CRM, Copyright (c) 2017 MicroPyramid, bajo licencia MIT. Se conservan la licencia y los derechos de sus autores en `LICENSE`. Las modificaciones de producto y marca corresponden al proyecto High Demand Media. Las dependencias mantienen sus propias licencias.
