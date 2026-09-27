# Revisión antes del commit — 27 de septiembre de 2026

Se guarda el trabajo local acumulado desde `94f3f8b`: Help y base de conocimiento, permisos ampliados, autenticación personal por email/contraseña, recuperación de acceso, limpieza de telemetría y conexiones heredadas, actualización de PDF y ajustes de interfaz del login.

## Verificación de esta revisión

- Backend: 97 pruebas aprobadas en contraseña, permisos ampliados, roles, Help y configuración de almacenamiento.
- Frontend: 7 pruebas aprobadas en sesiones/cookies, navegación demo y artículos de Help.
- Svelte: cero errores y cero advertencias.
- Compilación de producción del frontend: correcta.
- Modelos: `makemigrations --check --dry-run` sin cambios pendientes.
- `git diff --check`: correcto.
- Barrido de patrones reconocibles de credenciales en archivos modificados y nuevos: sin credenciales detectadas; se revisó una URL de ejemplo con contraseña ficticia en el README. Este barrido no sustituye un análisis exhaustivo de todo el historial.

No se repitió la suite general completa. Los fallos generales y limitaciones del informe del 23 de septiembre siguen siendo pendientes salvo los cierres documentados en `../access/password-login.md`. El móvil no se compiló. Las pruebas seleccionadas no certifican por sí solas que el proyecto esté listo para producción.

## Estado del despliegue

El destino previsto es un entorno Staging para testers. No se añadieron todavía los servicios remotos ni una configuración de despliegue de producción. La elección de Google para correo está pendiente de implementación: el backend conserva su configuración de correo actual.

El login ya no muestra Create account ni el icono de correo en recuperación. La ruta de registro sigue disponible; cerrar el registro público del entorno online continúa siendo una tarea del despliegue.

El cambio del email del administrador se hizo en la base de datos local: no es contenido de este commit. Un commit de Git conserva código y documentación, no los registros de la base de datos ni adjuntos.
