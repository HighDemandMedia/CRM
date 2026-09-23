# Acceso y equipos: entorno local

## Iniciar con correo de pruebas

Desde la raíz del repositorio:

```sh
docker compose -f docker-compose.yml -f docker-compose.mail.yml up -d
```

Usar ambos archivos también al recrear los servicios para conservar el correo local.
Mailpit captura los mensajes; no los entrega a direcciones reales. La bandeja está
en http://localhost:8025 y solo escucha en la computadora local. Es una herramienta
de desarrollo, no una configuración para producción.

## Entrar

1. Abrir http://localhost:5173/login e introducir el correo, por ejemplo admin@example.com.
2. Abrir la bandeja local y el mensaje de acceso más reciente.
3. Abrir el enlace de acceso en el navegador donde se usará el CRM.
4. Seleccionar la organización.

El acceso es por enlace de correo, sin contraseña. Google se muestra únicamente
cuando está configurado. En producción se necesita un proveedor real de correo
y revisar los ajustes de registro, dominios, cookies y HTTPS.

## Invitar y administrar

En Team and access, un Admin puede enviar, reenviar y cancelar invitaciones.
Las invitaciones duran siete días; reenviar invalida el enlace anterior.
El destinatario debe iniciar sesión con el mismo correo y aceptar explícitamente.
Enviar una invitación no crea inmediatamente un miembro con acceso.

Se pueden crear equipos y editar sus integrantes. Los integrantes deben ser
usuarios activos de la misma organización. Desactivar un miembro revoca sus
tokens de API; reactivarlo no restaura esos tokens.

## Alcance de este primer bloque

Implementado: correo local, acceso por enlace, invitaciones pendientes con
aceptación, administración existente de Admin/Member y edición de equipos.

Pendiente antes de cerrar la fase de acceso: definir e implementar Owner/Manager,
la matriz de permisos por módulo y alcance propio/equipo/organización, validar
esos permisos en todos los endpoints y verificar el aislamiento con PostgreSQL.
La existencia de un equipo no implica por sí sola nuevos permisos de registros.

También quedan para sus fases correspondientes las propiedades y pipelines
configurables, reglas por etapa, perfil e integraciones de Google.
