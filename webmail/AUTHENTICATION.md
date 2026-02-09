# Sistema de Autenticación - Webmail ImprovMX

## 📋 Resumen

El sistema de autenticación permite gestionar múltiples usuarios con control de acceso basado en roles. Cada usuario autenticado solo puede ver los correos dirigidos a su dirección de email correspondiente.

## 🔐 Características

- ✅ **Autenticación obligatoria**: Todos los usuarios deben iniciar sesión
- ✅ **Sistema de roles**: Usuarios y Administradores
- ✅ **Usuario admin por defecto**: Creado automáticamente si no existen usuarios
- ✅ **Panel de administración**: Solo accesible para administradores
- ✅ **Gestión de usuarios**: Crear, eliminar y cambiar roles
- ✅ **Seguridad**: Contraseñas hasheadas con bcrypt
- ✅ **Sesiones**: Gestión automática de sesiones con Flask-Login

## 🚀 Primeros Pasos

### 1. Usuario por Defecto

La primera vez que se inicie la aplicación, se creará automáticamente un usuario administrador:

- **Usuario/Email**: `webmaster`
- **Contraseña**: `admin123`
- **Rol**: `admin`

⚠️ **IMPORTANTE**: Cambia esta contraseña inmediatamente después del primer inicio.

### 2. Iniciar Sesión

```
URL: http://192.168.1.33:26000/login
```

Ingresa tus credenciales:
- **Email/Usuario**: Tu nombre de usuario (ej: `webmaster`, `jlvillaronga@puntoa.ar`)
- **Contraseña**: Tu contraseña

### 3. Configurar Usuarios

Como administrador, puedes crear nuevos usuarios:

1. Inicia sesión como `webmaster`
2. Ve a **Gestionar Usuarios** en el sidebar
3. Completa el formulario:
   - **Email/Usuario**: La dirección de correo del usuario (ej: `usuario@dominio.com`)
   - **Contraseña**: Mínimo 6 caracteres
   - **Nombre**: Nombre del usuario (opcional)
   - **Rol**: `Usuario` o `Administrador`
4. Click en **Crear Usuario**

## 👥 Roles de Usuario

### Administrador
- ✅ Acceso a todos los correos
- ✅ Panel de administración
- ✅ Crear nuevos usuarios
- ✅ Eliminar usuarios (excepto el propio)
- ✅ Cambiar roles de otros usuarios
- ✅ Ver correos de cualquier destinatario

### Usuario
- ✅ Ver solo correos dirigidos a su email
- ✅ Marcar correos como leídos
- ✅ Buscar correos
- ❌ No puede acceder al panel de administración
- ❌ No puede gestionar usuarios

## 📊 Flujo de Autenticación

### 1. Login
```
Usuario → Login → Verificación → Sesión activa → Dashboard
```

### 2. Visualización de Correos
```
Usuario autenticado → Filtro por email → Correos del usuario
```

### 3. Administración
```
Admin → Panel admin → Crear/Eliminar usuarios → Cambios en MongoDB
```

## 🔧 API Endpoints

### Autenticación

#### `POST /login`
Inicia sesión del usuario.

**Parámetros:**
- `email`: Email o nombre de usuario
- `password`: Contraseña

**Respuesta:**
- Redirect a `/` si es exitoso
- Mensaje de error si falla

#### `GET /logout`
Cierra la sesión del usuario.

**Respuesta:**
- Redirect a `/login`

### Administración

#### `GET /admin/users`
Lista todos los usuarios (solo administradores).

**Requiere:** Rol de administrador

**Respuesta:** Página con tabla de usuarios

#### `POST /admin/users`
Crea o elimina usuarios (solo administradores).

**Parámetros para crear:**
- `action`: `create`
- `email`: Email del usuario
- `password`: Contraseña
- `name`: Nombre (opcional)
- `role`: `user` o `admin`

**Parámetros para eliminar:**
- `action`: `delete`
- `user_id`: ID del usuario a eliminar

#### `POST /admin/users/<user_id>/toggle-role`
Cambia el rol de un usuario entre admin y user.

**Requiere:** Rol de administrador
**Nota:** No puedes cambiar tu propio rol

## 🗄️ Base de Datos

### Colección: `users`

Estructura de documento:

```javascript
{
  "_id": ObjectId("..."),
  "email": "usuario@dominio.com",
  "password_hash": "$2b$12$...",  // bcrypt hash
  "name": "Nombre del Usuario",
  "role": "admin" | "user",
  "created_at": ISODate("2024-01-15T10:30:00Z")
}
```

### Consultas MongoDB

**Verificar usuario:**
```javascript
db.users.findOne({email: "webmaster"})
```

**Listar todos los usuarios:**
```javascript
db.users.find().sort({created_at: -1})
```

**Actualizar rol:**
```javascript
db.users.updateOne(
  {_id: ObjectId("...")},
  {$set: {role: "admin"}}
)
```

## 🔒 Seguridad

### Contraseñas
- Almacenadas como hashes bcrypt
- Mínimo 6 caracteres
- Nunca se almacenan en texto plano

### Sesiones
- Flask-Login gestiona automáticamente las sesiones
- Las sesiones expiran al cerrar el navegador (configurable)
- Protección CSRF automática

### Autenticación
- Decorador `@login_required` en todas las rutas protegidas
- Verificación automática en cada petición
- Redirección a `/login` si no está autenticado

### Recomendaciones de Seguridad

1. **Cambiar contraseña del admin por defecto**
   ```bash
   # Opción 1: Desde el panel de administración
   # Opción 2: Directamente en MongoDB
   from werkzeug.security import generate_password_hash
   db.users.update_one(
       {email: "webmaster"},
       {$set: {password_hash: generate_password_hash("nueva-contraseña")}}
   )
   ```

2. **Usar contraseñas fuertes**
   - Mínimo 12 caracteres
   - Mayúsculas, minúsculas, números y símbolos
   - No usar palabras comunes

3. **Configurar SECRET_KEY en producción**
   ```env
   SECRET_KEY=tu-clave-secreta-aleatoria-muy-larga
   ```

4. **Limitar número de administradores**
   - Solo 2-3 usuarios con rol admin
   - La mayoría deberían ser usuarios normales

5. **Habilitar HTTPS**
   - Configurar Caddy con SSL/TLS
   - Nunca usar HTTP en producción

## 🛠️ Troubleshooting

### No puedo iniciar sesión

**Problema:** Credenciales incorrectas

**Solución:**
1. Verifica que el usuario existe en MongoDB
2. Revisa las mayúsculas/minúsculas del email
3. Si olvidaste la contraseña, elimina y recrea el usuario

```javascript
// Verificar usuario en MongoDB
db.users.find({email: "tu-email"})
```

### El usuario webmaster no fue creado

**Problema:** El usuario por defecto no existe

**Solución:**
```python
# Ejecutar en Python
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime

client = MongoClient("mongodb://Admin:sloch1618@localhost")
db = client["webmail_improvmx"]
users = db["users"]

admin = {
    "email": "webmaster",
    "password_hash": generate_password_hash("admin123"),
    "name": "Webmaster",
    "role": "admin",
    "created_at": datetime.utcnow()
}
users.insert_one(admin)
```

### No puedo ver correos después de iniciar sesión

**Problema:** El usuario no tiene correos o el email no coincide

**Solución:**
1. Verifica que el usuario email coincida con el destinatario de los correos
2. Revisa en MongoDB:
```javascript
// Buscar correos para este usuario
db.emails.find({
  $or: [
    {"to.email": "tu-email@dominio.com"},
    {"envelope.recipient": "tu-email@dominio.com"}
  ]
})
```

### Error: "Access denied"

**Problema:** Intentando acceder a correos de otro usuario

**Solución:**
- Los usuarios normales solo pueden ver correos dirigidos a su email
- Los administradores pueden ver todos los correos
- Verifica que el usuario tenga el rol correcto

## 📝 Ejemplos de Uso

### Crear usuario para `jlvillaronga@puntoa.ar`

1. Inicia sesión como `webmaster`
2. Ve a **Gestionar Usuarios**
3. Llena el formulario:
   - Email: `jlvillaronga@puntoa.ar`
   - Contraseña: `contraseña-segura`
   - Nombre: `Jose Luis`
   - Rol: `Usuario`
4. Click en **Crear Usuario**

### Promover usuario a administrador

1. Inicia sesión como `webmaster`
2. Ve a **Gestionar Usuarios**
3. Busca el usuario
4. Click en **Cambiar Rol**
5. Confirma el cambio

### Eliminar usuario

1. Inicia sesión como `webmaster`
2. Ve a **Gestionar Usuarios**
3. Busca el usuario
4. Click en el ícono de **basura**
5. Confirma la eliminación

⚠️ **Nota:** No puedes eliminar tu propio usuario

## 🔐 Consideraciones de Producción

### Configuración Recomendada

1. **Cambiar SECRET_KEY**
   ```env
   SECRET_KEY=$(openssl rand -hex 32)
   ```

2. **Configurar HTTPS**
   - Usar Caddy como reverse proxy
   - Certificados SSL/TLS automáticos
   - Nunca exponer el puerto 26000 directamente

3. **Implementar rate limiting**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   
   @app.route('/login', methods=['POST'])
   @limiter.limit("5 per minute")
   def login():
       ...
   ```

4. **Agregar logging**
   ```python
   import logging
   logging.basicConfig(filename='auth.log', level=logging.INFO)
   ```

5. **Backups automáticos**
   ```bash
   # Backup de usuarios
   mongodump --db webmail_improvmx --collection users --out /backup
   ```

## 📚 Referencias

- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [Werkzeug Security](https://werkzeug.palletsprojects.com/en/2.3.x/utils/#module-werkzeug.security)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🆘 Soporte

Si encuentras problemas:

1. Revisa los logs: `journalctl -u webmail -f`
2. Verifica la conexión a MongoDB
3. Revisa los usuarios en la base de datos
4. Consulta la documentación general en `README.md`