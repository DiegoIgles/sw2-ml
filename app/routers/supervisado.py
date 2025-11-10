from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..clients import fetch_plazos
from ..features import flatten_plazos, enrich_plazos_with_docs
from ..models import ensure_supervised_model, score_supervised

router = APIRouter(prefix="/ml/supervisado", tags=["supervisado"])

@router.get("/prob_riesgo")
def prob_riesgo():
    payload = fetch_plazos()
    df = flatten_plazos(payload)
    df, num_feats = enrich_plazos_with_docs(df)
    model, status = ensure_supervised_model(df, num_feats)
    data = score_supervised(df, model, num_feats)
    return JSONResponse({"status": status, "total": len(data), "data": data})
