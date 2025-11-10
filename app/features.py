# app/features.py
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import unquote
import pandas as pd
from dateutil import parser as dtparser

from .clients import fetch_plazos, fetch_docs  # (fetch_plazos puede usarse en debug)
import numpy as np
# ----------------------------------------------------------------------
# Fechas / tiempo
# ----------------------------------------------------------------------
def now_ts() -> pd.Timestamp:
    """Fecha/hora actual normalizada a medianoche (naive, sin TZ)."""
    # Importante: naive para que opere con columnas naive
    return pd.Timestamp.now().normalize()

def today_local() -> pd.Timestamp:
    """Alias para compatibilidad con imports existentes."""
    return now_ts()

def safe_parse_date(d: Optional[str]):
    if not d:
        return None
    try:
        return dtparser.parse(d)  # puede retornar aware (UTC) si hay 'Z'
    except Exception:
        return None

# ----------------------------------------------------------------------
# Helpers de normalización de TZ
# ----------------------------------------------------------------------
def to_naive_ts(series: pd.Series) -> pd.Series:
    """
    Convierte una Serie de fechas a datetime64[ns] naive (sin tz).
    - Fuerza utc=True para homogeneizar aware/naive
    - Luego quita la zona horaria con tz_convert(None)
    """
    s = pd.to_datetime(series, errors="coerce", utc=True)
    # ahora es datetime64[ns, UTC] => lo pasamos a naive
    return s.dt.tz_convert(None)

# ----------------------------------------------------------------------
# Plazos
# ----------------------------------------------------------------------
def flatten_plazos(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Convierte el JSON de /plazos en DataFrame y calcula features:
    - fecha_vencimiento / fecha_cumplimiento en datetime64[ns] naive
    - days_to_due, desc_len, estado_abierto, overdue_now
    """
    rows = []
    for item in payload.get("data", []):
        expediente = item.get("expediente") or {}
        cliente = (expediente or {}).get("cliente") or {}
        rows.append({
            "id_plazo": item.get("id_plazo"),
            "descripcion": (item.get("descripcion") or "").strip(),
            "fecha_vencimiento": safe_parse_date(item.get("fecha_vencimiento")),
            "cumplido": bool(item.get("cumplido")),
            "fecha_cumplimiento": safe_parse_date(item.get("fecha_cumplimiento")) if item.get("fecha_cumplimiento") else None,
            "expediente_id": expediente.get("id_expediente"),
            "expediente_estado": (expediente.get("estado") or "").upper().strip() if expediente else "",
            "expediente_titulo": expediente.get("titulo") or "",
            "cliente_nombre": cliente.get("nombre_completo") or "",
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 🔧 A datetime64[ns] naive (quita TZ si venía con 'Z')
    df["fecha_vencimiento"]  = to_naive_ts(df["fecha_vencimiento"])
    df["fecha_cumplimiento"] = to_naive_ts(df["fecha_cumplimiento"])

    # days_to_due robusto (Timedelta -> días)
    today = now_ts()  # naive
    delta = df["fecha_vencimiento"] - today
    df["days_to_due"] = delta.dt.days

    df["desc_len"] = df["descripcion"].astype(str).str.len()
    df["estado_abierto"] = (df["expediente_estado"] == "ABIERTO").astype(int)
    df["overdue_now"] = (df["days_to_due"] < 0) & (~df["cumplido"])
    return df

# ----------------------------------------------------------------------
# Documentos
# ----------------------------------------------------------------------
def flatten_docs(docs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convierte el JSON de /admin/documentos en DataFrame y calcula:
    - created_at -> datetime64[ns] naive
    - size_mb, days_since_created
    """
    rows = []
    for d in docs:
        filename_raw = (d.get("filename") or "").strip()
        filename = unquote(filename_raw)
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        created = d.get("created_at")
        rows.append({
            "doc_id": d.get("doc_id") or d.get("_id"),
            "filename": filename,
            "file_ext": ext,
            "size": d.get("size"),
            "size_mb": (d.get("size") or 0) / (1024.0*1024.0),
            "id_cliente": d.get("id_cliente"),
            "id_expediente": d.get("id_expediente"),
            "created_at": safe_parse_date(created) if created else None,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 🔧 A datetime64[ns] naive
    df["created_at"] = to_naive_ts(df["created_at"])

    today = now_ts()  # naive
    delta = today - df["created_at"]
    df["days_since_created"] = delta.dt.days
    return df

# ----------------------------------------------------------------------
# Agregados por expediente
# ----------------------------------------------------------------------
def aggregate_docs_per_expediente(df_docs: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega por id_expediente: conteo, total MB, días desde último doc,
    recent_docs_7d (flag) y proporción de PDFs.
    """
    if df_docs.empty:
        return pd.DataFrame(columns=[
            "id_expediente", "docs_count_exp", "docs_total_size_mb", "days_since_last_doc",
            "recent_docs_7d", "pdf_ratio_exp"
        ])
    agg = df_docs.groupby("id_expediente").agg(
        docs_count_exp=("doc_id","count"),
        docs_total_size_mb=("size_mb","sum"),
        last_doc=("created_at","max"),
        pdf_count=("file_ext", lambda s: (s.str.lower()=="pdf").sum()),
    ).reset_index()

    today = now_ts()  # naive
    delta = today - agg["last_doc"]
    agg["days_since_last_doc"] = delta.dt.days
    agg["recent_docs_7d"] = agg["last_doc"].apply(lambda x: int(pd.notna(x) and (today - x).days <= 7))
    agg["pdf_ratio_exp"] = np.where(
    agg["docs_count_exp"] > 0,
    agg["pdf_count"] / agg["docs_count_exp"],
    0.0
)
    agg = agg.drop(columns=["last_doc","pdf_count"])
    return agg

# ----------------------------------------------------------------------
# Enriquecimiento de plazos con docs
# ----------------------------------------------------------------------
def enrich_plazos_with_docs(df_plazos: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Une plazos con agregados de documentos por expediente.
    Retorna (df_enriquecido, lista_features_numericas)
    """
    df_docs = flatten_docs(fetch_docs())
    agg = aggregate_docs_per_expediente(df_docs)
    df = df_plazos.merge(agg, how="left", left_on="expediente_id", right_on="id_expediente")
    df = df.drop(columns=["id_expediente"], errors="ignore")

    num_feats = [
        "days_to_due", "desc_len", "estado_abierto",
        "docs_count_exp", "docs_total_size_mb", "days_since_last_doc",
        "recent_docs_7d", "pdf_ratio_exp"
    ]
    # Completar NaN/ausentes para que los modelos no fallen
    for c in ["docs_count_exp", "docs_total_size_mb", "days_since_last_doc", "recent_docs_7d", "pdf_ratio_exp"]:
        if c not in df.columns:
            df[c] = 0
    df[num_feats] = df[num_feats].fillna(0)
    return df, num_feats
