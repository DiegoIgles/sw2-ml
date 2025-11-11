@echo off
REM Script rápido para levantar el servicio localmente con Docker Compose (Windows)
docker-compose -f docker-compose.local.yml up --build -d
necho "Esperando unos segundos para que el contenedor arranque..."
docker ps --filter "name=sw2-ml-local"
