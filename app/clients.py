import os
from typing import Dict, Any, List
import requests

PLAZOS_ENDPOINT = os.getenv("PLAZOS_ENDPOINT", "http://localhost:3000/plazos")
DOCS_ENDPOINT   = os.getenv("DOCS_ENDPOINT",   "http://localhost:8081/admin/documentos")

def fetch_plazos() -> Dict[str, Any]:
    r = requests.get(PLAZOS_ENDPOINT, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_docs() -> List[Dict[str, Any]]:
    r = requests.get(DOCS_ENDPOINT, timeout=10)
    r.raise_for_status()
    return r.json()
