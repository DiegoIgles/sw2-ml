# 💰 Costos de Google Cloud Run para ML Service

## Resumen Ejecutivo

**Configuración ultra-económica (recomendada)**:
- CPU: 1 vCPU
- RAM: 1 GB
- Min instances: 0 (escala a $0 cuando no hay tráfico)
- Max instances: 3
- Concurrency: 80

## Estimación de Costos SIN Crédito Gratis

### Escenarios Reales

| Escenario | Requests/día | Tiempo activo/día | Costo/mes | Notas |
|-----------|--------------|-------------------|-----------|-------|
| **Desarrollo normal** | 10-50 | 30-60 min | **$0.10-0.75** | Uso típico académico |
| **Testing intensivo** | 100-500 | 2-4 horas | $1-3 | Días de pruebas |
| **Demo/Defensa** | 50-200 | 1-2 horas | $0.50-2 | Un día específico |
| **24/7 continuo** | 1000+ | 24 horas | $20-25 | Peor caso (muy raro) |

### ¿Cuánto Recargar?

| Recarga | Duración estimada | Para qué alcanza |
|---------|-------------------|------------------|
| **$5 USD** | 6-10 meses | Desarrollo completo + margen |
| **$10 USD** ✅ | 12+ meses | **Recomendado** - Proyecto completo sin preocupaciones |
| **$20 USD** | 24+ meses | Holgado - Incluye experimentación |

**Recomendación: Recarga $10 USD** (suficiente para todo el proyecto + defensa + buffer)

## Comparación con Otros Proveedores

| Proveedor | Microservicio | Configuración | Costo/mes | Escalado |
|-----------|---------------|---------------|-----------|----------|
| **Google Cloud Run** ✅ | **ML Service** | **1 vCPU, 1GB** | **$0.50-1** | **Automático a 0** |
| DigitalOcean DOKS | Expedientes | 2 × s-2vcpu-2gb | $37 | Manual |
| Azure AKS | Documentos | 2 × Standard_DC2s_v3 | $140 (stopped: $2) | Manual |

**Cloud Run es 40-140x más barato** que los otros servicios.

## Breakdown Detallado de Costos

### Precio por Recurso (us-central1)

| Recurso | Precio | Tu uso estimado | Costo/mes |
|---------|--------|-----------------|-----------|
| **CPU** | $0.00002400/vCPU-sec | ~30 min/día | $0.05-0.50 |
| **Memory** | $0.00000250/GiB-sec | ~30 min/día | $0.01-0.25 |
| **Requests** | $0.40/millón | < 50k/mes | $0.00 (gratis) |
| **Container Registry** | ~$0.026/GB/mes | 0.5 GB | $0.10 |
| **Networking** | $0.12/GB (egress) | < 1 GB/mes | $0.05 |
| **TOTAL** | | | **$0.21-0.90** |

### Primeros 2 Millones de Requests: GRATIS

Cloud Run incluye **2M requests/mes gratis**. Con 50 requests/día:
- Mes: 50 × 30 = 1,500 requests
- Año: 1,500 × 12 = 18,000 requests
- **Jamás pagarás por requests** con tráfico académico

### Escalado a 0 = $0

Cuando **no hay tráfico** (noches, fines de semana):
- CPU: $0
- RAM: $0
- Solo pagas: Container Registry (~$0.10/mes)

**Ahorro vs mantener VM corriendo 24/7**: ~$20-25/mes

## Optimizaciones de Costo

### Ya Implementadas

✅ **min-instances: 0** - Escala a 0 automáticamente
✅ **max-instances: 3** - Límite bajo (evita gastos inesperados)
✅ **concurrency: 80** - Múltiples requests por instancia
✅ **1 vCPU, 1 GB RAM** - Suficiente para scikit-learn
✅ **HTTP (no HTTPS custom)** - Usa SSL managed gratis

### Adicionales (si necesitas reducir más)

1. **Región más barata**: `us-central1` es la más económica
2. **Timeout bajo**: 300s es razonable (vs 900s máximo)
3. **Build con Cloud Build**: Gratis (primeros 120 min/día)
4. **Artifact Registry**: $0.10/GB/mes (vs Container Registry $0.026/GB/mes, pero más límites)

## Proyección de Gasto Real

### Mes 1-2 (Setup y desarrollo)
- Builds: 5-10 × $0 = $0 (gratis)
- Testing: 20 requests/día × $0 = $0 (gratis)
- Runtime: ~30 min/día × $0.05 = **$0.50**
- Registry: $0.10
- **Total: ~$0.60/mes**

### Mes 3-4 (Testing intensivo)
- Testing: 100 requests/día × $0 = $0 (gratis)
- Runtime: ~2 horas/día × $0.15 = **$1.50**
- Registry: $0.10
- **Total: ~$1.60/mes**

### Día de Defensa
- Runtime: 2 horas × $0.15 = **$0.30**
- Requests: 200 × $0 = $0 (gratis)
- **Total: ~$0.30**

### Proyecto Completo (4 meses)
- Desarrollo (2 meses): $0.60 × 2 = $1.20
- Testing (1 mes): $1.60
- Defensa (1 día): $0.30
- Buffer: $1.00
- **Total estimado: ~$4.10**

**Con $10 recargados, te sobran ~$6 para otros proyectos.**

## Comparación: VM vs Cloud Run

### Compute Engine (VM e2-micro)
- Costo: $7.11/mes (running 24/7)
- CPU: 0.25-2 vCPUs (shared)
- RAM: 1 GB
- Setup: Manual (nginx, systemd, etc)
- Escalado: Manual
- **Costo 4 meses: ~$28**

### Cloud Run (configuración actual)
- Costo: $0.50-1/mes (escala a 0)
- CPU: 1 vCPU (dedicado cuando activo)
- RAM: 1 GB
- Setup: Automático
- Escalado: Automático
- **Costo 4 meses: ~$4** ✅

**Cloud Run ahorra $24 vs VM** en el proyecto completo.

## Monitoreo de Costos en Tiempo Real

### Ver facturación actual

```powershell
# Ver billing account
gcloud billing accounts list

# Ver gasto acumulado del proyecto
gcloud billing projects describe $(gcloud config get-value project)

# O visita el dashboard
https://console.cloud.google.com/billing
```

### Alertas de presupuesto (recomendado)

1. Ve a: https://console.cloud.google.com/billing/budgets
2. Click "Create Budget"
3. Configura:
   - Budget amount: $5 (50% de tu recarga)
   - Alert threshold: 50%, 90%, 100%
   - Email notifications: tu correo
4. Save

**Te avisará si te acercas al límite.**

## Estrategia de Ahorro Máximo

### Durante Desarrollo (Días normales)
```powershell
# Ya está configurado para escalar a 0 automáticamente
# No necesitas hacer nada
# Costo: ~$0.50/mes
```

### Durante Testing Intensivo (Días específicos)
```powershell
# Subir a 1 instancia mínima (solo esos días)
gcloud run services update sw2-ml-service --min-instances 1 --region us-central1

# Volver a 0 al terminar (automático después de 15 min sin tráfico)
gcloud run services update sw2-ml-service --min-instances 0 --region us-central1
```

### Día de Defensa
```powershell
# 30 minutos antes: subir min-instances a 1 (elimina cold start)
gcloud run services update sw2-ml-service --min-instances 1 --region us-central1

# Después de defender: volver a 0
gcloud run services update sw2-ml-service --min-instances 0 --region us-central1
```

### Después de Defender (Proyecto terminado)
```powershell
# Opción 1: Dejar corriendo (sigue escalando a 0 = $0.10/mes solo registry)
# No hacer nada

# Opción 2: Eliminar servicio (liberar todo)
gcloud run services delete sw2-ml-service --region us-central1

# Opción 3: Eliminar proyecto completo
gcloud projects delete $(gcloud config get-value project)
```

## FAQ

**¿1 GB RAM es suficiente?**
Sí, para datasets pequeños/medianos (< 10k docs). Si tienes OOM errors, puedes subir a 2GB:
```powershell
gcloud run services update sw2-ml-service --memory 2Gi --region us-central1
# Costo adicional: ~$0.50/mes
```

**¿Y si tengo cold starts lentos?**
Cold start típico: 3-5s. Si necesitas 0s:
```powershell
gcloud run services update sw2-ml-service --min-instances 1 --region us-central1
# Costo adicional: ~$15-20/mes (solo cuando necesario)
```

**¿Puedo pausar el servicio para no gastar?**
No hace falta — con `min-instances: 0`, ya escala a $0 automáticamente.

**¿Qué pasa si me paso de presupuesto?**
1. Configura alertas de presupuesto (arriba)
2. Si llegas al límite, el servicio sigue corriendo (Google te factura)
3. Puedes eliminar el servicio en cualquier momento

**¿Es mejor recargar $5 o $10?**
$10 — te da tranquilidad. $5 alcanza técnicamente, pero con $10 no tienes que preocuparte.

## Conclusión

**Respuesta corta**: Recarga **$10 USD** y olvídate de los costos.

**Costo real del proyecto**: ~$4-5 total

**Sobra**: ~$5-6 para otros proyectos o experimentos

**Cloud Run es la opción más económica** para este microservicio, especialmente vs DigitalOcean ($37/mes) o Azure ($140/mes).

---

**Última actualización**: Noviembre 2025  
**Configuración**: 1 vCPU, 1 GB, min=0, max=3, HTTP  
**Región**: us-central1 (más barata)
