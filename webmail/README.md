# Webmail Application - ImprovMX

Una aplicación web moderna y responsive para visualizar correos electrónicos recibidos a través del servicio webhook de ImprovMX y almacenados en MongoDB.

## 📋 Características

- ✅ Interfaz web moderna con Bootstrap 5
- ✅ Diseño responsive (móvil y desktop)
- ✅ Filtrado por dirección de correo electrónico
- ✅ Búsqueda por asunto, remitente o contenido
- ✅ Carpetas: Bandeja de entrada, No leídos, Todos los correos
- ✅ Visualización de correos HTML y texto plano
- ✅ Soporte para imágenes inline (CID)
- ✅ Información de seguridad (SPF, DKIM, DMARC)
- ✅ Paginación de resultados
- ✅ Indicador de correos no leídos
- ✅ Sidebar colapsable en móviles
- ✅ Menú de navegación tipo webmail

## 🚀 Arquitectura del Sistema

```
Caddy (HTTPS) → Gunicorn (Puerto 26000) → Flask App → MongoDB
```

**Componentes:**
- **Caddy**: Maneja SSL/TLS y actúa como reverse proxy
- **Gunicorn**: Servidor WSGI Python (puerto 26000)
- **Flask**: Aplicación web que procesa las solicitudes
- **MongoDB**: Base de datos con los correos almacenados

## 📦 Instalación y Configuración

### Prerrequisitos

- Python 3.8+
- MongoDB 4.0+
- Caddy 2.0+ (para SSL/TLS y reverse proxy)
- pip (gestor de paquetes de Python)
- Virtual environment existente en `/home/jose/webmail_improvmx/venv`

### 1. Estructura de Directorios

```
/home/jose/webmail_improvmx/
├── .env                          # Variables de entorno (compartido)
├── venv/                         # Virtual environment (compartido)
├── webmail/                       # Directorio de la aplicación webmail
│   ├── app.py                     # Aplicación Flask principal
│   ├── gunicorn.conf.py           # Configuración de Gunicorn
│   ├── webmail.service            # Archivo de servicio systemd
│   ├── templates/                # Templates HTML
│   │   ├── base.html           # Template base con sidebar
│   │   ├── index.html          # Lista de correos
│   │   ├── view_email.html     # Visualización de correo
│   │   ├── error.html          # Página de error
│   │   └── no_email.html      # Error de email no proporcionado
│   └── README.md               # Este archivo
├── install_webmail_service.sh    # Instalador automático
└── start_webmail.sh             # Script de inicio para desarrollo
```

### 2. Instalación como Servicio Systemd (Producción)

Esta es la forma recomendada de ejecutar el webmail en producción.

**Instalación automática:**

```bash
# Ejecutar el instalador con permisos de root
sudo ./install_webmail_service.sh
```

El instalador realizará:
- ✅ Verificar conexión a MongoDB
- ✅ Usar el entorno virtual existente
- ✅ Instalar dependencias Python si es necesario
- ✅ Configurar permisos de usuario
- ✅ Instalar servicio systemd
- ✅ Habilitar inicio automático
- ✅ Iniciar el servicio
- ✅ Verificar funcionamiento

**Comandos de gestión del servicio:**

```bash
# Ver estado del servicio
sudo systemctl status webmail

# Iniciar servicio
sudo systemctl start webmail

# Detener servicio
sudo systemctl stop webmail

# Reiniciar servicio
sudo systemctl restart webmail

# Recargar configuración (sin interrupción)
sudo systemctl reload webmail

# Ver logs en tiempo real
sudo journalctl -u webmail -f

# Ver últimos 50 líneas de logs
sudo journalctl -u webmail -n 50
```

### 3. Ejecución Manual (Desarrollo/Testing)

```bash
# Desde el directorio principal
./start_webmail.sh
```

O manualmente:

```bash
cd webmail
source ../venv/bin/activate
export $(cat ../.env | grep -v '^#' | xargs)
gunicorn -c gunicorn.conf.py app:app
```

El servidor escuchará en `http://0.0.0.0:26000`

## 📡 Uso de la Aplicación

### Acceso a la Aplicación

**Importante:** La aplicación requiere el parámetro `email` en la URL para filtrar los correos.

```
https://tu-dominio.com/?email=usuario@dominio.com
```

**Ejemplos:**
```
https://webmail.puntoa.ar/?email=jlvillaronga@puntoa.ar
https://webmail.puntoa.ar/?email=info@puntoa.ar
```

### Filtrado de Correos

La aplicación filtra correos que coinciden con el parámetro `email`:

**Criterios de filtrado:**
1. Correos donde `to[].email` coincide con el email proporcionado
2. Correos donde `envelope.recipient` coincide con el email proporcionado

**Ejemplo de consulta MongoDB:**
```javascript
{
  "$or": [
    {"to.email": "jlvillaronga@puntoa.ar"},
    {"envelope.recipient": "jlvillaronga@puntoa.ar"}
  ]
}
```

### Carpetas Disponibles

- **Bandeja de entrada**: Todos los correos recibidos
- **No leídos**: Correos con `processed: false`
- **Todos los correos**: Todos los correos sin filtro

### Búsqueda

La búsqueda permite encontrar correos por:
- Asunto
- Remitente (email)
- Contenido del mensaje (texto)

## 🎨 Características de la Interfaz

### Diseño Responsive

- **Sidebar colapsable** en dispositivos móviles
- **Grid de Bootstrap** para adaptabilidad
- **Touch-friendly** para navegación móvil

### Elementos de UI

#### Sidebar
- Logo de la aplicación
- Navegación por carpetas
- Información de cuenta actual
- Iconos de Bootstrap Icons

#### Lista de Correos
- Indicador visual de correos no leídos (fondo amarillo)
- Badge "Nuevo" para correos no leídos
- Badge de adjuntos cuando corresponda
- Vista previa del contenido (snippet)
- Fecha formateada
- Información de remitente

#### Visualización de Correo
- Cabecera completa (De, Para, Fecha, ID)
- Verificación de seguridad (SPF, DKIM, DMARC)
- Contenido HTML o texto plano
- Imágenes inline procesadas
- Lista de adjuntos
- Botones de acción (Responder, Reenviar, Eliminar)
- Encabezados colapsables

### Colores y Estilos

- **Primary**: Azul (#0d6efd)
- **Warning**: Amarillo para no leídos (#ffc107)
- **Success**: Verde para verificaciones pasadas
- **Danger**: Rojo para errores
- **Gradient**: Sidebar con gradiente azul

## 🔧 Configuración de Variables de Entorno

La aplicación usa el archivo `.env` en el directorio principal:

```env
# MongoDB Config
MONGO_USER=Admin
MONGO_PASS=sloch1618
MONGO_HOST=localhost
MONGO_DB=webmail_improvmx

# Dominio a escuchar
DOMINIO=puntoa.ar
```

## 📊 Endpoints de la API

### 1. Página Principal (Lista de Correos)

```
GET /
```

**Parámetros Query:**
- `email` (requerido): Email del usuario
- `page`: Página actual (default: 1)
- `per_page`: Correos por página (default: 20)
- `search`: Término de búsqueda
- `folder`: Carpeta (inbox/unread/all, default: inbox)

**Ejemplo:**
```
GET /?email=jlvillaronga@puntoa.ar&page=1&per_page=20&folder=inbox
```

### 2. Visualización de Correo

```
GET /view/<email_id>
```

**Parámetros Query:**
- `email` (requerido): Email del usuario

**Ejemplo:**
```
GET /view/507f1f77bcf86cd799439011?email=jlvillaronga@puntoa.ar
```

### 3. Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Webmail Application",
  "timestamp": "2026-02-08T10:30:00.000Z"
}
```

## 🔒 Seguridad

### Consideraciones de Seguridad

1. **Filtrado por Email**: Los usuarios solo ven correos dirigidos a su email
2. **Validación de Recipiente**: Verificación doble (to.email y envelope.recipient)
3. **SSL/TLS**: Manejado por Caddy como reverse proxy
4. **No Autenticación**: La autenticación se maneja externamente

### Próximas Mejoras de Seguridad

- [ ] Implementar rate limiting
- [ ] Validación de parámetros más robusta
- [ ] Headers de seguridad HTTP
- [ ] CSP (Content Security Policy)
- [ ] Sanitización de contenido HTML

## 🧪 Pruebas

### Health Check

```bash
# Verificar que el servicio está corriendo
curl http://localhost:26000/health
```

### Prueba de Navegador

1. Acceder a: `http://localhost:26000/?email=test@dominio.com`
2. Debería mostrar la interfaz de webmail
3. Si hay correos en MongoDB, aparecerán en la lista

### Prueba de Búsqueda

1. Escribir un término en el buscador
2. Hacer clic en "Buscar"
3. Se mostrarán los resultados filtrados

## 🐛 Solución de Problemas

### Servicio no inicia

```bash
# Ver logs del servicio
sudo journalctl -u webmail -n 50

# Verificar MongoDB
sudo systemctl status mongod

# Verificar puerto
netstat -tulpn | grep 26000
```

### No aparecen correos

1. Verificar que el email del parámetro coincide con MongoDB
2. Verificar que el webhook está recibiendo correos
3. Consultar MongoDB directamente:
```bash
mongosh --username Admin --password --authenticationDatabase webmail_improvmx
use webmail_improvmx
db.emails.find({"to.email": "tu-email@dominio.com"})
```

### Conexión MongoDB fallida

```bash
# Verificar credenciales en .env
cat ../.env

# Verificar que MongoDB está corriendo
sudo systemctl status mongod

# Probar conexión manual
python3 -c "from pymongo import MongoClient; client = MongoClient('mongodb://Admin:password@localhost'); print(client.server_info())"
```

## 📦 Configuración de Gunicorn

El archivo `gunicorn.conf.py` contiene la configuración de producción:

- **Bind:** 0.0.0.0:26000
- **Workers:** (CPU cores × 2) + 1
- **Timeout:** 30 segundos
- **Log Level:** INFO
- **Worker Class:** sync

## 🌐 Configuración de Caddy (Reverse Proxy)

**Ejemplo de configuración de Caddy:**

```caddyfile
webmail.puntoa.ar {
    reverse_proxy localhost:26000
    
    # Caddy maneja SSL/TLS automáticamente con Let's Encrypt
    # No se requiere configuración adicional de certificados
    
    # Headers de seguridad
    header {
        X-Real-IP {remote_host}
        X-Forwarded-For {remote_host}
        X-Forwarded-Proto {scheme}
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
    }
}
```

## 📝 Integración con Sistema Existente

Esta aplicación webmail se integra con:

1. **Webhook de ImprovMX** (ya en producción en puerto 42010)
2. **MongoDB compartido** con datos de correos
3. **Entorno virtual compartido** en `/home/jose/webmail_improvmx/venv`
4. **Variables de entorno compartidas** desde `.env` principal

### Arquitectura Completa

```
                    ┌─────────────┐
                    │  ImprovMX  │
                    └──────┬──────┘
                           │ HTTPS Webhook
                           ▼
              ┌──────────────────────────┐
              │       Caddy            │
              │  (SSL/TLS + Proxy)   │
              └───────────┬────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                             │
          ▼                             ▼
┌─────────────────┐         ┌─────────────────┐
│  Webhook API   │         │  Webmail App   │
│  (Puerto 42010)│         │  (Puerto 26000)│
│  Flask + Gunicorn│       │  Flask + Gunicorn│
└────────┬────────┘         └────────┬────────┘
         │                          │
         └──────────┬───────────────┘
                    ▼
         ┌────────────────────────┐
         │     MongoDB         │
         │  (Base de datos)    │
         └────────────────────┘
```

## 🚀 Funcionalidades Futuras

### Planeado para Desarrollo Futuro

- [ ] Envío de correos (composición)
- [ ] Responder y reenviar correos
- [ ] Gestión de carpetas personalizadas
- [ ] Etiquetas y categorización
- [ ] Filtros avanzados
- [ ] Descarga de adjuntos
- [ ] Visualización de cabeceras de correo
- [ ] Exportación de correos
- [ ] Notificaciones en tiempo real
- [ ] Modo oscuro
- [ ] Preferencias de usuario
- [ ] Búsqueda avanzada con operadores
- [ ] Vista de conversación
- [ ] Marcar como spam
- [ ] Gestión de contactos

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request para sugerencias.

## 📞 Soporte

Si encuentras algún problema o tienes preguntas, por favor abre un issue en el repositorio.

## 📚 Documentación Relacionada

- [README principal del proyecto](../README.md)
- [Documentación de Flask](https://flask.palletsprojects.com/)
- [Documentación de Bootstrap 5](https://getbootstrap.com/docs/5.3/)
- [Documentación de Gunicorn](https://docs.gunicorn.org/)