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
MONGO_USER=your_user
MONGO_PASS=your_password
MONGO_HOST=localhost
MONGO_DB=webmail_improvmx

# Dominio a escuchar
DOMINIO=your_domain
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

## 🔐 Seguridad

### Características de Seguridad Implementadas

1. **Autenticación Bearer Token:** Todos los endpoints protegidos requieren autenticación vía Bearer Token

2. **Rate Limiting:** Límites de velocidad para prevenir abuso y asegurar uso justo del API

3. **Protección contra Fuerza Bruta:** Bloqueo automático de IPs con múltiples intentos fallidos de autenticación

4. **SSL/TLS:** **Importante** - Este webhook NO configura SSL/TLS. La gestión de SSL se realiza exclusivamente mediante Caddy, que actúa como reverse proxy y maneja automáticamente los certificados HTTPS.

### Configuración de Variables de Entorno

El archivo `.env` debe incluir la variable de autenticación:

```env
# API Authentication
API_KEY=your_secure_256_bit_token_here

# MongoDB Config
MONGO_USER=your_user
MONGO_PASS=your_password
MONGO_HOST=localhost
MONGO_DB=webmail_improvmx

# Dominio a escuchar
DOMINIO=your_domain
```

### Endpoints y Autenticación

#### Endpoints Públicos (Sin Autenticación)

| Método | Endpoint | Descripción | Rate Limit |
|--------|----------|-------------|------------|
| GET | `/docs` | Documentación del API | 60/minuto |
| POST | `/webhook` | Recepción de correos desde ImprovMX | 200/minuto |

#### Endpoints Protegidos (Requieren Autenticación)

| Método | Endpoint | Descripción | Rate Limit |
|--------|----------|-------------|------------|
| GET | `/` | Health check | 30/minuto |
| GET | `/emails` | Listar correos | 20/minuto |
| GET | `/emails/<email_id>` | Obtener correo específico | 30/minuto |
| GET | `/emails/<email_id>/attachment/<name>` | Descargar adjunto | 10/minuto |

### Uso de la API con Autenticación

Para acceder a los endpoints protegidos, debes incluir el header de autorización:

```bash
curl -X GET http://localhost:42010/emails \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Rate Limiting

**Límites globales por IP:**
- 200 solicitudes por día
- 50 solicitudes por hora

**Respuesta cuando se excede el límite:**
```json
{
  "error": "Rate limit exceeded: 30 per 1 minute"
}
```

**Código HTTP:** 429 Too Many Requests

### Protección contra Fuerza Bruta

**Reglas:**
- Máximo 5 intentos fallidos de autenticación
- Intentos contados en ventana de 5 minutos
- Bloqueo de IP por 15 minutos tras exceder límite
- Limpieza automática de intentos antiguos

**Respuesta cuando IP está bloqueada:**
```json
{
  "success": false,
  "error": "Too many failed attempts. Please try again later."
}
```

**Código HTTP:** 429 Too Many Requests

### Documentación Completa

Para más detalles sobre autenticación, rate limiting y seguridad, consulta:

- **`API_AUTHENTICATION.md`** - Documentación completa de seguridad del API
  - Explicación detallada de autenticación Bearer Token
  - Tablas de rate limiting por endpoint
  - Ejemplos de uso en cURL, Python y JavaScript
  - Guía de testing de características de seguridad
  - Sección de troubleshooting

### Sugerencias Adicionales de Seguridad

1. **Rotación de API Keys:** Rotar regularmente las claves API para mantener la seguridad

2. **IP Whitelisting:** Considera implementar whitelisting de IPs para endpoints sensibles

3. **Monitoring:** Implementar monitoreo de intentos fallidos y actividades sospechosas

4. **Log Rotation:** Configurar rotación de logs para mantener el sistema limpio

5. **Firewall:** Configura tu firewall para permitir tráfico solo en el puerto 42010 desde Caddy

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

## 🌐 Problema de Conexión a SMTP de ImprovMX (Timeout al Enviar Correos)

**Síntoma:** Al intentar enviar correos a través de smtp.improvmx.com, se experimentan tiempos de espera excesivos (timeouts) que pueden durar varios minutos antes de que la conexión falle o tenga éxito.

**Causa:** El problema ocurre porque el sistema intenta conectarse primero usando IPv6 antes de IPv4. Si la red o el servidor no tiene soporte IPv6 completo o si hay problemas de routing IPv6, el intento de conexión IPv6 falla después de un largo tiempo de espera antes de intentar con IPv4.

**Diagnóstico:**

```bash
# Verificar la resolución DNS de smtp.improvmx.com
nslookup smtp.improvmx.com
# o
dig smtp.improvmx.com

# Verificar cuál protocolo se está intentando usar
ping smtp.improvmx.com
ping6 smtp.improvmx.com

# Probar conexión al puerto SMTP (587) con timeout
timeout 5 nc -zv smtp.improvmx.com 587
```

**Solución - Forzar Conexión IPv4 mediante /etc/hosts:**

1. **Obtener las direcciones IPv4 de smtp.improvmx.com:**
```bash
# Obtener solo direcciones IPv4
dig smtp.improvmx.com +short A

# Ejemplo de salida (puede variar):
# 54.230.200.20
# 54.230.200.50
```

2. **Editar el archivo /etc/hosts:**
```bash
sudo nano /etc/hosts
```

3. **Agregar las direcciones IPv4 de smtp.improvmx.com:**
```bash
# Agregar al final del archivo /etc/hosts
54.230.200.20 smtp.improvmx.com
54.230.200.50 smtp.improvmx.com
```

4. **Guardar el archivo y probar la conexión:**
```bash
# Verificar que la resolución usa /etc/hosts
ping smtp.improvmx.com

# Probar conexión SMTP rápida
timeout 5 nc -zv smtp.improvmx.com 587
```

**Verificación de que la solución funcionó:**

```bash
# La resolución DNS ahora debería mostrar solo las IPs de /etc/hosts
nslookup smtp.improvmx.com

# El ping debería responder inmediatamente (sin timeout)
ping -c 2 smtp.improvmx.com

# La conexión al puerto SMTP debería ser rápida
time nc -zv smtp.improvmx.com 587
```

**Mantenimiento de la solución:**

Es importante mantener actualizadas las direcciones IPv4 en /etc/hosts ya que ImprovMX podría cambiarlas en el futuro. Se recomienda:

1. **Crear un script de verificación:**
```bash
#!/bin/bash
# Script: check_smtp_ips.sh

echo "Direcciones IPv4 actuales de smtp.improvmx.com:"
dig smtp.improvmx.com +short A

echo ""
echo "Direcciones configuradas en /etc/hosts:"
grep smtp.improvmx.com /etc/hosts
```

2. **Verificar periódicamente si las IPs han cambiado:**
```bash
# Ejecutar el script
chmod +x check_smtp_ips.sh
./check_smtp_ips.sh
```

3. **Actualización automatizada (opcional):**
```bash
#!/bin/bash
# Script: update_smtp_hosts.sh

# Obtener nuevas IPs
NEW_IPS=$(dig smtp.improvmx.com +short A | grep -E '^[0-9]')

# Eliminar entradas antiguas
sudo sed -i '/smtp.improvmx.com/d' /etc/hosts

# Agregar nuevas IPs
for ip in $NEW_IPS; do
    echo "$ip smtp.improvmx.com" | sudo tee -a /etc/hosts
done

echo "/etc/hosts actualizado con las IPs más recientes de smtp.improvmx.com"
```

**Solución alternativa - Deshabilitar IPv6:**

Si prefieres una solución más permanente y no necesitas IPv6 en tu sistema:

```bash
# Verificar si IPv6 está habilitado
cat /proc/sys/net/ipv6/conf/all/disable_ipv6
# 0 = habilitado, 1 = deshabilitado

# Deshabilitar IPv6 temporalmente
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1

# Para hacer el cambio permanente, editar /etc/sysctl.conf
echo "net.ipv6.conf.all.disable_ipv6=1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6=1" | sudo tee -a /etc/sysctl.conf

# Aplicar cambios
sudo sysctl -p
```

**⚠️ Importante:** Deshabilitar IPv6 puede afectar otros servicios que dependan de IPv6. La solución con /etc/hosts es más segura y solo afecta la conexión a smtp.improvmx.com.

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