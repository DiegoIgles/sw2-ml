import os
import logging
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)

# Compatibilidad con nombres de variables del API Gateway local-testing guide:
# - EXPEDIENTES_URL (gateway) -> PLAZOS_ENDPOINT (este servicio)
# - DOCUMENTOS_URL  (gateway) -> DOCS_ENDPOINT (este servicio)
PLAZOS_ENDPOINT = os.getenv("PLAZOS_ENDPOINT") or os.getenv("EXPEDIENTES_URL") or "http://localhost:3000/plazos"
DOCS_ENDPOINT = os.getenv("DOCS_ENDPOINT") or os.getenv("DOCUMENTOS_URL") or "http://localhost:8081/admin/documentos"

def fetch_plazos() -> Dict[str, Any]:
    try:
        r = requests.get(PLAZOS_ENDPOINT, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        # No queremos que un upstream caído provoque errores tipo None en el flujo.
        logger.exception("fetch_plazos failed for %s", PLAZOS_ENDPOINT)
        return {"data": []}

def fetch_docs() -> List[Dict[str, Any]]:
    try:
        r = requests.get(DOCS_ENDPOINT, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Normalizar distintas formas de respuesta:
        # - Si el endpoint devuelve {'data': [...]}, devolver la lista interna
        # - Si devuelve directamente una lista, devolverla
        # - Si devuelve otra cosa o null, devolver lista vacía
        if isinstance(data, dict) and "data" in data:
            return data.get("data") or []
        if isinstance(data, list):
            return data
        return []
    except Exception as exc:
        logger.exception("fetch_docs failed for %s", DOCS_ENDPOINT)
        return []
