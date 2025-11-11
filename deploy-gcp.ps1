# deploy-gcp.ps1 - Deploy SW2 ML Service a Google Cloud Run
# Uso:
#   .\deploy-gcp.ps1
#   .\deploy-gcp.ps1 -ProjectID "mi-proyecto" -Region "us-central1" -PlazosEndpoint "http://IP/plazos" -DocsEndpoint "http://IP/admin/documentos"

param(
    [string]$ProjectID = "",
    [string]$Region = "us-central1",
    [string]$ServiceName = "sw2-ml-service",
    [string]$Repo = "sw2-ml-repo",
    [string]$Image = "ml-service",
    [string]$PlazosEndpoint = "",
    [string]$DocsEndpoint = ""
)

# Colores para output
function Write-ColorOutput {
    param($ForegroundColor, [string]$Message)
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Message
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Green "=========================================="
Write-ColorOutput Green "  🚀 Desplegando SW2 ML Service"
Write-ColorOutput Green "  📦 Google Cloud Run"
Write-ColorOutput Green "=========================================="
Write-Output ""

# Verificar que gcloud esté instalado
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-ColorOutput Red "❌ gcloud CLI no está instalado."
    Write-ColorOutput Yellow "   Instala desde: https://cloud.google.com/sdk/docs/install"
    Write-ColorOutput Yellow "   O usa Chocolatey: choco install gcloudsdk"
    exit 1
}

Write-ColorOutput Cyan "✓ gcloud CLI detectado"

# Obtener ProjectID si no se pasó como parámetro
if ([string]::IsNullOrEmpty($ProjectID)) {
    $ProjectID = gcloud config get-value project 2>$null
    if ([string]::IsNullOrEmpty($ProjectID)) {
        Write-ColorOutput Red "❌ No se pudo obtener el Project ID."
        Write-ColorOutput Yellow "   Configura el proyecto primero:"
        Write-ColorOutput White "   gcloud config set project TU_PROJECT_ID"
        exit 1
    }
    Write-ColorOutput Yellow "ℹ  Usando proyecto configurado: $ProjectID"
} else {
    Write-ColorOutput Cyan "✓ Proyecto especificado: $ProjectID"
}

Write-Output ""
Write-ColorOutput Cyan "📋 Configuración del deployment:"
Write-Output "   Proyecto:      $ProjectID"
Write-Output "   Región:        $Region"
Write-Output "   Servicio:      $ServiceName"
Write-Output "   Repositorio:   $Repo"
Write-Output "   Imagen:        $Image"
if (-not [string]::IsNullOrEmpty($PlazosEndpoint)) {
    Write-Output "   Plazos:        $PlazosEndpoint"
}
if (-not [string]::IsNullOrEmpty($DocsEndpoint)) {
    Write-Output "   Documentos:    $DocsEndpoint"
}
Write-Output ""

# Confirmar antes de continuar
Write-ColorOutput Yellow "⚠️  Esto construirá y desplegará el servicio a Cloud Run."
$confirm = Read-Host "   ¿Continuar? (y/N)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-ColorOutput Yellow "❌ Deployment cancelado."
    exit 0
}

Write-Output ""
Write-ColorOutput Yellow "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-ColorOutput Yellow "  Paso 1/3: Construyendo imagen Docker"
Write-ColorOutput Yellow "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Output ""

$imageTag = "us-central1-docker.pkg.dev/$ProjectID/$Repo/${Image}:latest"
Write-ColorOutput Cyan "🏗️  Build con Cloud Build (más rápido que local)..."
Write-Output "   Imagen: $imageTag"
Write-Output ""

gcloud builds submit --tag $imageTag --project=$ProjectID

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "❌ Error al construir la imagen."
    Write-ColorOutput Yellow "   Verifica:"
    Write-Output "   • Dockerfile existe en el directorio actual"
    Write-Output "   • Cloud Build API está habilitada"
    Write-Output "   • Artifact Registry repository '$Repo' existe"
    Write-Output ""
    Write-ColorOutput Yellow "   Habilitar API: gcloud services enable cloudbuild.googleapis.com"
    Write-ColorOutput Yellow "   Crear repo:    gcloud artifacts repositories create $Repo --repository-format=docker --location=us-central1"
    exit 1
}

Write-ColorOutput Green "✅ Imagen construida y pusheada exitosamente"
Write-Output ""

Write-ColorOutput Yellow "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-ColorOutput Yellow "  Paso 2/3: Desplegando a Cloud Run"
Write-ColorOutput Yellow "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Output ""

# Construir comando de deploy
$deployCmd = @(
    "gcloud", "run", "deploy", $ServiceName,
    "--image", $imageTag,
    "--platform", "managed",
    "--region", $Region,
    "--allow-unauthenticated",
    "--cpu", "1",
    "--memory", "1Gi",
    "--timeout", "300",
    "--min-instances", "0",
    "--max-instances", "3",
    "--concurrency", "80",
    "--project=$ProjectID"
)

# Agregar variables de entorno si se especificaron
$envVars = @()
if (-not [string]::IsNullOrEmpty($PlazosEndpoint)) {
    $envVars += "PLAZOS_ENDPOINT=$PlazosEndpoint"
}
if (-not [string]::IsNullOrEmpty($DocsEndpoint)) {
    $envVars += "DOCS_ENDPOINT=$DocsEndpoint"
}
if ($envVars.Count -gt 0) {
    $deployCmd += "--set-env-vars"
    $deployCmd += ($envVars -join ",")
}

Write-ColorOutput Cyan "🚀 Ejecutando deployment..."
Write-Output "   CPU: 1 vCPU, RAM: 1 GB (ultra-económico)"
Write-Output "   Timeout: 300s, Instances: 0-3, Concurrency: 80"
Write-Output ""

& $deployCmd[0] $deployCmd[1..($deployCmd.Length-1)]

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "❌ Error al desplegar el servicio."
    Write-ColorOutput Yellow "   Verifica:"
    Write-Output "   • Cloud Run API está habilitada"
    Write-Output "   • Tienes permisos suficientes"
    Write-Output ""
    Write-ColorOutput Yellow "   Habilitar API: gcloud services enable run.googleapis.com"
    exit 1
}

Write-ColorOutput Green "✅ Servicio desplegado exitosamente"
Write-Output ""

Write-ColorOutput Yellow "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-ColorOutput Yellow "  Paso 3/3: Verificación y Tests"
Write-ColorOutput Yellow "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Output ""

# Obtener URL del servicio
$ServiceURL = gcloud run services describe $ServiceName --region $Region --project=$ProjectID --format="value(status.url)"

if ([string]::IsNullOrEmpty($ServiceURL)) {
    Write-ColorOutput Red "⚠️  No se pudo obtener la URL del servicio."
    exit 1
}

Write-ColorOutput Green "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-ColorOutput Green "  ✅ DEPLOYMENT EXITOSO"
Write-ColorOutput Green "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Output ""
Write-ColorOutput Cyan "🌐 URL del servicio:"
Write-ColorOutput White "   $ServiceURL"
Write-Output ""
Write-ColorOutput Cyan "📊 Endpoints disponibles:"
Write-Output "   Health:        $ServiceURL/health"
Write-Output "   Liveness:      $ServiceURL/health/live"
Write-Output "   Readiness:     $ServiceURL/debug/upstreams_status"
Write-Output "   Swagger UI:    $ServiceURL/docs"
Write-Output "   OpenAPI:       $ServiceURL/openapi.json"
Write-Output ""

# Probar health check
Write-ColorOutput Yellow "🧪 Probando health check..."
try {
    $response = Invoke-RestMethod -Uri "$ServiceURL/health" -Method Get -TimeoutSec 15 -ErrorAction Stop
    Write-ColorOutput Green "✅ Health check OK"
    Write-Output "   Respuesta: $($response | ConvertTo-Json -Compress)"
} catch {
    Write-ColorOutput Red "⚠️  Health check falló (puede ser cold start, reintenta manualmente)"
    Write-Output "   Error: $_"
}

Write-Output ""
Write-ColorOutput Cyan "📝 Comandos útiles:"
Write-Output ""
Write-ColorOutput White "  # Ver logs en tiempo real"
Write-Output "  gcloud run services logs read $ServiceName --region $Region --limit 50 --project=$ProjectID"
Write-Output ""
Write-ColorOutput White "  # Ver logs (tail -f)"
Write-Output "  gcloud run services logs tail $ServiceName --region $Region --project=$ProjectID"
Write-Output ""
Write-ColorOutput White "  # Actualizar variables de entorno"
Write-Output "  gcloud run services update $ServiceName --region $Region --set-env-vars KEY=VALUE --project=$ProjectID"
Write-Output ""
Write-ColorOutput White "  # Forzar nuevo deployment"
Write-Output "  gcloud run services update $ServiceName --region $Region --project=$ProjectID"
Write-Output ""
Write-ColorOutput White "  # Ver detalles del servicio"
Write-Output "  gcloud run services describe $ServiceName --region $Region --project=$ProjectID"
Write-Output ""
Write-ColorOutput White "  # Eliminar servicio"
Write-Output "  gcloud run services delete $ServiceName --region $Region --project=$ProjectID"
Write-Output ""

Write-ColorOutput Cyan "🔗 Próximos pasos:"
Write-Output "   1. Prueba Swagger UI: $ServiceURL/docs"
Write-Output "   2. Actualiza tu API Gateway con: ML_SERVICE_URL=$ServiceURL"
Write-Output "   3. Verifica conectividad con upstreams: $ServiceURL/debug/upstreams_status"
Write-Output ""

Write-ColorOutput Green "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-ColorOutput Green "  🎉 Deployment completado"
Write-ColorOutput Green "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
