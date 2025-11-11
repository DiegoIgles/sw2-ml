# 📄 Microservicio de Documentos - Azure AKS Deployment

## 🎯 Objetivo
Desplegar el microservicio de Documentos (Go + MongoDB + GridFS) en **Azure Kubernetes Service (AKS)** con gestión completa del ciclo de vida del cluster.

## 🏗️ Arquitectura

```
API Gateway (AWS EKS)
    ↓ HTTP + JWT Auth
Documentos Service (Azure AKS) - LoadBalancer: 128.203.103.88
    ↓
MongoDB 6 (StatefulSet en K8s) + GridFS
    ↓
Azure Managed Disk (PVC 10GB)
```

**IMPORTANTE**: Este microservicio está en Azure para cumplir el requisito académico de distribución multi-cloud:
- API Gateway: AWS EKS
- Documentos: Azure AKS ✅
- Expedientes: Otro proveedor

## 🌐 URLs del Servicio Desplegado

- **Health Check**: `http://128.203.103.88/health`
- **Swagger UI**: `http://128.203.103.88/docs`
- **OpenAPI Spec**: `http://128.203.103.88/openapi.json`
- **Base URL**: `http://128.203.103.88`

## 📋 Prerequisitos

### 1. Cuenta de Azure con Créditos
- **Estudiantes**: Activar [Azure for Students](https://azure.microsoft.com/free/students/) con GitHub Student Pack
  - $100 USD de crédito
  - Válido por 12 meses
  - No requiere tarjeta de crédito
- **Alternativa**: [Cuenta gratuita de Azure](https://azure.microsoft.com/free/) ($200 por 30 días)

### 2. Herramientas Locales
```powershell
# Instalar Azure CLI
winget install Microsoft.AzureCLI

# Verificar instalación (requiere reiniciar terminal o PC)
az --version

# Instalar kubectl
az aks install-cli

# Verificar kubectl
kubectl version --client

# Instalar Docker Desktop (para construir imágenes)
winget install Docker.DockerDesktop
```

### 3. Autenticación en Azure
```powershell
# Login interactivo
az login

# Verificar suscripción activa y crédito disponible
az account list --output table
az account show

# Establecer suscripción por defecto si tienes varias
az account set --subscription "TU_SUBSCRIPTION_ID"
```

## 🚀 Deployment desde Cero

### Paso 1: Registrar Proveedores de Azure

```powershell
# Registrar proveedores necesarios (solo primera vez)
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.ContainerRegistry

# Verificar registro (debe decir "Registered")
az provider show --namespace Microsoft.ContainerService --query "registrationState"
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState"
```

### Paso 2: Crear Infraestructura Base

```powershell
# 1. Crear Resource Group
az group create `
  --name sw2-documentos-rg `
  --location eastus

# 2. Crear Azure Container Registry (ACR)
az acr create `
  --resource-group sw2-documentos-rg `
  --name sw2registry `
  --sku Basic

# 3. Crear Cluster AKS (tarda 5-10 minutos)
az aks create `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster `
  --node-count 2 `
  --node-vm-size Standard_DC2s_v3 `
  --enable-managed-identity `
  --generate-ssh-keys

# 4. Integrar ACR con AKS (permite pull de imágenes sin auth)
az aks update `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster `
  --attach-acr sw2registry
```

**Nota sobre VM Size**: `Standard_DC2s_v3` es la VM más pequeña disponible en Azure for Students en `eastus` (2 vCPUs, 8GB RAM). Costo: ~$0.096/hora por nodo (~$140/mes si corre 24/7).

### Paso 3: Configurar kubectl

```powershell
# Obtener credenciales del cluster
az aks get-credentials `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster `
  --overwrite-existing

# Verificar conexión
kubectl get nodes
# Debe mostrar 2 nodos en estado "Ready"
```

### Paso 4: Configurar JWT_SECRET

**⚠️ CRÍTICO**: El `JWT_SECRET` debe ser **idéntico** en todos los servicios (Auth, Gateway, Documentos, Expedientes).

Edita `k8s/secrets.yaml` y reemplaza `JWT_SECRET` con el valor correcto:

```yaml
stringData:
  JWT_SECRET: "8f7f1e63e4fe5380429da00fe3e79a8ed00c4be5e4a04f82feaf0597a7bca7cd3471dca9223b2b7cf6a9f7ec2a8cd9d3241145bc91192a068445934ada9b5cb4"
```

También actualiza tu `.env` local con el mismo valor para desarrollo.

### Paso 5: Construir y Subir Imagen Docker

```powershell
# 1. Autenticar con ACR
az acr login --name sw2registry

# 2. Construir imagen
docker build -t sw2registry.azurecr.io/documentos-service:latest .

# 3. Subir imagen a ACR
docker push sw2registry.azurecr.io/documentos-service:latest

# Verificar imagen
az acr repository list --name sw2registry --output table
```

### Paso 6: Desplegar a Kubernetes

```powershell
# Aplicar todos los manifiestos
kubectl apply -f k8s/

# Si da error de namespace, ejecutar dos veces:
kubectl apply -f k8s/

# Ver estado del deployment
kubectl get all -n sw2-documentos

# Esperar a que todos los pods estén Running
kubectl get pods -n sw2-documentos -w
# Presiona Ctrl+C cuando veas 1/1 Running en todos
```

### Paso 7: Obtener IP Externa

```powershell
# Obtener LoadBalancer IP (puede tardar 2-3 minutos)
kubectl get svc -n sw2-documentos

# Deberías ver algo como:
# NAME                 TYPE           EXTERNAL-IP      PORT(S)
# documentos-service   LoadBalancer   128.203.103.88   80:31121/TCP
```

### Paso 8: Probar el Servicio

```powershell
# Obtener IP
$IP = kubectl get svc documentos-service -n sw2-documentos -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Probar health check
curl http://$IP/health
# Debe responder: {"status":"ok"}

# Ver Swagger UI en el navegador
start http://$IP/docs
```

## 🔄 Redeployment (Actualizar después de cambios)

Si ya tienes el cluster corriendo y solo quieres actualizar el código:

```powershell
# 1. Asegurarte de que el cluster esté corriendo
kubectl get nodes
# Si está detenido: az aks start --resource-group sw2-documentos-rg --name sw2-documentos-cluster

# 2. Construir nueva imagen
az acr login --name sw2registry
docker build -t sw2registry.azurecr.io/documentos-service:latest .
docker push sw2registry.azurecr.io/documentos-service:latest

# 3. Forzar actualización del deployment
kubectl rollout restart deployment/documentos-service -n sw2-documentos

# 4. Ver progreso
kubectl rollout status deployment/documentos-service -n sw2-documentos

# 5. Verificar
kubectl get pods -n sw2-documentos
curl http://$(kubectl get svc documentos-service -n sw2-documentos -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/health
```

## � Gestión de Costos: Detener y Reiniciar Cluster

### ⚠️ IMPORTANTE: Ahorro de Créditos

Con Standard_DC2s_v3 (2 nodos), el costo es **~$0.192/hora** (~$140/mes si corre 24/7). Con $100 de crédito, puedes correr el cluster ~520 horas (~21 días continuos).

**Recomendación**: Detén el cluster cuando no lo uses. Solo tardas 5 minutos en reiniciarlo.

### Detener Cluster (Conserva TODO)

```powershell
# Detener cluster (RECOMENDADO)
az aks stop `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster

# Verificar que esté detenido
az aks show `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster `
  --query "powerState.code" `
  --output tsv
# Debe decir: "Stopped"
```

**¿Qué se conserva cuando detienes?**
- ✅ Configuración completa del cluster
- ✅ Todos los deployments y manifiestos
- ✅ Imágenes en el Container Registry
- ✅ Datos en volúmenes persistentes (MongoDB)
- ✅ LoadBalancer IP (se reasigna al reiniciar)

**¿Qué dejas de pagar?**
- ✅ VMs (nodos) - $0/hora
- ❌ Discos persistentes - ~$0.50/mes (inevitable)
- ❌ LoadBalancer IP reservada - ~$0.005/hora

**Costo mientras está detenido**: ~$1-2/mes (solo almacenamiento)

### Reiniciar Cluster (Rápido)

```powershell
# Iniciar cluster
az aks start `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster

# Esto tarda 3-5 minutos

# Verificar que esté corriendo
az aks show `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster `
  --query "powerState.code" `
  --output tsv
# Debe decir: "Running"

# Verificar pods
kubectl get pods -n sw2-documentos

# Obtener nueva IP del LoadBalancer (puede cambiar)
kubectl get svc -n sw2-documentos

# Probar servicio
curl http://$(kubectl get svc documentos-service -n sw2-documentos -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/health
```

### Eliminar TODO (Nuclear - Solo si no volverás a usar)

```powershell
# ⚠️ CUIDADO: Esto ELIMINA TODO permanentemente
az group delete `
  --name sw2-documentos-rg `
  --yes `
  --no-wait

# Esto elimina:
# - Cluster AKS
# - Container Registry
# - Discos persistentes
# - LoadBalancer
# - Todos los datos de MongoDB
```

**Solo usa esto si**:
- Ya defendiste tu proyecto
- No necesitas el servicio nunca más
- Quieres recuperar el 100% del espacio

### Estrategia Recomendada para el Proyecto

1. **Durante desarrollo**: Detén el cluster al final del día
   ```powershell
   az aks stop --resource-group sw2-documentos-rg --name sw2-documentos-cluster
   ```

2. **Día de la defensa**: Inicia 30 minutos antes
   ```powershell
   az aks start --resource-group sw2-documentos-rg --name sw2-documentos-cluster
   kubectl get svc -n sw2-documentos  # Obtener nueva IP
   ```

3. **Después de defender**: Elimina todo
   ```powershell
   az group delete --name sw2-documentos-rg --yes
   ```

### Monitorear Crédito Restante

```powershell
# Ver suscripción y crédito (desde Azure Portal es más claro)
az account show

# O visita: https://www.microsoftazuresponsorships.com/Balance
```

## �📦 Paso 2: Estructura del Proyecto

Tu microservicio de Documentos debe tener esta estructura:

```
documentos-microservice/
├── .github/
│   └── workflows/
│       └── deploy-digitalocean.yml    # CI/CD automatizado
├── k8s/
│   ├── 00-namespace.yaml              # Namespace 'documentos'
│   ├── 01-mongodb-pvc.yaml            # Almacenamiento persistente
│   ├── 02-mongodb-deployment.yaml     # Base de datos MongoDB
│   ├── 03-mongodb-service.yaml        # Servicio interno MongoDB
│   ├── 04-secret.yaml                 # Credenciales (MONGO_URI, etc)
│   ├── 05-configmap.yaml              # Variables de entorno
│   ├── 06-deployment.yaml             # Deployment del servicio Go
│   ├── 07-service.yaml                # LoadBalancer externo
│   └── deploy.sh                      # Script de deployment
├── cmd/
│   └── main.go                        # Entrypoint de la aplicación
├── internal/
│   ├── handlers/                      # HTTP handlers
│   ├── models/                        # Modelos de MongoDB
│   └── repository/                    # Capa de datos
├── Dockerfile                         # Contenedor Go
├── go.mod
├── go.sum
└── README.md
```

## 🐳 Paso 3: Dockerfile para Go

Crea o verifica tu `Dockerfile`:

```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copiar dependencias
COPY go.mod go.sum ./
RUN go mod download

# Copiar código fuente
COPY . .

# Compilar aplicación
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main ./cmd/main.go

# Production stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copiar binario desde build stage
COPY --from=builder /app/main .

# Exponer puerto
EXPOSE 8081

# Comando de inicio
CMD ["./main"]
```

## ☸️ Paso 4: Manifiestos de Kubernetes

### 00-namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: documentos
  labels:
    app: documentos-microservice
    environment: production
```

### 01-mongodb-pvc.yaml
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mongodb-pvc
  namespace: documentos
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: managed-csi  # Azure managed disk
```

### 02-mongodb-deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mongodb
  namespace: documentos
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
      - name: mongodb
        image: mongo:7.0
        ports:
        - containerPort: 27017
        env:
        - name: MONGO_INITDB_ROOT_USERNAME
          valueFrom:
            secretKeyRef:
              name: documentos-secret
              key: mongo-root-username
        - name: MONGO_INITDB_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: documentos-secret
              key: mongo-root-password
        volumeMounts:
        - name: mongodb-storage
          mountPath: /data/db
      volumes:
      - name: mongodb-storage
        persistentVolumeClaim:
          claimName: mongodb-pvc
```

### 03-mongodb-service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mongodb
  namespace: documentos
spec:
  selector:
    app: mongodb
  ports:
    - protocol: TCP
      port: 27017
      targetPort: 27017
  type: ClusterIP
```

### 04-secret.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: documentos-secret
  namespace: documentos
type: Opaque
stringData:
  mongo-root-username: admin
  mongo-root-password: YourSecurePassword123!
  mongo-uri: mongodb://admin:YourSecurePassword123!@mongodb:27017/documentos?authSource=admin
```

**⚠️ IMPORTANTE**: En producción, usa valores seguros y nunca los subas a Git. Usa GitHub Secrets.

### 05-configmap.yaml
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: documentos-config
  namespace: documentos
data:
  PORT: "8081"
  GO_ENV: "production"
  LOG_LEVEL: "info"
```

### 06-deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: documentos-service
  namespace: documentos
  labels:
    app: documentos-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: documentos-service
  template:
    metadata:
      labels:
        app: documentos-service
    spec:
      containers:
      - name: documentos
        image: sw2registry.azurecr.io/documentos-service:latest
        ports:
        - containerPort: 8081
        env:
        - name: PORT
          valueFrom:
            configMapKeyRef:
              name: documentos-config
              key: PORT
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: documentos-secret
              key: mongo-uri
        - name: GO_ENV
          valueFrom:
            configMapKeyRef:
              name: documentos-config
              key: GO_ENV
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 07-service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: documentos-service
  namespace: documentos
spec:
  type: LoadBalancer
  selector:
    app: documentos-service
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8081
```

### deploy.sh
```bash
#!/bin/bash

echo "🚀 Desplegando Microservicio de Documentos en DigitalOcean..."

# Aplicar manifiestos en orden
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-mongodb-pvc.yaml
kubectl apply -f k8s/02-mongodb-deployment.yaml
kubectl apply -f k8s/03-mongodb-service.yaml
kubectl apply -f k8s/04-secret.yaml
kubectl apply -f k8s/05-configmap.yaml
kubectl apply -f k8s/06-deployment.yaml
kubectl apply -f k8s/07-service.yaml

echo "⏳ Esperando a que los pods estén listos..."
kubectl wait --for=condition=ready pod -l app=documentos-service -n documentos --timeout=300s

echo "📊 Estado del deployment:"
kubectl get all -n documentos

echo "🌐 Obteniendo LoadBalancer IP..."
kubectl get service documentos-service -n documentos
```

## 🤖 Paso 5: GitHub Actions para CI/CD

Crea `.github/workflows/deploy-azure.yml`:

```yaml
name: Deploy to Azure AKS

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  REGISTRY: sw2registry.azurecr.io
  IMAGE_NAME: documentos-service
  RESOURCE_GROUP: sw2-documentos-rg
  CLUSTER_NAME: sw2-documentos-cluster

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Log in to Azure Container Registry
        run: |
          az acr login --name sw2registry

      - name: Build Docker image
        run: |
          docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker tag ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Push image to ACR
        run: |
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Get AKS credentials
        run: |
          az aks get-credentials --resource-group ${{ env.RESOURCE_GROUP }} --name ${{ env.CLUSTER_NAME }}

      - name: Update Kubernetes secrets
        run: |
          kubectl create secret generic documentos-secret \
            --from-literal=mongo-root-username=${{ secrets.MONGO_ROOT_USERNAME }} \
            --from-literal=mongo-root-password=${{ secrets.MONGO_ROOT_PASSWORD }} \
            --from-literal=mongo-uri=${{ secrets.MONGO_URI }} \
            --namespace=documentos \
            --dry-run=client -o yaml | kubectl apply -f -

      - name: Deploy to AKS
        run: |
          kubectl apply -f k8s/
          kubectl rollout restart deployment/documentos-service -n documentos
          kubectl rollout status deployment/documentos-service -n documentos

      - name: Verify deployment
        run: |
          kubectl get pods -n documentos
          kubectl get services -n documentos
```

## 🔐 Paso 6: Configurar GitHub Secrets

Ve a tu repositorio en GitHub → Settings → Secrets and variables → Actions → New repository secret

Agrega estos secrets:

1. **AZURE_CREDENTIALS**
   - Necesitas crear un Service Principal en Azure:
   ```powershell
   az ad sp create-for-rbac --name "sw2-documentos-sp" --role contributor `
     --scopes /subscriptions/TU_SUBSCRIPTION_ID/resourceGroups/sw2-documentos-rg `
     --sdk-auth
   ```
   - Copia el JSON completo que devuelve y pégalo como valor del secret

2. **MONGO_ROOT_USERNAME**
   - Valor: `admin` (o el usuario que prefieras)

3. **MONGO_ROOT_PASSWORD**
   - Valor: `TuPasswordSegura123!`

4. **MONGO_URI**
   - Valor: `mongodb://admin:TuPasswordSegura123!@mongodb:27017/documentos?authSource=admin`

### Obtener tu Subscription ID
```powershell
az account show --query id --output tsv
```

## 🏃 Paso 7: Crear Container Registry en Azure

```powershell
# Crear Azure Container Registry (ACR)
az acr create `
  --resource-group sw2-documentos-rg `
  --name sw2registry `
  --sku Basic

# Verificar
az acr list --output table

# Login al registry
az acr login --name sw2registry

# Habilitar integración con AKS (permite pull sin auth)
az aks update `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster `
  --attach-acr sw2registry
```

O desde Azure Portal:
1. Buscar "Container registries"
2. Click "Create"
3. Resource group: `sw2-documentos-rg`
4. Registry name: `sw2registry`
5. SKU: Basic
6. Click "Review + create"

## 🎬 Paso 8: Deployment Manual (Primera vez)

```powershell
# Conectar a tu cluster
az aks get-credentials `
  --resource-group sw2-documentos-rg `
  --name sw2-documentos-cluster

# Verificar conexión
kubectl get nodes

# Aplicar manifiestos
cd k8s
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-mongodb-pvc.yaml
kubectl apply -f 02-mongodb-deployment.yaml
kubectl apply -f 03-mongodb-service.yaml
kubectl apply -f 04-secret.yaml
kubectl apply -f 05-configmap.yaml

# Construir y pushear imagen Docker (primera vez)
az acr login --name sw2registry
docker build -t sw2registry.azurecr.io/documentos-service:latest .
docker push sw2registry.azurecr.io/documentos-service:latest

# Aplicar deployment y service
kubectl apply -f 06-deployment.yaml
kubectl apply -f 07-service.yaml

# Ver estado
kubectl get all -n documentos

# Obtener IP del LoadBalancer (puede tardar 2-3 minutos en asignarse)
kubectl get service documentos-service -n documentos -w
```

## 🔍 Paso 9: Verificación y Testing

```powershell
# Ver logs del servicio
kubectl logs -f deployment/documentos-service -n documentos

# Ver logs de MongoDB
kubectl logs -f deployment/mongodb -n documentos

# Obtener LoadBalancer IP
$LOAD_BALANCER_IP = kubectl get service documentos-service -n documentos -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Probar health endpoint
curl http://$LOAD_BALANCER_IP/health

# Probar API
curl http://$LOAD_BALANCER_IP/api/documentos
```

## 🔗 Paso 10: Conectar con API Gateway

Una vez que tengas el LoadBalancer IP, actualiza el API Gateway (AWS):

1. Edita el ConfigMap del Gateway:
```powershell
kubectl edit configmap gateway-config -n sw2-gateway
```

2. Actualiza la variable `DOCUMENTOS_SERVICE_URL`:
```yaml
data:
  DOCUMENTOS_SERVICE_URL: "http://LOAD_BALANCER_IP"  # IP de DigitalOcean
```

3. Reinicia el Gateway:
```powershell
kubectl rollout restart deployment/api-gateway -n sw2-gateway
```

## 📊 Comandos Útiles de Mantenimiento

```powershell
# Ver todos los recursos
kubectl get all -n documentos

# Escalar pods
kubectl scale deployment documentos-service --replicas=3 -n documentos

# Ver logs en tiempo real
kubectl logs -f -l app=documentos-service -n documentos

# Ejecutar comando en pod
kubectl exec -it deployment/mongodb -n documentos -- mongosh

# Ver eventos
kubectl get events -n documentos --sort-by='.lastTimestamp'

# Eliminar todo
kubectl delete namespace documentos
```

## 🐛 Troubleshooting

### Pod no inicia
```powershell
kubectl describe pod <pod-name> -n documentos
kubectl logs <pod-name> -n documentos
```

### LoadBalancer en "Pending"
```powershell
# Verificar que el cluster tenga acceso a crear LoadBalancers
kubectl describe service documentos-service -n documentos
```

### MongoDB connection refused
```powershell
# Verificar que MongoDB esté corriendo
kubectl get pods -n documentos
kubectl logs deployment/mongodb -n documentos

# Probar conexión interna
kubectl run -it --rm test-mongo --image=mongo:7.0 --restart=Never -n documentos -- mongosh mongodb://admin:password@mongodb:27017/documentos
```

## 💰 Costos Estimados

- **AKS Cluster (control plane)**: Gratis
- **VMs (2 × Standard_B2s)**: ~$30-40/mes
- **LoadBalancer**: ~$5-10/mes
- **Azure Container Registry (Basic)**: ~$5/mes
- **Managed Disk (5GB)**: ~$0.50/mes

**Total aproximado**: $40-55/mes

**Crédito gratis**:
- Azure for Students: $100 USD (12 meses)
- Cuenta gratuita: $200 USD (30 días)

**Suficiente para el proyecto académico completo.**

## ✅ Checklist de Deployment

- [ ] Cuenta de Azure creada y verificada
- [ ] Azure CLI instalado y autenticado
- [ ] Cluster AKS creado
- [ ] kubectl configurado para el cluster
- [ ] Azure Container Registry (ACR) creado
- [ ] ACR integrado con AKS
- [ ] Manifiestos de Kubernetes creados en carpeta k8s/
- [ ] Dockerfile configurado correctamente
- [ ] GitHub Actions workflow creado
- [ ] GitHub Secrets configurados (AZURE_CREDENTIALS, MONGO_*)
- [ ] Imagen Docker pusheada al ACR
- [ ] Deployment aplicado a Kubernetes
- [ ] LoadBalancer IP obtenida
- [ ] Health endpoint respondiendo
- [ ] API Gateway actualizado con nueva URL
- [ ] Tests de integración exitosos

## 📚 Recursos Adicionales

- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Go Docker Best Practices](https://docs.docker.com/language/golang/build-images/)

## 🆘 Soporte

Si tienes problemas:
1. Revisa los logs: `kubectl logs -f deployment/documentos-service -n documentos`
2. Verifica eventos: `kubectl get events -n documentos`
3. Consulta la documentación oficial de Azure
4. Pregunta al equipo del proyecto

---

**Autor**: Equipo SW2  
**Última actualización**: Noviembre 2025  
**Microservicio**: Documentos (Go + MongoDB)  
**Proveedor**: Azure AKS

---

##  Resumen R�pido: Comandos Esenciales

### Primera vez (Deployment desde cero)
```powershell
# 1. Login y setup
az login
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.ContainerRegistry

# 2. Crear infraestructura
az group create --name sw2-documentos-rg --location eastus
az acr create --resource-group sw2-documentos-rg --name sw2registry --sku Basic
az aks create --resource-group sw2-documentos-rg --name sw2-documentos-cluster --node-count 2 --node-vm-size Standard_DC2s_v3 --enable-managed-identity --generate-ssh-keys
az aks update --resource-group sw2-documentos-rg --name sw2-documentos-cluster --attach-acr sw2registry

# 3. Configurar kubectl
az aks get-credentials --resource-group sw2-documentos-rg --name sw2-documentos-cluster
kubectl get nodes

# 4. Editar JWT_SECRET en k8s/secrets.yaml (debe coincidir con API Gateway)

# 5. Build y push
az acr login --name sw2registry
docker build -t sw2registry.azurecr.io/documentos-service:latest .
docker push sw2registry.azurecr.io/documentos-service:latest

# 6. Deploy
kubectl apply -f k8s/
kubectl apply -f k8s/  # Ejecutar dos veces si da error de namespace
kubectl get all -n sw2-documentos

# 7. Obtener IP
kubectl get svc -n sw2-documentos
# IP: 128.203.103.88
```

### Detener cluster (fin del d�a)
```powershell
az aks stop --resource-group sw2-documentos-rg --name sw2-documentos-cluster
```

### Reiniciar cluster (d�a de defensa)
```powershell
# 1. Iniciar cluster
az aks start --resource-group sw2-documentos-rg --name sw2-documentos-cluster

# 2. Verificar
kubectl get pods -n sw2-documentos
kubectl get svc -n sw2-documentos

# 3. Probar
curl http://$(kubectl get svc documentos-service -n sw2-documentos -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/health
```

### Actualizar c�digo (sin recrear cluster)
```powershell
# 1. Build nueva imagen
docker build -t sw2registry.azurecr.io/documentos-service:latest .
docker push sw2registry.azurecr.io/documentos-service:latest

# 2. Restart deployment
kubectl rollout restart deployment/documentos-service -n sw2-documentos
kubectl get pods -n sw2-documentos
```

### Eliminar todo (despu�s de defender)
```powershell
az group delete --name sw2-documentos-rg --yes --no-wait
```

##  Integraci�n con API Gateway (AWS)

Tu API Gateway debe apuntar a: **http://128.203.103.88**

**JWT_SECRET** (copiar exactamente a todos los servicios):
```
8f7f1e63e4fe5380429da00fe3e79a8ed00c4be5e4a04f82feaf0597a7bca7cd3471dca9223b2b7cf6a9f7ec2a8cd9d3241145bc91192a068445934ada9b5cb4
```

### Configuraci�n en API Gateway
1. Variable de entorno DOCUMENTOS_SERVICE_URL=http://128.203.103.88
2. Variable de entorno JWT_SECRET=(valor de arriba)
3. Proxy de rutas:
   - /documentos/*  http://128.203.103.88/documentos/*
   - Pasar header Authorization: Bearer <token>

##  Tips y Troubleshooting

### �C�mo saber si el cluster est� corriendo o detenido?
```powershell
az aks show --resource-group sw2-documentos-rg --name sw2-documentos-cluster --query "powerState.code"
```

### �C�mo ver logs de un pod?
```powershell
kubectl logs -f deployment/documentos-service -n sw2-documentos
kubectl logs -f deployment/mongodb -n sw2-documentos
```

### �C�mo ver cu�nto cr�dito me queda?
Visita: https://www.microsoftazuresponsorships.com/Balance

### �La IP del LoadBalancer puede cambiar?
S�, al detener y reiniciar el cluster, Azure puede asignar una IP diferente. Siempre verifica con:
```powershell
kubectl get svc -n sw2-documentos
```

### �Puedo usar un dominio en vez de la IP?
S�, pero requiere:
1. Comprar un dominio o usar uno gratuito (Freenom, DuckDNS)
2. Configurar DNS tipo A record apuntando a la IP del LoadBalancer
3. Opcional: Configurar certificado SSL con cert-manager

Para el proyecto acad�mico, la IP es suficiente.

##  Costos Detallados

| Recurso | Costo Running | Costo Stopped | Notas |
|---------|---------------|---------------|-------|
| AKS Control Plane | /hora | /hora | Gratis en tier Free |
| 2 � Standard_DC2s_v3 | .192/hora | /hora | Solo pagas cuando corre |
| Managed Disk (10GB) | .0002/hora | .0002/hora | Siempre se paga |
| LoadBalancer | .005/hora | .005/hora | Se paga mientras exista |
| ACR Basic | .007/hora | .007/hora | Flat rate mensual |
| **TOTAL** | **~.204/hora** | **~.012/hora** | **/mes vs /mes** |

Con  de cr�dito:
- **Corriendo 24/7**: ~490 horas (~20 d�as)
- **Detenido siempre**: ~8,300 horas (~11 meses)
- **Estrategia mixta** (8h/d�a corriendo, 16h detenido): ~2,000 horas (~83 d�as de proyecto)

##  Checklist Final

- [ ] Cuenta Azure for Students activada ( cr�dito)
- [ ] Azure CLI instalado y autenticado
- [ ] Docker Desktop instalado y corriendo
- [ ] kubectl instalado
- [ ] Resource group creado
- [ ] Azure Container Registry creado
- [ ] AKS Cluster creado (2 nodos Standard_DC2s_v3)
- [ ] ACR integrado con AKS
- [ ] JWT_SECRET configurado en k8s/secrets.yaml
- [ ] Imagen Docker construida y pusheada
- [ ] Manifiestos aplicados a Kubernetes
- [ ] Pods corriendo (1/1 Ready)
- [ ] LoadBalancer IP obtenida
- [ ] Health check respondiendo (http://IP/health)
- [ ] Swagger UI accesible (http://IP/docs)
- [ ] API Gateway configurado con la IP del servicio
- [ ] JWT_SECRET sincronizado entre todos los servicios
- [ ] Cluster detenido cuando no se usa

---

**Deployment URL**: http://128.203.103.88  
**Swagger**: http://128.203.103.88/docs  
**Health**: http://128.203.103.88/health  
**Proveedor**: Azure AKS (East US)  
**�ltima actualizaci�n**: Noviembre 2025

