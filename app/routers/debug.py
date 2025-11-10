from fastapi import APIRouter
from ..clients import fetch_plazos
from ..features import flatten_plazos

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/plazos_dtypes")
def plazos_dtypes():
    df = flatten_plazos(fetch_plazos())
    return {
        "columns": list(df.columns),
        "dtypes": {k: str(v) for k,v in df.dtypes.items()},
        "sample": df.head(5).astype(str).to_dict(orient="records"),
    }
