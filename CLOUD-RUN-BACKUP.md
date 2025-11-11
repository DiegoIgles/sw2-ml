# Cloud Run Backup - Volver a Desplegar

## Comandos Rápidos para Volver a Cloud Run

### Redesplegar desde Cero (5 minutos)

```powershell
# 1. Recargar PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 2. Configurar proyecto
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" config set project sw2-ml-service

# 3. Build y push imagen
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" builds submit --tag us-central1-docker.pkg.dev/sw2-ml-service/sw2-ml-repo/ml-service:latest

# 4. Deploy a Cloud Run
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy sw2-ml-service `
  --image us-central1-docker.pkg.dev/sw2-ml-service/sw2-ml-repo/ml-service:latest `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --cpu 1 `
  --memory 1Gi `
  --timeout 300 `
  --min-instances 0 `
  --max-instances 3 `
  --concurrency 80 `
  --set-env-vars "PLAZOS_ENDPOINT=http://IP_EXPEDIENTES/plazos,DOCS_ENDPOINT=http://IP_DOCUMENTOS/admin/documentos"

# 5. Obtener URL
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services describe sw2-ml-service --region us-central1 --format="value(status.url)"
```

### URL Anterior (por si acaso)

```
https://sw2-ml-service-385002445483.us-central1.run.app
```

### Actualizar Variables de Entorno (sin redesplegar)

```powershell
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services update sw2-ml-service `
  --region us-central1 `
  --set-env-vars "PLAZOS_ENDPOINT=http://NUEVA_IP/plazos,DOCS_ENDPOINT=http://NUEVA_IP/admin/documentos"
```

### Ver Logs

```powershell
& "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run services logs read sw2-ml-service --region us-central1 --limit 50
```

### Costo

- **Solo activo**: ~$0.30/día
- **Build**: Gratis (primeros 120 min/día)
- **Almacenamiento**: $0.10/mes

---

**Fecha de backup**: 11 nov 2025  
**Proyecto**: sw2-ml-service  
**Región**: us-central1
