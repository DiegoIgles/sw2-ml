# 🚀 Deployment GKE (Google Kubernetes Engine)

## Deployment Completo con Kubectl

### Cluster Creado
- **Nombre**: sw2-ml-cluster
- **Tipo**: Autopilot (managed)
- **Región**: us-central1
- **Réplicas**: 4 pods (distribuidos automáticamente)

---

## Comandos de Deployment

### 1. Conectar kubectl al Cluster

```powershell
# Recargar PATH si es necesario
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Obtener credenciales del cluster
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" container clusters get-credentials sw2-ml-cluster --region us-central1

# Verificar conexión
kubectl cluster-info
kubectl get nodes
```

### 2. Aplicar Manifiestos de Kubernetes

```powershell
# Aplicar todos los manifiestos
kubectl apply -f k8s-gke/

# Ver progreso
kubectl get all -n sw2-ml

# Ver pods (debe mostrar 4 réplicas)
kubectl get pods -n sw2-ml -o wide
```

### 3. Obtener IP Externa del LoadBalancer

```powershell
# Esperar a que se asigne IP (tarda ~2-3 minutos)
kubectl get service ml-service -n sw2-ml -w

# O directamente:
kubectl get service ml-service -n sw2-ml -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 4. Verificar Servicio

```powershell
# Obtener IP
$IP = kubectl get service ml-service -n sw2-ml -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Probar endpoints
curl "http://$IP/health"
curl "http://$IP/health/live"
curl "http://$IP/docs"
```

---

## Comandos Útiles con Kubectl

### Ver Estado de Pods

```powershell
# Listar todos los pods
kubectl get pods -n sw2-ml

# Detalle de un pod específico
kubectl describe pod <pod-name> -n sw2-ml

# Ver logs de un pod
kubectl logs <pod-name> -n sw2-ml

# Ver logs en tiempo real
kubectl logs -f deployment/ml-service -n sw2-ml
```

### Escalar Réplicas

```powershell
# Aumentar a 6 réplicas
kubectl scale deployment ml-service --replicas=6 -n sw2-ml

# Volver a 4 réplicas
kubectl scale deployment ml-service --replicas=4 -n sw2-ml
```

### Actualizar Imagen

```powershell
# Build nueva imagen
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" builds submit --tag us-central1-docker.pkg.dev/sw2-ml-service/sw2-ml-repo/ml-service:latest

# Rolling update automático
kubectl rollout restart deployment/ml-service -n sw2-ml

# Ver progreso del rollout
kubectl rollout status deployment/ml-service -n sw2-ml
```

### Actualizar Variables de Entorno

```powershell
# Editar ConfigMap
kubectl edit configmap ml-service-config -n sw2-ml

# O desde archivo
# (edita k8s-gke/01-configmap.yaml y luego:)
kubectl apply -f k8s-gke/01-configmap.yaml

# Reiniciar pods para aplicar cambios
kubectl rollout restart deployment/ml-service -n sw2-ml
```

### 🔧 IMPORTANTE: Actualizar IPs de Otros Microservicios

**DESPUÉS de desplegar Expedientes (DigitalOcean) y Documentos (Azure):**

#### 1️⃣ Obtener IPs de los otros servicios

```powershell
# En el proyecto de Expedientes (DigitalOcean)
kubectl get service expedientes-service -n expedientes -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# En el proyecto de Documentos (Azure)
kubectl get service documentos-service -n documentos -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

#### 2️⃣ Editar el ConfigMap con las IPs reales

Abre `k8s-gke/01-configmap.yaml` y reemplaza las IPs de prueba:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ml-service-config
  namespace: sw2-ml
data:
  PORT: "8010"
  # ⚠️ ACTUALIZAR CON LAS IPs REALES:
  PLAZOS_ENDPOINT: "http://<IP-DIGITALOCEAN>/plazos"
  DOCS_ENDPOINT: "http://<IP-AZURE>/admin/documentos"
```

**Ejemplo con IPs reales:**
```yaml
  PLAZOS_ENDPOINT: "http://142.93.45.123/plazos"
  DOCS_ENDPOINT: "http://20.185.10.98/admin/documentos"
```

#### 3️⃣ Aplicar el cambio al cluster

```powershell
# Configurar PATH y autenticación (una vez por sesión)
$env:Path += ";C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
$env:USE_GKE_GCLOUD_AUTH_PLUGIN = "True"

# Aplicar ConfigMap actualizado
kubectl apply -f k8s-gke/01-configmap.yaml

# Reiniciar los 4 pods para que carguen las nuevas IPs
kubectl rollout restart deployment/ml-service -n sw2-ml

# Verificar que se reiniciaron correctamente
kubectl get pods -n sw2-ml -w
```

#### 4️⃣ Verificar las nuevas variables

```powershell
# Ver el ConfigMap actualizado
kubectl describe configmap ml-service-config -n sw2-ml

# Ver variables en un pod (para confirmar)
kubectl exec -it <pod-name> -n sw2-ml -- env | grep ENDPOINT
```

#### 5️⃣ Probar endpoints que usan los servicios externos

```powershell
# Obtener IP del ML Service
$IP = kubectl get service ml-service -n sw2-ml -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Probar endpoints que dependen de los otros servicios
curl "http://$IP/docs-analytics/summary"
curl "http://$IP/supervisado/classify"
```

---

**⏱️ Tiempo del proceso**: ~1-2 minutos (apply + restart + health checks)

### Ver Eventos

```powershell
# Ver eventos del namespace
kubectl get events -n sw2-ml --sort-by='.lastTimestamp'

# Ver eventos de un pod específico
kubectl describe pod <pod-name> -n sw2-ml
```

---

## Demostrar Distribución Multi-Cloud

### Ver Pods en Diferentes Nodos

```powershell
# Ver pods con sus nodos
kubectl get pods -n sw2-ml -o wide

# Mostrar tabla formateada
kubectl get pods -n sw2-ml -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,IP:.status.podIP
```

**Output esperado** (4 pods distribuidos):
```
NAME                          STATUS    NODE                                      IP
ml-service-xxxxx-aaaaa        Running   gk3-sw2-ml-cluster-pool-1-xxxxxxxx       10.x.x.1
ml-service-xxxxx-bbbbb        Running   gk3-sw2-ml-cluster-pool-1-yyyyyyyy       10.x.x.2
ml-service-xxxxx-ccccc        Running   gk3-sw2-ml-cluster-pool-1-zzzzzzzz       10.x.x.3
ml-service-xxxxx-ddddd        Running   gk3-sw2-ml-cluster-pool-1-wwwwwwww       10.x.x.4
```

### Ver Cluster Info

```powershell
# Info general del cluster
kubectl cluster-info

# Ver todos los nodos
kubectl get nodes

# Detalle de nodos
kubectl get nodes -o wide
```

---

## Costos (2 Días de Uso)

### Breakdown

| Recurso | Configuración | Costo/día | Total 2 días |
|---------|---------------|-----------|--------------|
| **GKE Autopilot** | 4 pods × 0.5 vCPU, 512Mi | $2-3 | $4-6 |
| **LoadBalancer** | IP externa | $0.60 | $1.20 |
| **Networking** | Egress <1GB | $0.10 | $0.20 |
| **Container Registry** | 500MB | $0.10 | $0.10 |
| **TOTAL** | | **$2.80-3.70/día** | **~$6-8 (2 días)** |

### Después de Defender (Eliminar Todo)

```powershell
# Eliminar cluster completo (libera TODO)
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" container clusters delete sw2-ml-cluster --region us-central1 --quiet

# Verificar eliminación
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" container clusters list
```

**Costo después de eliminar**: $0/día (solo registry: $0.10/mes)

---

## Troubleshooting

### Pods no inician (ImagePullBackOff)

```powershell
# Ver error detallado
kubectl describe pod <pod-name> -n sw2-ml

# Verificar que la imagen existe
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" artifacts docker images list us-central1-docker.pkg.dev/sw2-ml-service/sw2-ml-repo/ml-service
```

### LoadBalancer en Pending

```powershell
# Ver eventos del servicio
kubectl describe service ml-service -n sw2-ml

# Esperar 2-3 minutos (GKE asigna IP externa)
kubectl get service ml-service -n sw2-ml -w
```

### Pod en CrashLoopBackOff

```powershell
# Ver logs del pod
kubectl logs <pod-name> -n sw2-ml

# Ver logs anteriores (si el pod se reinició)
kubectl logs <pod-name> -n sw2-ml --previous
```

---

## Arquitectura Multi-Cloud Completa

```
┌─────────────────────────────────────────────┐
│         API Gateway (AWS/Local)             │
└────────────┬────────────────────────────────┘
             │
             │ HTTP/REST
             │
     ┌───────┴────────┬──────────────┬─────────────────┐
     │                │              │                 │
     ▼                ▼              ▼                 ▼
┌──────────┐  ┌──────────────┐  ┌─────────┐  ┌──────────────┐
│Expedientes│  │ Documentos   │  │ML Service│  │Otros...      │
│DigitalOcean  │ Azure AKS    │  │Google GKE│  │              │
│DOKS       │  │K8s           │  │K8s       │  │              │
│2 pods     │  │2 pods        │  │4 pods    │  │              │
│IP: x.x.x.x│  │IP: y.y.y.y   │  │IP: z.z.z.z│ │              │
└──────────┘  └──────────────┘  └─────────┘  └──────────────┘

Todos administrados con kubectl ✅
```

---

## URLs Importantes

- **Google Cloud Console**: https://console.cloud.google.com/kubernetes/list
- **Ver Logs en Consola**: https://console.cloud.google.com/logs/query
- **Ver Costos**: https://console.cloud.google.com/billing

---

**Fecha de creación**: 11 nov 2025  
**Proyecto**: sw2-ml-service  
**Cluster**: sw2-ml-cluster  
**Región**: us-central1  
**Réplicas**: 4 pods
