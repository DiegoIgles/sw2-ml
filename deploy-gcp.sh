#!/bin/bash
# deploy-gcp.sh - Deploy SW2 ML Service a Google Cloud Run
# Uso:
#   ./deploy-gcp.sh
#   PROJECT_ID="mi-proyecto" PLAZOS_ENDPOINT="http://IP/plazos" ./deploy-gcp.sh

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuración
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-sw2-ml-service}"
REPO="${REPO:-sw2-ml-repo}"
IMAGE="${IMAGE:-ml-service}"

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  🚀 Desplegando SW2 ML Service${NC}"
echo -e "${GREEN}  📦 Google Cloud Run${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# Verificar gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI no está instalado.${NC}"
    echo -e "${YELLOW}   Instala desde: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

echo -e "${CYAN}✓ gcloud CLI detectado${NC}"

# Verificar Project ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ No se pudo obtener el Project ID.${NC}"
    echo -e "${YELLOW}   Configura el proyecto primero:${NC}"
    echo -e "${WHITE}   gcloud config set project TU_PROJECT_ID${NC}"
    exit 1
fi

echo -e "${YELLOW}ℹ  Usando proyecto: $PROJECT_ID${NC}"
echo ""

echo -e "${CYAN}📋 Configuración del deployment:${NC}"
echo "   Proyecto:      $PROJECT_ID"
echo "   Región:        $REGION"
echo "   Servicio:      $SERVICE_NAME"
echo "   Repositorio:   $REPO"
echo "   Imagen:        $IMAGE"
[ -n "$PLAZOS_ENDPOINT" ] && echo "   Plazos:        $PLAZOS_ENDPOINT"
[ -n "$DOCS_ENDPOINT" ] && echo "   Documentos:    $DOCS_ENDPOINT"
echo ""

# Confirmar
echo -e "${YELLOW}⚠️  Esto construirá y desplegará el servicio a Cloud Run.${NC}"
read -p "   ¿Continuar? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Deployment cancelado.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Paso 1/3: Construyendo imagen Docker${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

IMAGE_TAG="us-central1-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE:latest"
echo -e "${CYAN}🏗️  Build con Cloud Build (más rápido que local)...${NC}"
echo "   Imagen: $IMAGE_TAG"
echo ""

gcloud builds submit --tag "$IMAGE_TAG" --project="$PROJECT_ID"

echo -e "${GREEN}✅ Imagen construida y pusheada exitosamente${NC}"
echo ""

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Paso 2/3: Desplegando a Cloud Run${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Construir comando de deploy
DEPLOY_CMD=(
    gcloud run deploy "$SERVICE_NAME"
    --image "$IMAGE_TAG"
    --platform managed
    --region "$REGION"
    --allow-unauthenticated
    --cpu 1
    --memory 1Gi
    --timeout 300
    --min-instances 0
    --max-instances 3
    --concurrency 80
    --project="$PROJECT_ID"
)

# Agregar env vars si existen
ENV_VARS=()
[ -n "$PLAZOS_ENDPOINT" ] && ENV_VARS+=("PLAZOS_ENDPOINT=$PLAZOS_ENDPOINT")
[ -n "$DOCS_ENDPOINT" ] && ENV_VARS+=("DOCS_ENDPOINT=$DOCS_ENDPOINT")

if [ ${#ENV_VARS[@]} -gt 0 ]; then
    IFS=,
    DEPLOY_CMD+=(--set-env-vars "${ENV_VARS[*]}")
    unset IFS
fi

echo -e "${CYAN}🚀 Ejecutando deployment...${NC}"
echo "   CPU: 1 vCPU, RAM: 1 GB (ultra-económico)"
echo "   Timeout: 300s, Instances: 0-3, Concurrency: 80"
echo ""

"${DEPLOY_CMD[@]}"

echo -e "${GREEN}✅ Servicio desplegado exitosamente${NC}"
echo ""

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Paso 3/3: Verificación y Tests${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Obtener URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)")

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}⚠️  No se pudo obtener la URL del servicio.${NC}"
    exit 1
fi

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ DEPLOYMENT EXITOSO${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}🌐 URL del servicio:${NC}"
echo -e "${WHITE}   $SERVICE_URL${NC}"
echo ""
echo -e "${CYAN}📊 Endpoints disponibles:${NC}"
echo "   Health:        $SERVICE_URL/health"
echo "   Liveness:      $SERVICE_URL/health/live"
echo "   Readiness:     $SERVICE_URL/debug/upstreams_status"
echo "   Swagger UI:    $SERVICE_URL/docs"
echo "   OpenAPI:       $SERVICE_URL/openapi.json"
echo ""

# Probar health check
echo -e "${YELLOW}🧪 Probando health check...${NC}"
if curl -f -s "$SERVICE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check OK${NC}"
    RESPONSE=$(curl -s "$SERVICE_URL/health")
    echo "   Respuesta: $RESPONSE"
else
    echo -e "${RED}⚠️  Health check falló (puede ser cold start, reintenta manualmente)${NC}"
fi

echo ""
echo -e "${CYAN}📝 Comandos útiles:${NC}"
echo ""
echo -e "${WHITE}  # Ver logs en tiempo real${NC}"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION --limit 50 --project=$PROJECT_ID"
echo ""
echo -e "${WHITE}  # Ver logs (tail -f)${NC}"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION --project=$PROJECT_ID"
echo ""
echo -e "${WHITE}  # Actualizar variables de entorno${NC}"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars KEY=VALUE --project=$PROJECT_ID"
echo ""
echo -e "${WHITE}  # Forzar nuevo deployment${NC}"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --project=$PROJECT_ID"
echo ""
echo -e "${WHITE}  # Ver detalles del servicio${NC}"
echo "  gcloud run services describe $SERVICE_NAME --region $REGION --project=$PROJECT_ID"
echo ""
echo -e "${WHITE}  # Eliminar servicio${NC}"
echo "  gcloud run services delete $SERVICE_NAME --region $REGION --project=$PROJECT_ID"
echo ""

echo -e "${CYAN}🔗 Próximos pasos:${NC}"
echo "   1. Prueba Swagger UI: $SERVICE_URL/docs"
echo "   2. Actualiza tu API Gateway con: ML_SERVICE_URL=$SERVICE_URL"
echo "   3. Verifica conectividad con upstreams: $SERVICE_URL/debug/upstreams_status"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🎉 Deployment completado${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
