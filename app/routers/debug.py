from fastapi import APIRouter, Response
from ..clients import fetch_plazos, PLAZOS_ENDPOINT, DOCS_ENDPOINT
from ..features import flatten_plazos
import requests

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/plazos_dtypes")
def plazos_dtypes():
    df = flatten_plazos(fetch_plazos())
    return {
        "columns": list(df.columns),
        "dtypes": {k: str(v) for k,v in df.dtypes.items()},
        "sample": df.head(5).astype(str).to_dict(orient="records"),
    }


@router.get("/upstreams_status")
def upstreams_status():
    """Comprueba rápidamente conectividad a los endpoints configurados.

    Devuelve HTTP 200 si ambos upstreams responden con status < 400 en un timeout corto.
    Devuelve HTTP 503 si alguno falla — útil como readinessProbe en Kubernetes.
    """
    results = {}
    overall_ok = True
    for name, url in (("plazos", PLAZOS_ENDPOINT), ("docs", DOCS_ENDPOINT)):
        try:
            r = requests.get(url, timeout=2)
            ok = r.status_code < 400
            results[name] = {"ok": ok, "status_code": r.status_code}
            if not ok:
                overall_ok = False
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)}
            overall_ok = False

    if overall_ok:
        return results
    return Response(content=str(results), status_code=503, media_type="application/json")
