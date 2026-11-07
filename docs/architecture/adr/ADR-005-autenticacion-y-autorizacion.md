# ADR-005 · Autenticación y autorización en el borde HTTP

- **Estado:** Aceptada
- **Fecha:** 6 de noviembre de 2026
- **Equipo:** 12 (CleanPro)
- **Relacionada con:** RNF-02 (seguridad), ADR-001 (Domain Model), arquitectura de capas Dominio / Aplicación / Infraestructura

## Contexto

Hasta ahora la API aceptaba en el cuerpo de cada petición el identificador de quien actuaba (`cliente_id`, `coordinador_id`, `supervisor_id`, `admin_id`). Cualquiera podía hacerse pasar por otro usuario con solo escribir otro id, y la interfaz tenía un selector de rol sin ninguna comprobación. Para una aplicación publicada en internet se necesita saber **quién** hace cada petición y **qué rol** tiene, sin ensuciar el dominio con detalles de seguridad.

Restricciones: el proyecto prioriza pocas dependencias (el CI y la imagen Docker deben seguir siendo simples), el despliegue gratuito en Render corre una sola instancia y la solución debe poder explicarse y probarse por completo en la defensa.

## Decisión

1. **La autenticación vive en el borde HTTP** (`src/api/`). El dominio no conoce usuarios ni tokens: recibe un `Actor` ya resuelto. El id del actor sale siempre del usuario autenticado, nunca del cuerpo de la petición; los campos de id de actor se eliminaron de los esquemas de entrada y, si alguien los envía, se ignoran.
2. **Contraseñas con PBKDF2-HMAC-SHA256**, 600 000 iteraciones y sal aleatoria de 16 bytes, guardadas como `pbkdf2_sha256$<iteraciones>$<sal>$<hash>`. La comparación usa `hmac.compare_digest`.
3. **Tokens firmados con HMAC-SHA256** con el formato `<payload>.<firma>` (base64url). El payload lleva `sub` (usuario), `rol` y `exp` (vencimiento). Vigencia por defecto de 1 hora. El secreto viene de `CLEANPRO_SECRET` (mínimo 16 caracteres).
4. **El rol se lee de la base en cada petición** y el `rol` que viaja en el token se ignora. Desactivar a un usuario o cambiarle el rol se aplica al instante, sin esperar a que el token venza.
5. **Autorización por rol en cada endpoint** con la dependencia `requiere(*roles)`, que responde `403 SIN_PERMISO` antes de cualquier otra validación. El dominio vuelve a validar el rol (defensa en profundidad). Un cliente solo consulta sus propias cotizaciones y servicios.
6. **Limitador de intentos:** tras 5 fallos seguidos de un usuario, el login responde `429 DEMASIADOS_INTENTOS` durante 60 segundos, incluso con la clave correcta. Un acierto reinicia la cuenta.
7. **Sin enumeración de usuarios:** un usuario inexistente y una clave incorrecta devuelven la misma respuesta (`401 CREDENCIALES_INVALIDAS`) y hacen el mismo trabajo de cómputo.
8. **Usuarios de demo** (`cliente1..3`, `coord1`, `sup1`, `admin1`) cargados con `CLEANPRO_DEMO=1`, con la contraseña de `CLEANPRO_CLAVE_DEMO` (por defecto `cleanpro123`).

## Alternativas descartadas

- **JWT con una biblioteca externa** (por ejemplo PyJWT): añade una dependencia para un token con solo tres campos. El formato propio es corto, se prueba por completo (`tests/test_seguridad.py`) y evita configurar algoritmos de firma. A cambio, no es un estándar interoperable: si en el futuro otro sistema debiera validar estos tokens, convendría migrar a JWT.
- **OAuth2 con formulario** (`OAuth2PasswordBearer` y flujo de contraseña): obliga a enviar el login como formulario y a cargar más piezas, y no aporta nada con un solo proveedor de identidad. Se usa `HTTPBearer`, que en Swagger permite pegar el token directamente.
- **Confiar en el rol del token:** más simple y sin consulta a la base, pero un usuario dado de baja conservaría su acceso hasta que el token venza. Se prefirió la consulta por petición.
- **Sesiones en servidor (cookie):** obligarían a guardar estado de sesión y a manejar CSRF; no encaja con una API consumida también desde Swagger y otros clientes.

## Consecuencias

**Positivas**
- El dominio queda libre de seguridad; las reglas de negocio no cambiaron.
- No se agregó ninguna dependencia: todo usa la biblioteca estándar de Python.
- La suplantación por id en el cuerpo ya no es posible, y la autorización se prueba por rol y endpoint (`tests/test_autorizacion.py`).

**Límites conocidos (se documentan en el reporte)**
- Los servicios de aplicación aún construyen el `Actor` con un rol fijo; el rol real se exige en la API. Mejora futura: pasar el `Actor` autenticado a los comandos.
- El limitador vive en la memoria del proceso: sirve para una instancia. Con varias habría que moverlo a la base de datos o a Redis.
- No hay cierre de sesión en el servidor: el token vive hasta que vence (1 hora) o hasta que se desactiva al usuario.
- No hay endpoint para crear o administrar usuarios; los de demo se cargan al arrancar.
- Si no se cambia `CLEANPRO_CLAVE_DEMO`, la clave de demo es pública. Todos los usuarios de demo comparten la misma contraseña.
- Sin `CLEANPRO_SECRET`, el servidor usa un secreto aleatorio y las sesiones se pierden al reiniciar; en producción debe definirse.
