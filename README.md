# ImprovMX Webhook Server

Un servidor webhook para recibir y almacenar correos electrónicos enviados a través de ImprovMX, utilizando Flask y Gunicorn con MongoDB como base de datos.

## 📋 Características

- ✅ Recepción de correos vía webhook en el puerto 42010
- ✅ Almacenamiento automático en MongoDB
- ✅ API REST para consultar correos
- ✅ Soporte para adjuntos e imágenes inline
- ✅ Logs detallados de actividad
- ✅ Configuración optimizada con Gunicorn
- ✅ CORS habilitado para acceso web

## 🚀 Configuración Inicial

### Prerrequisitos

- Python 3.8+
- MongoDB 4.0+
- Caddy 2.0+ (para SSL/TLS y reverse proxy)
- pip (gestor de paquetes de Python)

### Arquitectura del Sistema

Este webhook está diseñado para funcionar con Caddy como reverse proxy:

- **Caddy**: Maneja SSL/TLS y actúa como reverse proxy (puerto 443/80)
- **Gunicorn**: Servidor WSGI Python (puerto 42010, solo localhost)
- **Flask**: Aplicación web que procesa los webhooks
- **MongoDB**: Base de datos para almacenar los correos

⚠️ **Importante:** No se configura SSL directamente en Gunicorn/Flask. SSL es manejado exclusivamente por Caddy.

### 1. Instalación de Dependencias

```bash
# Crear entorno virtual (opcional pero recomendado)
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración de Variables de Entorno

El archivo `.env` debe contener las siguientes variables:

```env
# MongoDB Config
MONGO_USER=Admin
MONGO_PASS=sloch1618
MONGO_HOST=localhost
MONGO_DB=webmail_improvmx

# Dominio a escuchar
DOMINIO=puntoa.ar
```

## 🏃 Ejecución del Servidor

### Instalación como Servicio Systemd (Recomendado para Producción)

Esta es la forma recomendada de ejecutar el webhook en producción.

**Instalación automática:**

```bash
# Ejecutar el instalador con permisos de root
sudo ./install_service.sh
```

El instalador realizará:
- ✅ Verificar conexión a MongoDB
- ✅ Crear entorno virtual si no existe
- ✅ Instalar dependencias Python
- ✅ Configurar permisos de usuario
- ✅ Instalar servicio systemd
- ✅ Habilitar inicio automático
- ✅ Iniciar el servicio
- ✅ Verificar funcionamiento

**Comandos de gestión del servicio:**

```bash
# Ver estado del servicio
sudo systemctl status improvmx-webhook

# Iniciar servicio
sudo systemctl start improvmx-webhook

# Detener servicio
sudo systemctl stop improvmx-webhook

# Reiniciar servicio
sudo systemctl restart improvmx-webhook

# Recargar configuración (sin interrupción)
sudo systemctl reload improvmx-webhook

# Ver logs en tiempo real
sudo journalctl -u improvmx-webhook -f

# Ver últimos 50 líneas de logs
sudo journalctl -u improvmx-webhook -n 50
```

**Desinstalar el servicio:**

```bash
# Ejecutar el desinstalador
sudo ./uninstall_service.sh
```

### Ejecución Manual con Gunicorn (Desarrollo/Testing)

```bash
# Cargar variables de entorno
export $(cat .env | grep -v '^#' | xargs)

# Iniciar Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

### Ejecución con Flask (Desarrollo)

```bash
python app.py
```

El servidor escuchará en `http://0.0.0.0:42010`

**Nota:** El puerto 42010 es interno y debe ser accesible solo desde Caddy. El acceso público es mediante HTTPS gestionado por Caddy.

## 📡 Endpoints del API

### 1. Webhook de Recepción de Correos

**POST** `/webhook`

Recibe correos desde ImprovMX y los almacena en MongoDB.

**Ejemplo de Request:**
```json
{
    "headers": {
        "X-Forwarding-Service": "ImprovMX v3.0.0",
        "Received-SPF": ["pass (improvmx.com: domain of example.com designates xxx.xxx.xxx.xxx as permitted sender)"]
    },
    "to": [{"name": "Usuario", "email": "usuario@puntoa.ar"}],
    "from": {"name": "Remitente", "email": "remitente@example.com"},
    "subject": "Asunto del correo",
    "text": "Contenido en texto plano",
    "html": "<p>Contenido HTML</p>",
    "attachments": [...],
    "inlines": [...]
}
```

**Response:**
```json
{
    "success": true,
    "message": "Email received and stored",
    "email_id": "507f1f77bcf86cd799439011"
}
```

### 2. Health Check

**GET** `/`

Verifica que el servidor esté funcionando correctamente.

**Response:**
```json
{
    "status": "healthy",
    "service": "ImprovMX Webhook",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 3. Listar Correos

**GET** `/emails`

Recupera correos almacenados con opciones de filtrado y paginación.

**Parámetros Query:**
- `limit`: Número de correos a retornar (default: 10)
- `skip`: Número de correos a saltar (default: 0)
- `from_email`: Filtrar por email del remitente
- `subject`: Filtrar por asunto (búsqueda parcial)

**Ejemplos:**
```bash
# Obtener los últimos 10 correos
curl http://localhost:42010/emails

# Obtener correos filtrados por remitente
curl http://localhost:42010/emails?from_email=test@example.com

# Buscar por asunto
curl http://localhost:42010/emails?subject=importante

# Paginación
curl http://localhost:42010/emails?limit=20&skip=10
```

**Response:**
```json
{
    "success": true,
    "count": 5,
    "emails": [
        {
            "_id": "507f1f77bcf86cd799439011",
            "subject": "Asunto del correo",
            "from": {"name": "Remitente", "email": "remitente@example.com"},
            "to": [{"name": "Usuario", "email": "usuario@puntoa.ar"}],
            "received_at": "2024-01-15T10:30:00.000Z",
            ...
        }
    ]
}
```

### 4. Obtener Correo Específico

**GET** `/emails/<email_id>`

Recupera un correo específico por su ID.

**Ejemplo:**
```bash
curl http://localhost:42010/emails/507f1f77bcf86cd799439011
```

### 5. Descargar Adjunto

**GET** `/emails/<email_id>/attachment/<attachment_name>`

Descarga un adjunto específico de un correo.

**Ejemplo:**
```bash
curl -O -J http://localhost:42010/emails/507f1f77bcf86cd799439011/attachment/documento.pdf
```

## 🧪 Pruebas

### Script de Prueba Automatizada

```bash
# Asegúrate de que el servidor esté corriendo
python test_webhook.py
```

El script realizará las siguientes pruebas:
1. ✅ Envío de un correo de prueba
2. ✅ Verificación del health check
3. ✅ Recuperación de lista de correos
4. ✅ Obtención de un correo específico

### Prueba Manual con cURL

```bash
# Health check
curl http://localhost:42010/

# Enviar correo de prueba
curl -X POST http://localhost:42010/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "to": [{"email": "test@puntoa.ar"}],
    "from": {"email": "sender@example.com", "name": "Test Sender"},
    "subject": "Test Email",
    "text": "This is a test email",
    "html": "<p>This is a test email</p>"
  }'

# Obtener correos
curl http://localhost:42010/emails
```

## 📊 Estructura de Datos en MongoDB

Cada correo se almacena en la colección `emails` con el siguiente esquema:

```javascript
{
    "_id": ObjectId,
    "headers": {
        "X-Forwarding-Service": String,
        "Received-SPF": [String],
        "Delivered-To": String,
        "DKIM-Signature": [String],
        "Authentication-Results": [String]
    },
    "to": [{ "name": String, "email": String }],
    "from": { "name": String, "email": String },
    "subject": String,
    "message-id": String,
    "date": String,
    "return-path": { "name": String, "email": String },
    "timestamp": Number,
    "text": String,
    "html": String,
    "inlines": [{
        "type": String,
        "name": String,
        "content": String (base64),
        "cid": String
    }],
    "attachments": [{
        "type": String,
        "name": String,
        "content": String (base64),
        "encoding": String
    }],
    "received_at": ISODate,
    "processed": Boolean
}
```

## 🔧 Configuración de Gunicorn

El archivo `gunicorn.conf.py` contiene la configuración de producción:

- **Bind:** 0.0.0.0:42010
- **Workers:** (CPU cores × 2) + 1
- **Timeout:** 30 segundos
- **Log Level:** INFO
- **Worker Class:** sync

Para ajustar el número de workers según tu carga:

```python
# En gunicorn.conf.py
workers = 4  # Ajusta según necesidad
```

## 🔐 Seguridad

### Consideraciones de Seguridad

1. **SSL/TLS:** **Importante** - Este webhook NO configura SSL/TLS. La gestión de SSL se realiza exclusivamente mediante Caddy, que actúa como reverse proxy y maneja automáticamente los certificados HTTPS.

2. **Autenticación:** Actualmente no hay autenticación en los endpoints. Considera agregar:
   - API Keys
   - JWT tokens
   - OAuth

3. **Rate Limiting:** Implementa límites de velocidad para prevenir abusos

4. **Validación de Entrada:** Los datos se validan básicamente. Considera usar una librería de validación más robusta.

5. **Firewall:** Configura tu firewall para permitir tráfico solo en el puerto 42010 desde Caddy

### Sugerencias de Mejoras de Seguridad

```python
# Agregar autenticación básica con API Key
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('API_KEY'):
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/webhook', methods=['POST'])
@require_api_key
def receive_email():
    # ...
```

## 🐛 Solución de Problemas

### MongoDB Connection Failed

```bash
# Verificar que MongoDB esté corriendo
sudo systemctl status mongodb

# Iniciar MongoDB si no está corriendo
sudo systemctl start mongodb

# Verificar credenciales en .env
```

### Puerto Ya en Uso

```bash
# Encontrar el proceso usando el puerto 42010
lsof -i :42010

# Matar el proceso
kill -9 <PID>
```

### Errores de Permisos

```bash
# Asegúrate de tener permisos de escritura
chmod +x start.sh
```

### Ver Logs de Gunicorn

```bash
# Los logs se muestran en stdout/stderr
# Para guardar logs en archivo:
gunicorn -c gunicorn.conf.py app:app >> server.log 2>&1
```

## 📦 Despliegue en Producción

### Instalación Automática del Servicio Systemd

Para un despliegue rápido y automatizado en producción:

```bash
# Ejecutar el instalador
sudo ./install_service.sh
```

Este método es **recomendado** porque:
- Automatiza todo el proceso de instalación
- Verifica dependencias y configuraciones
- Configura permisos y seguridad
- Habilita inicio automático en boot
- Incluye verificaciones post-instalación

### Instalación Manual del Servicio Systemd

Si prefieres una instalación manual más detallada:

1. **Crear entorno virtual:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configurar permisos:**

```bash
sudo chown -R www-data:www-data /home/jose/webmail_improvmx
```

3. **Instalar el servicio:**

```bash
# Copiar el archivo de servicio
sudo cp improvmx-webhook.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable improvmx-webhook

# Iniciar el servicio
sudo systemctl start improvmx-webhook
```

4. **Verificar instalación:**

```bash
# Ver estado
sudo systemctl status improvmx-webhook

# Ver logs
sudo journalctl -u improvmx-webhook -f
```

### Configuración de Caddy (Proxy Inverso y SSL)

**Nota:** Este webhook está diseñado para funcionar con Caddy como reverse proxy. Caddy maneja automáticamente:
- Terminación SSL/TLS
- Renovación automática de certificados
- Reverse proxy al puerto 42010
- Headers necesarios

**Ejemplo de configuración de Caddy:**

```caddyfile
webhook.puntoa.ar {
    reverse_proxy localhost:42010
    
    # Caddy maneja SSL/TLS automáticamente con Let's Encrypt
    # No se requiere configuración adicional de certificados
    
    # Headers opcionales de seguridad
    header {
        X-Real-IP {remote_host}
        X-Forwarded-For {remote_host}
        X-Forwarded-Proto {scheme}
    }
}
```

**Si prefieres usar Nginx en lugar de Caddy:**

```nginx
server {
    listen 80;
    server_name webhook.puntoa.ar;

    location / {
        proxy_pass http://localhost:42010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

⚠️ **Importante:** El webhook escucha únicamente en HTTP (puerto 42010). SSL/TLS debe ser manejado por Caddy o Nginx como reverse proxy.

## 📝 Integración con ImprovMX

1. Inicia sesión en tu cuenta de ImprovMX
2. Ve a la configuración de tu dominio
3. Configura el webhook URL: `https://tu-dominio.com/webhook`
   - **Importante:** Usa HTTPS ya que Caddy maneja SSL automáticamente
   - El puerto 42010 es interno y no debe incluirse en la URL pública
4. Asegúrate de que el servidor sea accesible públicamente
5. Verifica que el puerto 42010 esté abierto solo para conexiones locales desde Caddy
6. Configura Caddy para hacer el reverse proxy del tráfico HTTPS al puerto 42010

**Arquitectura de red:**
```
ImprovMX → HTTPS → Caddy (SSL/TLS) → localhost:42010 → Flask App → MongoDB
```

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request para sugerencias.

## 📞 Soporte

Si encuentras algún problema o tienes preguntas, por favor abre un issue en el repositorio.