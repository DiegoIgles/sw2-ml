# app/routers/no_supervisado.py
from fastapi import APIRouter, Query
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

from ..clients import fetch_plazos
from ..features import flatten_plazos, enrich_plazos_with_docs

router = APIRouter(prefix="/ml/no_supervisado", tags=["ml-no-supervisado"])


# =========================
# Helpers de "explicaciones"
# =========================
def _fit_mu_sigma(X: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Promedio y desviación estándar por feature para z-score.
    Reemplaza desviación 0 por un epsilon para evitar divisiones por cero.
    """
    mu = X.mean()
    sigma = X.std().replace(0, 1e-9)
    return mu, sigma


def _top_k_reasons(
    x_row: pd.Series, mu: pd.Series, sigma: pd.Series, feats: List[str], k: int = 3
) -> List[Dict[str, Any]]:
    """
    Devuelve las k features con mayor |z-score| para una fila (explicación simple).
    z = (x - mu) / sigma
    """
    z = (x_row[feats] - mu[feats]) / sigma[feats]
    absz = z.abs().sort_values(ascending=False)
    top = []
    for f in absz.index[: k]:
        top.append({"feature": f, "value": float(x_row[f]), "zscore": float(z[f])})
    return top


# =====================
# K-MEANS CLUSTERS
# =====================
@router.get("/clusters")
def clusters(k: int = Query(3, ge=1, description="Número de clusters")) -> Dict[str, Any]:
    payload = fetch_plazos()
    df_plazos = flatten_plazos(payload)
    if df_plazos.empty:
        return {"status": "sin_datos", "detail": "No hay plazos en el endpoint origen."}

    df, num_feats = enrich_plazos_with_docs(df_plazos)
    if df.empty:
        return {"status": "sin_datos", "detail": "Sin filas tras enriquecimiento."}

    base_cols = ["id_plazo", "expediente_id", "descripcion"]
    for c in base_cols:
        if c not in df.columns:
            df[c] = None

    X = df[num_feats].copy().astype(float).fillna(0.0)
    n = len(X)
    if n == 0:
        return {"status": "sin_datos", "detail": "No hay filas con features numéricas."}

    k = max(1, min(k, n))

    scaler = StandardScaler(with_mean=True, with_std=True)
    Xs = scaler.fit_transform(X.values)

    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(Xs)

    centers_original = scaler.inverse_transform(km.cluster_centers_)
    centers_df = pd.DataFrame(centers_original, columns=num_feats)

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
            "center": {f: float(center_row[f]) for f in num_feats},
            "top3": {k2: float(v2) for k2, v2 in top_feats.items()},
        })

    out_rows: List[Dict[str, Any]] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        feat_dict = {f: float(X.iloc[idx][f]) for f in num_feats}
        out_rows.append({
            "id_plazo": int(row["id_plazo"]) if pd.notna(row["id_plazo"]) else None,
            "expediente_id": int(row["expediente_id"]) if pd.notna(row["expediente_id"]) else None,
            "descripcion": row["descripcion"],
            "cluster": int(labels[idx]),
            "features": feat_dict
        })

    return {
        "status": "ok",
        "k": k,
        "n_samples": n,
        "features": num_feats,
        "clusters": clusters_summary,
        "assignments": out_rows
    }


# =====================
# ISOLATION FOREST (ANOMALÍAS)
# =====================
@router.get("/anomalias")
def anomalias(
    contaminacion: float = Query(0.15, gt=0.0, lt=0.5, description="Proporción esperada de anomalías (0-0.5)"),
    max_lista: int = Query(50, ge=1, description="Máximo de filas a devolver ordenadas por score de anomalía"),
    explain: bool = Query(False, description="Devuelve top-3 razones (z-scores) por fila"),
    k_reasons: int = Query(3, ge=1, le=10, description="Cantidad de razones a devolver cuando explain=true"),
) -> Dict[str, Any]:
    """
    Marca plazos anómalos combinando features numéricas (días al vencimiento, docs, etc.).
    - es_anomalo: True si IsolationForest => -1
    - anomaly_score: [0,1], mayor => más anómalo (normalizado desde score_samples)
    - explain=true: agrega "reasons" con top-k z-scores por fila
    """
    payload = fetch_plazos()
    df_plazos = flatten_plazos(payload)
    if df_plazos.empty:
        return {"status": "sin_datos", "detail": "No hay plazos en el endpoint origen."}

    df, num_feats = enrich_plazos_with_docs(df_plazos)
    if df.empty:
        return {"status": "sin_datos", "detail": "Sin filas tras enriquecimiento."}

    base_cols = ["id_plazo", "expediente_id", "descripcion"]
    for c in base_cols:
        if c not in df.columns:
            df[c] = None

    X = df[num_feats].copy().astype(float).fillna(0.0)
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
    labels = iso.fit_predict(Xs)  # -1 anómalo, 1 normal
    scores = iso.score_samples(Xs)  # más alto => más normal

    # Convertir a "anomaly_score" (más grande => más anómalo), normalizado [0,1]
    raw = -scores  # invertir: más grande => más anómalo
    rmin, rmax = float(raw.min()), float(raw.max())
    denom = (rmax - rmin) if (rmax > rmin) else 1e-9
    norm = (raw - rmin) / denom

    # Preparar explicaciones (z-scores) si se pide
    reasons_mu, reasons_sigma = _fit_mu_sigma(X) if explain else (None, None)

    rows: List[Dict[str, Any]] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        feat_dict = {f: float(X.iloc[idx][f]) for f in num_feats}
        base = {
            "id_plazo": int(row["id_plazo"]) if pd.notna(row["id_plazo"]) else None,
            "expediente_id": int(row["expediente_id"]) if pd.notna(row["expediente_id"]) else None,
            "descripcion": row["descripcion"],
            "es_anomalo": bool(labels[idx] == -1),
            "anomaly_score": float(norm[idx]),
            "iforest_raw": float(raw[idx]),
            "features": feat_dict,
        }
        if explain:
            base["reasons"] = _top_k_reasons(
                X.iloc[idx], reasons_mu, reasons_sigma, num_feats, k=k_reasons
            )
        rows.append(base)

    # Ordenar por score descendente y truncar
    rows_sorted = sorted(rows, key=lambda r: r["anomaly_score"], reverse=True)
    rows_sorted = rows_sorted[:max_lista]

    total_anomalos = int(sum(1 for r in rows if r["es_anomalo"]))
    return {
        "status": "ok",
        "n_samples": n,
        "contaminacion": contaminacion,
        "num_anomalos": total_anomalos,
        "features": num_feats,
        "top": rows_sorted
    }
