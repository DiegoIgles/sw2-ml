# 🧪 Guía Completa para Pruebas Locales del API Gateway

## 📌 Contexto del Proyecto

Este proyecto es un **API Gateway con GraphQL** que actúa como punto de entrada único para:
- ✅ **Microservicio de Expedientes** (NestJS + PostgreSQL) - Puerto 3000
- ✅ **Microservicio de Documentos** (Go + MongoDB) - Puerto 8081
- ✅ **API Gateway** (FastAPI + GraphQL) - Puerto 8000

El Gateway convierte las APIs REST de los microservicios en una única API GraphQL unificada para que el frontend consuma todo desde un solo endpoint.

---

## 🎯 Objetivo de esta Guía

Esta guía te permitirá:
1. Entender cómo levantar localmente el Gateway con Docker
2. Probar todas las funcionalidades con ejemplos reales
3. Verificar la integración con los microservicios de Expedientes y Documentos
4. Solucionar problemas comunes que puedan surgir

---

## 🧪 Pruebas locales del microservicio ML (`sw2-ml`)

Si estás aquí para probar el microservicio ML que acompaña al Gateway (repo `sw2-ml`), sigue esta sección.

El servicio ML expone endpoints de FastAPI en el puerto 8010, y requiere poder alcanzar dos upstreams:
- Expedientes (puerto 3000) — endpoint esperado: `/plazos`
- Documentos  (puerto 8081) — endpoint esperado: `/admin/documentos`

Hay dos formas de ejecutar el ML localmente:

### Opción A — Ejecutar `sw2-ml` en Docker (recomendado con Gateway en host)

1) Asegúrate de que los microservicios Expedientes y Documentos están corriendo en tu máquina (host) o en contenedores accesibles.

2) Ajusta `docker-compose.local.yml` (ya incluido) para usar `host.docker.internal` si los upstreams están en el host. Ejemplo mínimo:

```yaml
services:
  sw2-ml:
    build: .
    image: sw2-ml:local
    container_name: sw2-ml-local
    ports:
      - "8010:8010"
    environment:
      - PLAZOS_ENDPOINT=http://host.docker.internal:3000/plazos
      - DOCS_ENDPOINT=http://host.docker.internal:8081/admin/documentos
      - PORT=8010
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

3) Levanta el servicio:

```powershell
docker-compose -f docker-compose.local.yml up --build -d
```

4) Verifica:

```powershell
curl.exe http://localhost:8010/health
curl.exe http://localhost:8010/debug/upstreams_status
```

Si `/debug/upstreams_status` devuelve `ok: true` para ambos upstreams, el ML puede comunicarse correctamente.

### Opción B — Ejecutar `sw2-ml` localmente con uvicorn (sin Docker)

1) Crea un `.env` en la raíz del repo (opcional):

```
PLAZOS_ENDPOINT=http://localhost:3000/plazos
DOCS_ENDPOINT=http://localhost:8081/admin/documentos
PORT=8010
```

2) Instala dependencias y activa un virtualenv:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3) Corre la app:

```powershell
uvicorn app.main:app --reload --port 8010
```

4) Verifica salud y upstreams:

```powershell
Invoke-RestMethod http://localhost:8010/health -UseBasicParsing
Invoke-RestMethod http://localhost:8010/debug/upstreams_status -UseBasicParsing
```

### Diagnóstico rápido (si aparece `TypeError: 'NoneType' object is not iterable`)

- Significado: `fetch_docs()` o `fetch_plazos()` devolvieron `None` o un formato inesperado.
- Acciones:
  - Asegúrate de que las URLs en `PLAZOS_ENDPOINT` y `DOCS_ENDPOINT` incluyen las rutas completas (`/plazos` y `/admin/documentos`).
  - Desde host prueba: `curl.exe http://localhost:3000/plazos` y `curl.exe http://localhost:8081/admin/documentos`.
  - Desde el contenedor prueba la conectividad (ejemplo):

```powershell
docker exec -it sw2-ml-local python -c "import requests; print(requests.get('http://host.docker.internal:3000/plazos', timeout=3).status_code)"
```

### Notas finales

- `app/clients.py` ya incluye manejo defensivo: si un upstream falla, la función devolverá estructuras vacías en lugar de `None` para evitar errores de iteración.
- Para pruebas reproducibles, considera levantar también mocks (http-echo) o incluir los microservicios en el mismo `docker-compose` si prefieres no depender del host.

-----


## 📋 Prerequisitos

### 1. Software Instalado
- ✅ **Docker Desktop** corriendo (Windows/Mac/Linux)
- ✅ **Git** (para clonar repos si es necesario)
- ✅ **curl** o **Postman** para hacer pruebas (curl viene con Windows 10+)

### 2. Microservicios Backend

**IMPORTANTE**: El Gateway depende de los microservicios. Necesitas tenerlos corriendo primero.

#### A) Microservicio de Expedientes (NestJS)
- **Puerto**: 3000
- **Stack**: NestJS + TypeORM + PostgreSQL
- **Funcionalidad**: Gestión de clientes, expedientes, notas, plazos, autenticación
- **Health check**: `http://localhost:3000/health/live`

**Cómo levantarlo**:
```powershell
# Si tienes el repo del microservicio en otra carpeta
cd ruta\al\microservicio-expedientes
npm install
npm run start:dev
# O si tiene Docker:
docker-compose up -d
```

#### B) Microservicio de Documentos (Go) - OPCIONAL
- **Puerto**: 8081
- **Stack**: Go + MongoDB + GridFS
- **Funcionalidad**: Upload, download y gestión de documentos PDF
- **Health check**: `http://localhost:8081/health`

**Cómo levantarlo**:
```powershell
# Si tienes el repo del microservicio de documentos
cd ruta\al\microservicio-documentos
# Levantar MongoDB primero
docker-compose up -d mongodb
# Luego el servicio Go
go run main.go
# O si tiene Docker:
docker-compose up -d
```

**Nota**: Si NO tienes el microservicio de Documentos, el Gateway funcionará igual (solo ignora las queries/mutations de documentos).

---

## 🚀 Paso 1: Levantar el API Gateway

### Verificar Prerequisitos

```powershell
# 1. Verificar que Docker Desktop esté corriendo
docker version

# 2. Verificar que el microservicio de expedientes esté corriendo
curl http://localhost:3000/health/live
# Debe responder: {"status":"ok"} o similar

# 3. (Opcional) Verificar microservicio de documentos
curl http://localhost:8081/health
```

### Configurar Variables de Entorno

El Gateway ya viene con un `.env` preconfigurado para Docker, pero verifica que tenga estos valores:

```env
# Microservicios (usar host.docker.internal cuando el Gateway corre en Docker)
EXPEDIENTES_URL=http://host.docker.internal:3000
AUTH_URL=http://host.docker.internal:3000
DOCUMENTOS_URL=http://host.docker.internal:8081

# JWT - DEBE SER IDÉNTICO al del microservicio de expedientes
JWT_SECRET=tu_secreto_debe_coincidir_con_el_backend
JWT_ALGORITHM=HS256

# Timeouts y reintentos
TIMEOUT_MS=30000
RETRIES=3

# CORS - Agrega las URLs de tu frontend si usas uno
CORS_ORIGINS=http://localhost:3001,http://localhost:8081

# Server
PORT=8000
HOST=0.0.0.0
```

**⚠️ CRÍTICO**: El `JWT_SECRET` debe ser **exactamente igual** al que usa el microservicio de expedientes. Si no coincide, la autenticación fallará.

### Iniciar el Gateway

```powershell
# Desde la raíz del repositorio sw2-apiGateway

# Opción 1: Usar el script de inicio rápido (recomendado)
.\inicio-rapido.cmd

# Opción 2: Comando manual
docker-compose up --build -d

# Ver logs (útil para debug)
docker-compose logs -f
```

### Verificar que Está Corriendo

```powershell
# 1. Health check básico
curl http://localhost:8000/health/live

# Debe responder algo como:
# {
#   "status": "alive",
#   "timestamp": "2025-11-11T10:30:00.000Z",
#   "microservices": {
#     "expedientes": "ok"
#   }
# }

# 2. Abrir GraphQL Playground en el navegador
start http://localhost:8000/graphql
```

Si ves la interfaz de GraphQL Playground, ¡todo está funcionando! ✅

---

## 🧪 Paso 2: Probar Autenticación

Todos los ejemplos se ejecutan en **GraphQL Playground** (`http://localhost:8000/graphql`).

### 2.1 Registrar un Usuario Interno

Copia y pega en el editor de GraphQL Playground:

```graphql
mutation {
  register(input: {
    email: "admin@test.com"
    password: "admin123"
    rol: "ADMIN"
  }) {
    accessToken
    usuario {
      idUsuario
      email
      rol
    }
  }
}
```

Presiona el botón **Play** (▶️).

**Respuesta esperada**:
```json
{
  "data": {
    "register": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImVtYWlsIjoiYWRtaW5AdGVzdC5jb20iLCJyb2wiOiJBRE1JTiIsImlhdCI6MTczMTMzNjAwMCwiZXhwIjoxNzMxNDIyNDAwfQ.xyz...",
      "usuario": {
        "idUsuario": 1,
        "email": "admin@test.com",
        "rol": "ADMIN"
      }
    }
  }
}
```

**✅ Guarda el `accessToken`** — lo necesitarás para las siguientes pruebas.

### 2.2 Login

Si ya tienes un usuario registrado:

```graphql
mutation {
  login(input: {
    email: "admin@test.com"
    password: "admin123"
  }) {
    accessToken
    usuario {
      idUsuario
      email
      rol
    }
  }
}
```

### 2.3 Configurar Header de Autorización

Para las siguientes queries, necesitas agregar el token en los headers HTTP:

1. En GraphQL Playground, busca la sección **HTTP HEADERS** (abajo a la izquierda)
2. Agrega:

```json
{
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImVtYWlsIjoiYWRtaW5AdGVzdC5jb20iLCJyb2wiOiJBRE1JTiIsImlhdCI6MTczMTMzNjAwMCwiZXhwIjoxNzMxNDIyNDAwfQ.xyz..."
}
```

(Usa tu token real, no copies este ejemplo textual).

---

## 🧪 Paso 3: Probar CRUD de Clientes

### 3.1 Crear un Cliente

```graphql
mutation {
  createCliente(input: {
    nombreCompleto: "Juan Pérez Mamani"
    contactoEmail: "juan.perez@example.com"
    contactoTel: "71234567"
    direccion: "Av. 6 de Agosto #123, La Paz"
  }) {
    idCliente
    nombreCompleto
    contactoEmail
    contactoTel
    fechaRegistro
  }
}
```

**Respuesta esperada**:
```json
{
  "data": {
    "createCliente": {
      "idCliente": 1,
      "nombreCompleto": "Juan Pérez Mamani",
      "contactoEmail": "juan.perez@example.com",
      "contactoTel": "71234567",
      "fechaRegistro": "2025-11-11T10:35:00.000Z"
    }
  }
}
```

### 3.2 Listar Clientes

```graphql
query {
  clientes(limit: 10, offset: 0) {
    idCliente
    nombreCompleto
    contactoEmail
    contactoTel
    fechaRegistro
  }
}
```

### 3.3 Obtener un Cliente por ID

```graphql
query {
  cliente(id: 1) {
    idCliente
    nombreCompleto
    contactoEmail
    contactoTel
    direccion
    fechaRegistro
  }
}
```

---

## 🧪 Paso 4: Probar CRUD de Expedientes

### 4.1 Crear un Expediente

```graphql
mutation {
  createExpediente(input: {
    idCliente: 1
    titulo: "Caso de Divorcio"
    descripcion: "Proceso de divorcio amistoso entre las partes"
    estado: ABIERTO
  }) {
    idExpediente
    titulo
    descripcion
    estado
    fechaInicio
    idCliente
  }
}
```

### 4.2 Listar Expedientes con Filtros

```graphql
query {
  expedientes(
    limit: 20
    offset: 0
    estado: ABIERTO
    idCliente: 1
  ) {
    idExpediente
    titulo
    descripcion
    estado
    fechaInicio
    fechaCierre
  }
}
```

### 4.3 Actualizar un Expediente

```graphql
mutation {
  updateExpediente(id: 1, input: {
    estado: EN_PROCESO
    descripcion: "Proceso en curso - pendiente de documentación"
  }) {
    idExpediente
    titulo
    estado
    descripcion
    fechaActualizacion
  }
}
```

### 4.4 Cerrar un Expediente

```graphql
mutation {
  updateExpediente(id: 1, input: {
    estado: CERRADO
  }) {
    idExpediente
    estado
    fechaCierre
  }
}
```

---

## 🧪 Paso 5: Probar Notas

### 5.1 Crear una Nota

```graphql
mutation {
  createNota(input: {
    idExpediente: 1
    contenido: "Primera reunión con el cliente realizada exitosamente. Se acordaron los términos del proceso."
    tipo: "reunion"
  }) {
    idNota
    contenido
    tipo
    fechaCreacion
    idExpediente
  }
}
```

### 5.2 Listar Notas de un Expediente

```graphql
query {
  notasExpediente(idExpediente: 1) {
    idNota
    contenido
    tipo
    fechaCreacion
  }
}
```

### 5.3 Actualizar una Nota

```graphql
mutation {
  updateNota(id: 1, input: {
    contenido: "Reunión actualizada - se acordaron nuevos términos según acta adjunta"
    tipo: "acuerdo"
  }) {
    idNota
    contenido
    tipo
    fechaActualizacion
  }
}
```

---

## 🧪 Paso 6: Probar Plazos

### 6.1 Crear un Plazo

```graphql
mutation {
  createPlazo(input: {
    idExpediente: 1
    descripcion: "Presentar documentación ante el juzgado de familia"
    fechaVencimiento: "2025-12-31"
  }) {
    idPlazo
    descripcion
    fechaVencimiento
    cumplido
    idExpediente
  }
}
```

### 6.2 Listar Plazos de un Expediente

```graphql
query {
  plazosExpediente(idExpediente: 1) {
    idPlazo
    descripcion
    fechaVencimiento
    cumplido
    fechaCumplimiento
    fechaCreacion
  }
}
```

### 6.3 Marcar Plazo como Cumplido

```graphql
mutation {
  marcarPlazoCumplido(idPlazo: 1) {
    idPlazo
    cumplido
    fechaCumplimiento
  }
}
```

### 6.4 Listar Plazos Vencidos

```graphql
query {
  plazosVencidos {
    idPlazo
    descripcion
    fechaVencimiento
    cumplido
    idExpediente
  }
}
```

---

## 🧪 Paso 7: Probar Documentos (Opcional)

**Prerequisito**: El microservicio de Documentos debe estar corriendo en puerto 8081.

### 7.1 Listar Documentos de un Expediente

```graphql
query {
  documentosExpediente(idExpediente: 1) {
    id
    docId
    filename
    size
    idCliente
    idExpediente
    createdAt
  }
}
```

### 7.2 Subir un Documento

**IMPORTANTE**: El upload NO se hace por GraphQL, sino directamente a la API REST del microservicio de Documentos.

Desde PowerShell:
```powershell
# Crear un archivo de prueba
echo "Contenido de prueba" > documento-test.txt

# Subir usando curl (reemplaza el token con tu accessToken real)
curl.exe -X POST http://localhost:8081/documentos `
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR..." `
  -F "file=@documento-test.txt" `
  -F "id_expediente=1"
```

Respuesta esperada:
```json
{
  "doc_id": "507f1f77bcf86cd799439011",
  "filename": "documento-test.txt",
  "size": 21,
  "id_expediente": 1
}
```

### 7.3 Eliminar un Documento

```graphql
mutation {
  eliminarDocumento(docId: "507f1f77bcf86cd799439011") {
    success
    message
  }
}
```

### 7.4 Descargar un Documento

Abrir en el navegador o usar curl:
```powershell
curl.exe http://localhost:8081/documentos/507f1f77bcf86cd799439011 --output descargado.txt
```

---

## 🔍 Paso 8: Pruebas Avanzadas

### 8.1 Query Completa con Múltiples Recursos

```graphql
query ExpedienteCompleto {
  expediente(id: 1) {
    idExpediente
    titulo
    descripcion
    estado
    fechaInicio
  }
  
  cliente(id: 1) {
    idCliente
    nombreCompleto
    contactoEmail
  }
  
  notasExpediente(idExpediente: 1) {
    idNota
    contenido
    tipo
    fechaCreacion
  }
  
  plazosExpediente(idExpediente: 1) {
    idPlazo
    descripcion
    fechaVencimiento
    cumplido
  }
  
  documentosExpediente(idExpediente: 1) {
    docId
    filename
    size
    createdAt
  }
}
```

Esta query obtiene en una sola petición:
- Datos del expediente
- Datos del cliente
- Todas las notas
- Todos los plazos
- Todos los documentos

### 8.2 Búsqueda por Texto (Text Search)

```graphql
query {
  expedientes(q: "divorcio", limit: 10) {
    idExpediente
    titulo
    descripcion
    estado
  }
}
```

---

## 🐛 Troubleshooting

### Problema 1: "Connection refused" al microservicio

**Síntoma**: El Gateway responde con error 500 y logs muestran "Connection refused" a localhost:3000

**Causa**: El microservicio de expedientes no está corriendo.

**Solución**:
```powershell
# Verificar si el microservicio está corriendo
curl http://localhost:3000/health/live

# Si no responde, levantarlo primero
cd ruta\al\microservicio-expedientes
npm run start:dev
# o docker-compose up -d
```

### Problema 2: Error 401 Unauthorized

**Síntoma**: Queries protegidas fallan con "Unauthorized"

**Causas posibles**:
1. No incluiste el token en los headers
2. Token expirado
3. `JWT_SECRET` no coincide entre Gateway y microservicio

**Solución**:
```powershell
# 1. Verificar que agregaste el header en GraphQL Playground
# HTTP HEADERS (abajo izquierda):
# {
#   "Authorization": "Bearer tu_token_aqui"
# }

# 2. Hacer login nuevamente para obtener un token fresco
# (ejecutar mutation login)

# 3. Verificar que JWT_SECRET sea idéntico en ambos servicios
# Gateway: .env → JWT_SECRET=...
# Backend: .env → JWT_SECRET=... (mismo valor)
```

### Problema 3: GraphQL Playground no carga

**Síntoma**: `http://localhost:8000/graphql` no responde o da error de conexión

**Solución**:
```powershell
# 1. Verificar que el contenedor esté corriendo
docker ps

# Debe mostrar:
# CONTAINER ID   IMAGE                 PORTS                    NAMES
# abc123def456   api-gateway:latest    0.0.0.0:8000->8000/tcp   sw2-api-gateway

# 2. Ver logs del contenedor
docker-compose logs -f

# 3. Si no aparece, reiniciar
docker-compose down
docker-compose up --build -d
```

### Problema 4: Error 409 Conflict al registrar

**Síntoma**: No puedo registrar un usuario con un email

**Causa**: El email ya está registrado en la base de datos

**Solución**: Usar un email diferente o hacer login con las credenciales existentes

### Problema 5: Cambios en código no se aplican

**Síntoma**: Modifiqué archivos pero el Gateway sigue con el código viejo

**Causa**: Docker usa la imagen cacheada

**Solución**:
```powershell
# Reconstruir la imagen
docker-compose down
docker-compose up --build -d
```

### Problema 6: MongoDB connection error (documentos)

**Síntoma**: Queries de documentos fallan con "connection refused" a MongoDB

**Causa**: MongoDB no está corriendo o el microservicio de Documentos no está configurado

**Solución**:
```powershell
# Si usas el microservicio de documentos, verificar que MongoDB esté corriendo
docker ps | findstr mongo

# Si no aparece, levantarlo
cd ruta\al\microservicio-documentos
docker-compose up -d mongodb

# Esperar ~10 segundos y levantar el servicio Go
go run main.go
```

---

## 📊 Arquitectura de Prueba

```
┌──────────────────────────────────────────────┐
│          TU PC (localhost)                    │
├──────────────────────────────────────────────┤
│                                               │
│  Navegador (GraphQL Playground)              │
│  http://localhost:8000/graphql               │
│          │                                    │
│          ▼                                    │
│  ┌────────────────────────────────────┐     │
│  │  API Gateway (Docker)              │     │
│  │  Puerto: 8000                      │     │
│  │  Container: sw2-api-gateway        │     │
│  └─────────────┬──────────────────────┘     │
│                │                              │
│                │ HTTP via host.docker.internal
│                │                              │
│  ┌─────────────▼──────────────────────┐     │
│  │  Microservicio Expedientes         │     │
│  │  Puerto: 3000                      │     │
│  │  Stack: NestJS + PostgreSQL        │     │
│  └────────────────────────────────────┘     │
│                                               │
│  ┌────────────────────────────────────┐     │
│  │  Microservicio Documentos          │     │
│  │  Puerto: 8081                      │     │
│  │  Stack: Go + MongoDB               │     │
│  └────────────────────────────────────┘     │
│                                               │
└──────────────────────────────────────────────┘
```

---

## ✅ Checklist de Verificación

Antes de decir "todo funciona", verifica que puedas hacer:

- [ ] Health check del Gateway responde OK
- [ ] GraphQL Playground carga correctamente
- [ ] Registrar un usuario interno
- [ ] Hacer login y obtener token
- [ ] Crear un cliente
- [ ] Listar clientes
- [ ] Crear un expediente
- [ ] Actualizar estado de expediente
- [ ] Crear una nota
- [ ] Listar notas de expediente
- [ ] Crear un plazo
- [ ] Marcar plazo como cumplido
- [ ] (Opcional) Subir un documento vía REST
- [ ] (Opcional) Listar documentos de expediente
- [ ] Query compleja con múltiples recursos

---

## 📚 Recursos Adicionales

- **Ejemplos completos**: `docs/examples.graphql`
- **Arquitectura del sistema**: `docs/ARCHITECTURE.md`
- **Instalación paso a paso**: `INSTALL.md`
- **README principal**: `README.md`
- **Frontend integration**: `docs/frontend-integration.js`

---

## 🎓 Tips para el Evaluador / Compañero de Equipo

### Si eres evaluador:
1. Ejecuta `inicio-rapido.cmd` y espera ~30 segundos
2. Abre `http://localhost:8000/graphql`
3. Ejecuta la mutation `register` del Paso 2.1
4. Copia el `accessToken` y agrégalo en HTTP HEADERS
5. Ejecuta las queries de ejemplo de los pasos 3-6
6. Verifica que todo funcione correctamente

### Si eres compañero de equipo:
- Este Gateway **ya está funcionando** — solo necesitas levantarlo con Docker
- Los microservicios de backend (Expedientes y Documentos) **deben estar corriendo primero**
- El Gateway actúa como proxy GraphQL hacia las APIs REST de los microservicios
- **No necesitas modificar nada** — solo seguir los pasos de esta guía para probar
- Si algo no funciona, revisa la sección de Troubleshooting

### Flujo de trabajo típico:
```
1. Levantar microservicios backend (expedientes, documentos)
2. Levantar API Gateway (este proyecto)
3. Abrir GraphQL Playground
4. Registrar/Login para obtener token
5. Configurar header Authorization
6. Ejecutar queries y mutations
```

---

**Última actualización**: Noviembre 2025  
**Autor**: Equipo SW2  
**Versión Gateway**: 1.0.0
