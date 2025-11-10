# app/routers/docs_analytics.py
from fastapi import APIRouter, Query
from typing import List, Dict, Any, Tuple
import itertools
import difflib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

from ..clients import fetch_docs
from ..features import flatten_docs

router = APIRouter(prefix="/docs", tags=["docs-analytics"])


# ============== Helpers de explicabilidad (z-score) ==============
def _fit_mu_sigma(X: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    mu = X.mean()
    sigma = X.std().replace(0, 1e-9)  # evita división por 0
    return mu, sigma

def _top_k_reasons(x_row: pd.Series, mu: pd.Series, sigma: pd.Series, feats: List[str], k: int = 3):
    z = (x_row[feats] - mu[feats]) / sigma[feats]
    absz = z.abs().sort_values(ascending=False)
    top = []
    for f in absz.index[:k]:
        top.append({"feature": f, "value": float(x_row[f]), "zscore": float(z[f])})
    return top


# ============== Prepara features numéricas de documentos ==============
def _docs_with_features() -> Tuple[pd.DataFrame, List[str]]:
    docs = fetch_docs()                 # -> lista de dicts
    df = flatten_docs(docs)             # -> doc_id, filename, file_ext, size_mb, days_since_created, ...

    if df.empty:
        return df, []

    # Derivadas robustas
    df["name_len"] = df["filename"].astype(str).str.len().fillna(0).astype(float)
    df["is_pdf"] = (df["file_ext"].astype(str).str.lower() == "pdf").astype(int)
    # Asegurar numéricas clave que ya vienen de flatten_docs
    for c in ["size_mb", "days_since_created"]:
        if c not in df.columns:
            df[c] = 0.0

    # Set de features numéricas para clustering/anomalías
    num_feats = ["size_mb", "days_since_created", "name_len", "is_pdf"]
    df[num_feats] = df[num_feats].astype(float).fillna(0.0)

    # Normaliza metadatos básicos (solo para el output)
    base_cols = ["doc_id", "filename", "file_ext", "id_expediente", "id_cliente"]
    for c in base_cols:
        if c not in df.columns:
            df[c] = None

    return df, num_feats


# =======================
# 1) K-MEANS (DOCUMENTOS)
# =======================
@router.get("/no_supervisado/clusters")
def docs_clusters(k: int = Query(3, ge=1, description="Número de clusters")) -> Dict[str, Any]:
    df, feats = _docs_with_features()
    if df.empty:
        return {"status": "sin_datos", "detail": "No hay documentos en el endpoint origen."}

    X = df[feats].astype(float).fillna(0.0)
    n = len(X)
    if n == 0:
        return {"status": "sin_datos", "detail": "No hay filas con features numéricas."}

    k = max(1, min(k, n))

    scaler = StandardScaler(with_mean=True, with_std=True)
    Xs = scaler.fit_transform(X.values)

    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(Xs)

    centers_original = scaler.inverse_transform(km.cluster_centers_)
    centers_df = pd.DataFrame(centers_original, columns=feats)

    sizes = pd.Series(labels).value_counts().sort_index()
    clusters_summary: List[Dict[str, Any]] = []
    for i in range(k):
        center_row = centers_df.iloc[i]
        top_feats = (
            center_row.sort_values(ascending=False)
            .head(min(3, len(center_row)))
            .to_dict()
        )
        clusters_summary.append({
            "cluster": i,
            "size": int(sizes.get(i, 0)),
            "center": {f: float(center_row[f]) for f in feats},
            "top3": {k2: float(v2) for k2, v2 in top_feats.items()},
        })

    out_rows: List[Dict[str, Any]] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        feat_dict = {f: float(X.iloc[idx][f]) for f in feats}
        out_rows.append({
            "doc_id": row["doc_id"],
            "filename": row["filename"],
            "file_ext": row["file_ext"],
            "id_expediente": int(row["id_expediente"]) if pd.notna(row["id_expediente"]) else None,
            "id_cliente": int(row["id_cliente"]) if pd.notna(row["id_cliente"]) else None,
            "cluster": int(labels[idx]),
            "features": feat_dict
        })

    return {
        "status": "ok",
        "k": k,
        "n_samples": n,
        "features": feats,
        "clusters": clusters_summary,
        "assignments": out_rows
    }


# ===========================
# 2) ISOLATION FOREST (DOCS)
# ===========================
@router.get("/no_supervisado/anomalias")
def docs_anomalias(
    contaminacion: float = Query(0.15, gt=0.0, lt=0.5, description="Proporción esperada de anomalías (0-0.5)"),
    max_lista: int = Query(50, ge=1, description="Máximo de filas a devolver"),
    explain: bool = Query(False, description="Devuelve top-3 razones (z-scores) por fila"),
    k_reasons: int = Query(3, ge=1, le=10, description="Cantidad de razones si explain=true"),
) -> Dict[str, Any]:
    df, feats = _docs_with_features()
    if df.empty:
        return {"status": "sin_datos", "detail": "No hay documentos en el endpoint origen."}

    X = df[feats].astype(float).fillna(0.0)
    n = len(X)
    if n < 2:
        return {"status": "insuficiente", "detail": "Se requieren al menos 2 filas para detectar anomalías.", "n_samples": n}

    scaler = StandardScaler(with_mean=True, with_std=True)
    Xs = scaler.fit_transform(X.values)

    iso = IsolationForest(
        n_estimators=200,
        max_samples="auto",
        contamination=contaminacion,
        random_state=42,
        n_jobs=-1,
    )
    labels = iso.fit_predict(Xs)    # -1 anómalo, 1 normal
    scores = iso.score_samples(Xs)  # más alto => más normal

    raw = -scores
    rmin, rmax = float(raw.min()), float(raw.max())
    denom = (rmax - rmin) if (rmax > rmin) else 1e-9
    norm = (raw - rmin) / denom

    mu, sigma = _fit_mu_sigma(X) if explain else (None, None)

    rows: List[Dict[str, Any]] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        feat_dict = {f: float(X.iloc[idx][f]) for f in feats}
        base = {
            "doc_id": row["doc_id"],
            "filename": row["filename"],
            "file_ext": row["file_ext"],
            "id_expediente": int(row["id_expediente"]) if pd.notna(row["id_expediente"]) else None,
            "id_cliente": int(row["id_cliente"]) if pd.notna(row["id_cliente"]) else None,
            "es_anomalo": bool(labels[idx] == -1),
            "anomaly_score": float(norm[idx]),
            "iforest_raw": float(raw[idx]),
            "features": feat_dict,
        }
        if explain:
            base["reasons"] = _top_k_reasons(X.iloc[idx], mu, sigma, feats, k=k_reasons)
        rows.append(base)

    rows_sorted = sorted(rows, key=lambda r: r["anomaly_score"], reverse=True)[:max_lista]

    total_anomalos = int(sum(1 for r in rows if r["es_anomalo"]))
    return {
        "status": "ok",
        "n_samples": n,
        "contaminacion": contaminacion,
        "num_anomalos": total_anomalos,
        "features": feats,
        "top": rows_sorted
    }


# =======================================
# 3) Near-duplicados por nombre + tamaño
# =======================================
@router.get("/near_duplicados")
def docs_near_duplicados(
    threshold: float = Query(0.85, ge=0.0, le=1.0, description="Umbral de similitud combinada (0-1)"),
    max_pairs: int = Query(50, ge=1, description="Máximo de pares a devolver"),
    w_name: float = Query(0.7, ge=0.0, le=1.0, description="Peso similitud de nombre"),
    w_size: float = Query(0.3, ge=0.0, le=1.0, description="Peso similitud de tamaño"),
) -> Dict[str, Any]:
    """
    Calcula pares de documentos potencialmente duplicados combinando:
    - Similitud de nombre (SequenceMatcher.ratio)
    - Similitud de tamaño: 1 - |a-b| / max(a,b)
    score = w_name * name_sim + w_size * size_sim
    """
    if not np.isclose(w_name + w_size, 1.0):
        # normaliza si no suma 1
        total = max(w_name + w_size, 1e-9)
        w_name, w_size = w_name / total, w_size / total

    df, feats = _docs_with_features()
    if df.empty or len(df) < 2:
        return {"status": "sin_datos", "detail": "No hay suficientes documentos."}

    # Materializar columnas necesarias
    names = df["filename"].astype(str).fillna("")
    sizes = df["size_mb"].astype(float).fillna(0.0)
    exps  = df["id_expediente"]

    pairs = []
    for i, j in itertools.combinations(range(len(df)), 2):
        name_i, name_j = names.iloc[i], names.iloc[j]
        size_i, size_j = float(sizes.iloc[i]), float(sizes.iloc[j])

        # Similitud por nombre (0..1)
        name_sim = difflib.SequenceMatcher(None, name_i, name_j).ratio()

        # Similitud por tamaño (0..1)
        denom = max(size_i, size_j, 1e-9)
        size_sim = 1.0 - abs(size_i - size_j) / denom

        score = w_name * name_sim + w_size * size_sim
        if score >= threshold:
            pairs.append({
                "doc_id_a": df.iloc[i]["doc_id"],
                "doc_id_b": df.iloc[j]["doc_id"],
                "filename_a": name_i,
                "filename_b": name_j,
                "file_ext_a": df.iloc[i]["file_ext"],
                "file_ext_b": df.iloc[j]["file_ext"],
                "id_expediente_a": int(exps.iloc[i]) if pd.notna(exps.iloc[i]) else None,
                "id_expediente_b": int(exps.iloc[j]) if pd.notna(exps.iloc[j]) else None,
                "name_sim": float(name_sim),
                "size_sim": float(size_sim),
                "score": float(score),
                "same_expediente": bool(exps.iloc[i] == exps.iloc[j]),
            })

    pairs_sorted = sorted(pairs, key=lambda r: r["score"], reverse=True)[:max_pairs]
    return {
        "status": "ok",
        "n_docs": int(len(df)),
        "threshold": threshold,
        "weights": {"name": w_name, "size": w_size},
        "pairs": pairs_sorted
    }
