# 🚀 Deploy a DigitalOcean Kubernetes (DOKS)

## ⚡ Quick Start (Redeploy)

### Opción A: Cluster ya existe (solo actualizar código)

Si el cluster sigue corriendo y solo actualizaste el código:

```powershell
# 1. Conectar al cluster existente
doctl kubernetes cluster kubeconfig save expedientes-cluster

# 2. Verificar conexión
kubectl get nodes

# 3. Rebuild y push imagen
docker build -t registry.digitalocean.com/sw2-expedientes/expedientes-service:latest .
docker push registry.digitalocean.com/sw2-expedientes/expedientes-service:latest

# 4. Rolling update
kubectl rollout restart deployment/expedientes-service -n expedientes

# 5. Ver estado
kubectl get pods -n expedientes

# 6. Obtener LoadBalancer IP (será la misma)
kubectl get service expedientes-service -n expedientes
```

### Opción B: Cluster eliminado (recrear desde cero)

Si eliminaste el cluster para ahorrar recursos:

```powershell
# 1. Crear cluster de nuevo (3-5 minutos)
doctl kubernetes cluster create expedientes-cluster `
  --region nyc1 `
  --version 1.32.5-do.5 `
  --node-pool "name=expedientes-pool;size=s-2vcpu-2gb;count=2" `
  --set-current-context

# 2. Verificar nodos
kubectl get nodes

# 3. Crear secret del registry
doctl registry kubernetes-manifest | kubectl apply -f -

# 4. Aplicar manifiestos
kubectl apply -f k8s/

# 5. Esperar que todo esté listo (2-3 minutos)
kubectl get all -n expedientes

# 6. ⚠️ IMPORTANTE: Obtener NUEVA LoadBalancer IP
$NEW_IP = kubectl get service expedientes-service -n expedientes -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo "Nueva IP del LoadBalancer: $NEW_IP"
echo "⚠️ Actualiza tu Gateway con esta nueva IP"
```

**⚠️ IMPORTANTE**: La LoadBalancer IP **cambia cada vez que recreas el cluster**. Debes actualizar tu Gateway con la nueva IP.

---

**Configuración del deployment**:  
- **Registry**: `registry.digitalocean.com/sw2-expedientes` (se mantiene siempre)
- **Cluster**: `expedientes-cluster` (NYC1)
- **Namespace**: `expedientes`
- **LoadBalancer IP anterior**: `129.212.136.101` ⚠️ *Cambiará al recrear*

---

## ✅ Prerequisitos (Full Setup)

1. Cuenta de DigitalOcean creada y verificada
2. `doctl` (DigitalOcean CLI) instalado
3. `kubectl` instalado

## 📦 Paso 1: Instalar doctl (CLI de DigitalOcean)

```powershell
# Opción 1: Con Chocolatey
choco install doctl

# Opción 2: Manual
# Descargar desde: https://github.com/digitalocean/doctl/releases
# Extraer y agregar al PATH
```

## 🔐 Paso 2: Autenticación

```powershell
# 1. Crear Personal Access Token en DigitalOcean
# https://cloud.digitalocean.com/account/api/tokens
# Click "Generate New Token"
# Name: "kubectl-access"
# Scopes: ✓ Read ✓ Write
# Copiar el token

# 2. Autenticar doctl
doctl auth init
# Pegar el token cuando lo pida

# 3. Verificar autenticación
doctl account get
```

## ☸️ Paso 3: Crear Cluster de Kubernetes

```powershell
# Ver regiones disponibles
doctl kubernetes options regions

# Ver tamaños de nodos disponibles
doctl kubernetes options sizes

# Crear cluster (tarda 3-5 minutos) - CONFIGURACIÓN ACTUAL
doctl kubernetes cluster create expedientes-cluster `
  --region nyc1 `
  --version 1.32.5-do.5 `
  --node-pool "name=expedientes-pool;size=s-2vcpu-2gb;count=2" `
  --set-current-context

# Ver clusters
doctl kubernetes cluster list

# Obtener credenciales (automático con --set-current-context, pero por si acaso)
doctl kubernetes cluster kubeconfig save expedientes-cluster

# Verificar conexión
kubectl cluster-info
kubectl get nodes
```

## 🐳 Paso 4: Crear Container Registry

```powershell
# Crear registry (nombre único global) - YA EXISTE: sw2-expedientes
doctl registry create sw2-expedientes

# Ver registry creado
doctl registry get

# Login a Docker (válido por 30 días)
doctl registry login

# Registry actual
echo "Registry: registry.digitalocean.com/sw2-expedientes"
```

**Registry existente**: `registry.digitalocean.com/sw2-expedientes`

## 🏗️ Paso 5: Build y Push de Imagen Docker

```powershell
# Build de imagen con tags (latest + versión)
docker build -t registry.digitalocean.com/sw2-expedientes/expedientes-service:latest `
  -t registry.digitalocean.com/sw2-expedientes/expedientes-service:v1.0.1 .

# Push a DigitalOcean Container Registry
docker push registry.digitalocean.com/sw2-expedientes/expedientes-service:latest
docker push registry.digitalocean.com/sw2-expedientes/expedientes-service:v1.0.1

# Ver imágenes en registry
doctl registry repository list-v2
```

**Última versión pusheada**: `v1.0.1`

## 🔧 Paso 6: Dar permisos al Cluster para acceder al Registry

```powershell
# Crear secret para que Kubernetes pueda acceder al Container Registry
& "$env:LOCALAPPDATA\doctl\doctl.exe" registry kubernetes-manifest | kubectl apply -f -

# Verificar que el secret existe
kubectl get secrets -n expedientes

# El deployment ya está configurado con:
# - image: registry.digitalocean.com/sw2-expedientes/expedientes-service:latest
# - imagePullSecrets: registry-sw2-expedientes
```

**Manifiestos listos en**: `k8s/` (8 archivos)

## 🚀 Paso 7: Deploy a Kubernetes

```powershell
# Aplicar todos los manifiestos
kubectl apply -f k8s/

# Ver progreso
kubectl get all -n expedientes

# Ver eventos
kubectl get events -n expedientes --sort-by='.lastTimestamp'

# Ver logs de PostgreSQL
kubectl logs -f deployment/postgres -n expedientes

# Ver logs del servicio
kubectl logs -f deployment/expedientes-service -n expedientes

# Esperar a que el LoadBalancer obtenga IP (2-3 minutos)
kubectl get service expedientes-service -n expedientes -w
```

## 🌐 Paso 8: Obtener LoadBalancer URL

```powershell
# Obtener IP externa
kubectl get service expedientes-service -n expedientes

# O directamente:
$LOAD_BALANCER_IP = kubectl get service expedientes-service -n expedientes -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo "🌐 URL del servicio: http://$LOAD_BALANCER_IP"
```

**LoadBalancer IP actual**: `129.212.136.101`

### Endpoints disponibles:

```powershell
# Health checks
curl http://129.212.136.101/health/live
curl http://129.212.136.101/health/ready

# Swagger UI
Start-Process "http://129.212.136.101/docs"

# API endpoints
curl http://129.212.136.101/api/expedientes
curl http://129.212.136.101/api/clientes
curl http://129.212.136.101/api/notas
curl http://129.212.136.101/api/plazos
```

## 📊 Comandos Útiles

```powershell
# Ver todos los recursos
kubectl get all -n expedientes

# Ver pods con más detalle
kubectl get pods -n expedientes -o wide

# Describir un pod
kubectl describe pod <pod-name> -n expedientes

# Ver logs
kubectl logs -f deployment/expedientes-service -n expedientes

# Escalar deployment
kubectl scale deployment expedientes-service --replicas=3 -n expedientes

# Actualizar imagen
docker build -t registry.digitalocean.com/$REGISTRY_NAME/expedientes-service:latest .
docker push registry.digitalocean.com/$REGISTRY_NAME/expedientes-service:latest
kubectl rollout restart deployment/expedientes-service -n expedientes

# Ver estado del rollout
kubectl rollout status deployment/expedientes-service -n expedientes

# Ver historial de rollouts
kubectl rollout history deployment/expedientes-service -n expedientes

# Hacer rollback
kubectl rollout undo deployment/expedientes-service -n expedientes
```

## 🗄️ Conectar a PostgreSQL

```powershell
# Port-forward para acceso local
kubectl port-forward -n expedientes service/postgres 5432:5432

# En otra terminal, conectar con psql
psql postgresql://postgres:ExpedientesSecure2025!@localhost:5432/expedientes_db

# O ejecutar dentro del pod
kubectl exec -it deployment/postgres -n expedientes -- psql -U postgres -d expedientes_db
```

## 💰 Costos Estimados (DigitalOcean)

### Configuración Actual (Optimizada)

- **Kubernetes Cluster**: Gratis (solo pagas los nodos)
- **Droplets (2x s-2vcpu-2gb)**: $12/mes cada uno = $24/mes
- **LoadBalancer**: $12/mes
- **Block Storage (10GB)**: $1/mes
- **Container Registry**: Gratis (primeros 500MB)

**Total aproximado**: **~$37/mes**

**Crédito gratis**: $200 por 60 días = **~5.4 meses gratis**

### Costos por hora (para pausar cuando no uses)
- **Nodos**: ~$0.017/hora cada uno = $0.034/hora total
- **LoadBalancer**: ~$0.017/hora
- **Total**: **~$0.051/hora** (~$1.22/día si está corriendo 24/7)

## 🔥 Pausar/Reanudar Cluster (Ahorrar recursos)

### Eliminar cluster (para ahorrar recursos)
```powershell
# ⚠️ IMPORTANTE: Esto BORRA el cluster completamente
# Los manifiestos en k8s/ están guardados para recrearlo después

# Eliminar cluster
doctl kubernetes cluster delete expedientes-cluster --force

# Esto elimina:
# - Nodos (ahorro de $24/mes)
# - LoadBalancer (ahorro de $12/mes)
# - Block Storage (ahorro de $1/mes)

# El Container Registry se mantiene con las imágenes
```

### Recrear cluster desde cero

```powershell
# 1. Crear cluster de nuevo (3-5 minutos)
doctl kubernetes cluster create expedientes-cluster `
  --region nyc1 `
  --version 1.32.5-do.5 `
  --node-pool "name=expedientes-pool;size=s-2vcpu-2gb;count=2" `
  --set-current-context

# 2. Verificar conexión
kubectl get nodes

# 3. Crear secret del registry
doctl registry kubernetes-manifest | kubectl apply -f -

# 4. Aplicar manifiestos
kubectl apply -f k8s/

# 5. Ver progreso (tarda ~2 minutos)
kubectl get all -n expedientes

# 6. ⚠️ CRÍTICO: Obtener NUEVA LoadBalancer IP
$NEW_IP = kubectl get service expedientes-service -n expedientes -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo "========================================="
echo "🚨 NUEVA LoadBalancer IP: $NEW_IP"
echo "========================================="
echo ""
echo "⚠️ ACTUALIZA tu API Gateway con:"
echo "EXPEDIENTES_SERVICE_URL = 'http://$NEW_IP'"
```

### ⚠️ IMPORTANTE: Sobre la LoadBalancer IP

**¿Qué se mantiene al recrear?**
- ✅ Container Registry (imágenes guardadas)
- ✅ Manifiestos k8s/ (en tu repo Git)
- ✅ Código fuente (en tu repo Git)

**¿Qué cambia al recrear?**
- ❌ LoadBalancer IP (se asigna una nueva)
- ❌ Datos de PostgreSQL (si no usas backup externo)
- ❌ Configuración del kubeconfig local

**Después de recrear, SIEMPRE**:
1. Obtén la nueva LoadBalancer IP con: `kubectl get service expedientes-service -n expedientes`
2. Actualiza tu API Gateway con la nueva IP
3. Prueba los endpoints: `http://NUEVA_IP/health/ready`

## 🐛 Troubleshooting

### ImagePullBackOff
```powershell
# Dar permisos al cluster para acceder al registry
doctl registry kubernetes-manifest | kubectl apply -f -

# Verificar secret
kubectl get secrets -n expedientes

# Reintentar pull
kubectl rollout restart deployment/expedientes-service -n expedientes
```

### LoadBalancer en Pending
```powershell
# Verificar eventos
kubectl describe service expedientes-service -n expedientes

# Ver cuota de LoadBalancers
doctl compute load-balancer list
```

### Pod en CrashLoopBackOff
```powershell
# Ver logs
kubectl logs deployment/expedientes-service -n expedientes

# Ver eventos
kubectl describe pod <pod-name> -n expedientes

# Verificar variables de entorno
kubectl exec deployment/expedientes-service -n expedientes -- env | grep DB
```

## 🔗 Conectar con API Gateway

### Obtener la LoadBalancer IP actual

```powershell
# Obtener IP actual
$LOAD_BALANCER_IP = kubectl get service expedientes-service -n expedientes -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo "LoadBalancer IP: $LOAD_BALANCER_IP"
```

### Actualizar API Gateway (FastAPI en AWS)

```python
# En tu Gateway (FastAPI) - archivo .env o config
EXPEDIENTES_SERVICE_URL = "http://LOAD_BALANCER_IP"  # ⚠️ Usar IP actual

# Ejemplo (IP puede ser diferente cada vez que recrees el cluster):
# EXPEDIENTES_SERVICE_URL = "http://143.198.123.45"
```

### Endpoints disponibles:

```bash
# Health checks
GET  http://LOAD_BALANCER_IP/health/live
GET  http://LOAD_BALANCER_IP/health/ready

# Swagger UI
http://LOAD_BALANCER_IP/docs

# API endpoints
GET    http://LOAD_BALANCER_IP/api/expedientes
POST   http://LOAD_BALANCER_IP/api/expedientes
GET    http://LOAD_BALANCER_IP/api/expedientes/:id
PUT    http://LOAD_BALANCER_IP/api/expedientes/:id
DELETE http://LOAD_BALANCER_IP/api/expedientes/:id

GET    http://LOAD_BALANCER_IP/api/clientes
POST   http://LOAD_BALANCER_IP/api/clientes

GET    http://LOAD_BALANCER_IP/api/notas
POST   http://LOAD_BALANCER_IP/api/notas

GET    http://LOAD_BALANCER_IP/api/plazos
POST   http://LOAD_BALANCER_IP/api/plazos
```

**⚠️ CRÍTICO**: Cada vez que elimines y recrees el cluster, la IP cambia. Siempre verifica con:
```powershell
kubectl get service expedientes-service -n expedientes
```

## 🗑️ Eliminar Todo

```powershell
# Eliminar recursos de Kubernetes
kubectl delete namespace expedientes

# Eliminar cluster
doctl kubernetes cluster delete expedientes-cluster

# Eliminar registry
doctl registry delete sw2-expedientes

# Eliminar LoadBalancer (si quedó huérfano)
doctl compute load-balancer list
doctl compute load-balancer delete <lb-id>
```

## 📚 Recursos

- [DigitalOcean Kubernetes Documentation](https://docs.digitalocean.com/products/kubernetes/)
- [doctl CLI Reference](https://docs.digitalocean.com/reference/doctl/)
- [DigitalOcean Container Registry](https://docs.digitalocean.com/products/container-registry/)

---

## 📊 Resumen de Configuración

| Componente | Valor | Persiste al recrear? |
|------------|-------|----------------------|
| **Proveedor** | DigitalOcean | ✅ |
| **Cluster** | `expedientes-cluster` (NYC1) | ✅ (mismo nombre) |
| **Nodos** | 2 × s-2vcpu-2gb (2 vCPUs, 2GB RAM) | ✅ (misma config) |
| **Kubernetes** | v1.32.5-do.5 | ⚠️ (puede actualizarse) |
| **Registry** | `registry.digitalocean.com/sw2-expedientes` | ✅ **Se mantiene** |
| **Namespace** | `expedientes` | ✅ (en manifiestos) |
| **LoadBalancer IP** | ⚠️ **CAMBIA** cada vez | ❌ **Nueva IP** |
| **Costo mensual** | ~$37/mes ($200 crédito = ~5.4 meses) | ✅ |
| **Última versión** | v1.0.1 | ✅ (en registry) |

---

### ⚠️ Al recrear el cluster:
- ✅ **Container Registry**: Imágenes guardadas (`v1.0.1`, `latest`)
- ✅ **Código fuente**: En Git (manifiestos k8s/)
- ✅ **Configuración**: Manifiestos listos para aplicar
- ❌ **LoadBalancer IP**: **Se asigna una nueva IP diferente**
- ❌ **Datos PostgreSQL**: Se pierden (crear backup si necesitas persistencia)

**Comando para obtener nueva IP**:
```powershell
kubectl get service expedientes-service -n expedientes -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

**Deployment Date**: Noviembre 10, 2025  
**Status**: ✅ Listo para pausar/recrear cuando necesites  
**Tiempo de setup**: 
- Primera vez: 15-20 minutos
- Redeploy (cluster existe): 2-3 minutos  
- Recrear (cluster eliminado): 5-7 minutos
