# app/routers/regresion.py
from fastapi import APIRouter, Query
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_score

from ..clients import fetch_plazos, fetch_docs
from ..features import flatten_plazos, enrich_plazos_with_docs, flatten_docs

router = APIRouter(tags=["regresion"])

# --------------------------
# Helpers comunes y features
# --------------------------
def _safe_kfold(n: int, k: int) -> int:
    # Usa k splits, pero no más que n y al menos 2 si es posible
    if n < 2:
        return 1
    return max(2, min(k, n))

def _pipe_lr() -> Pipeline:
    return Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("reg", LinearRegression())
    ])

# ====================================
# 1) REGRESIÓN PARA PLAZOS (days_to_due)
# ====================================
@router.get("/ml/regresion/plazos/dias_restantes")
def reg_plazos_dias_restantes(kfold: int = Query(5, ge=2, le=20)) -> Dict[str, Any]:
    """
    Regresión lineal para predecir days_to_due sin fuga de objetivo:
    - Quita 'days_to_due' de las features (estaba en num_feats).
    - CV robusto con nanmean/nanstd para R² (algunos folds pueden quedar con var(y)=0).
    """
    # 1) Cargar y enriquecer
    payload = fetch_plazos()
    df_plazos = flatten_plazos(payload)
    if df_plazos.empty:
        return {"status": "sin_datos", "detail": "No hay plazos en el endpoint origen."}

    df, num_feats_all = enrich_plazos_with_docs(df_plazos)
    if df.empty or ("days_to_due" not in df.columns):
        return {"status": "sin_datos", "detail": "No hay features numéricas o target 'days_to_due'."}

    # 2) Definir features SIN el target para evitar leakage
    num_feats = [f for f in num_feats_all if f != "days_to_due"]
    if not num_feats:
        # Si por alguna razón no quedan features, usamos baseline
        pred = float(df["days_to_due"].astype(float).mean())
        preds = [{
            "id_plazo": int(df.iloc[i]["id_plazo"]) if pd.notna(df.iloc[i]["id_plazo"]) else None,
            "expediente_id": int(df.iloc[i]["expediente_id"]) if ("expediente_id" in df.columns and pd.notna(df.iloc[i]["expediente_id"])) else None,
            "descripcion": df.iloc[i].get("descripcion"),
            "y_true": float(df.iloc[i]["days_to_due"]),
            "y_pred": pred,
            "residual": float(df.iloc[i]["days_to_due"] - pred)
        } for i in range(len(df))]
        return {
            "status": "fallback_sin_features",
            "reason": "No hay features distintas del target; baseline por media.",
            "n_samples": len(df),
            "features": num_feats,
            "baseline_mean_days_to_due": pred,
            "predictions": preds
        }

    # 3) X, y
    X = df[num_feats].copy().astype(float)
    y = df["days_to_due"].astype(float)
    n = len(X)

    if n < 3 or y.nunique() < 2:
        # Fallback si datos insuficientes o sin variación
        pred = float(y.mean()) if n > 0 else 0.0
        preds = [{
            "id_plazo": int(df.iloc[i]["id_plazo"]) if pd.notna(df.iloc[i]["id_plazo"]) else None,
            "expediente_id": int(df.iloc[i]["expediente_id"]) if ("expediente_id" in df.columns and pd.notna(df.iloc[i]["expediente_id"])) else None,
            "descripcion": df.iloc[i].get("descripcion"),
            "y_true": float(y.iloc[i]),
            "y_pred": pred,
            "residual": float(y.iloc[i] - pred)
        } for i in range(n)]
        return {
            "status": "fallback",
            "reason": "Datos insuficientes o target casi constante",
            "n_samples": n,
            "features": num_feats,
            "baseline_mean_days_to_due": pred,
            "predictions": preds
        }

    # 4) CV + entrenamiento
    cv_splits = _safe_kfold(n, kfold)
    cv = KFold(n_splits=cv_splits, shuffle=True, random_state=42)
    pipe = _pipe_lr()

    # R² puede dar NaN en algún fold si var(y_train)=0 → usar nanmean/nanstd
    r2_scores = cross_val_score(pipe, X, y, cv=cv, scoring="r2")
    mae_scores = -cross_val_score(pipe, X, y, cv=cv, scoring="neg_mean_absolute_error")

    pipe.fit(X, y)
    y_pred = pipe.predict(X)

    reg = pipe.named_steps["reg"]
    coefs = {f: float(c) for f, c in zip(num_feats, reg.coef_)}
    intercept = float(reg.intercept_)

    out_rows: List[Dict[str, Any]] = []
    for i in range(n):
        out_rows.append({
            "id_plazo": int(df.iloc[i]["id_plazo"]) if pd.notna(df.iloc[i]["id_plazo"]) else None,
            "expediente_id": int(df.iloc[i]["expediente_id"]) if ("expediente_id" in df.columns and pd.notna(df.iloc[i]["expediente_id"])) else None,
            "descripcion": df.iloc[i].get("descripcion"),
            "y_true": float(y.iloc[i]),
            "y_pred": float(y_pred[i]),
            "residual": float(y.iloc[i] - y_pred[i]),
            "features": {f: float(X.iloc[i][f]) for f in num_feats}
        })

    return {
        "status": "ok",
        "model": "LinearRegression (impute+scale) sin leakage",
        "n_samples": n,
        "features": num_feats,
        "cv": {
            "splits": cv_splits,
            "r2_folds": [None if np.isnan(v) else float(v) for v in r2_scores],
            "r2_mean": (None if np.isnan(np.nanmean(r2_scores)) else float(np.nanmean(r2_scores))),
            "r2_std": (None if np.isnan(np.nanstd(r2_scores)) else float(np.nanstd(r2_scores))),
            "mae_mean": float(np.mean(mae_scores)),
            "mae_std": float(np.std(mae_scores)),
        },
        "coefficients_std_space": coefs,
        "intercept_std_space": intercept,
        "predictions": out_rows
    }

# ==================================
# 2) REGRESIÓN PARA DOCS (size_mb)
# ==================================
def _docs_with_features() -> Tuple[pd.DataFrame, List[str]]:
    docs = fetch_docs()
    df = flatten_docs(docs)
    if df.empty:
        return df, []

    # Features numéricas sencillas
    df["name_len"] = df["filename"].astype(str).str.len().fillna(0).astype(float)
    df["is_pdf"] = (df["file_ext"].astype(str).str.lower() == "pdf").astype(int)

    for c in ["size_mb", "days_since_created"]:
        if c not in df.columns:
            df[c] = 0.0
    num_feats = ["days_since_created", "name_len", "is_pdf"]

    # Campos base p/salida
    for c in ["doc_id", "filename", "file_ext", "id_expediente", "id_cliente"]:
        if c not in df.columns:
            df[c] = None

    # Tipos correctos
    df[num_feats + ["size_mb"]] = df[num_feats + ["size_mb"]].astype(float).fillna(0.0)
    return df, num_feats

@router.get("/docs/regresion/size_mb")
def reg_docs_size_mb(kfold: int = Query(5, ge=2, le=20)) -> Dict[str, Any]:
    """
    Entrena una regresión lineal para predecir size_mb de los documentos, usando:
    - days_since_created, name_len, is_pdf
    Devuelve CV (R2, MAE), coeficientes (espacio estandarizado) y predicciones por doc.
    """
    df, feats = _docs_with_features()
    if df.empty:
        return {"status": "sin_datos", "detail": "No hay documentos en el endpoint origen."}

    X = df[feats].copy().astype(float)
    y = df["size_mb"].astype(float)
    n = len(X)

    if n < 3 or y.nunique() < 2:
        pred = float(y.mean()) if n > 0 else 0.0
        preds = [{
            "doc_id": df.iloc[i]["doc_id"],
            "filename": df.iloc[i]["filename"],
            "file_ext": df.iloc[i]["file_ext"],
            "id_expediente": int(df.iloc[i]["id_expediente"]) if pd.notna(df.iloc[i]["id_expediente"]) else None,
            "id_cliente": int(df.iloc[i]["id_cliente"]) if pd.notna(df.iloc[i]["id_cliente"]) else None,
            "y_true": float(y.iloc[i]),
            "y_pred": pred,
            "residual": float(y.iloc[i] - pred)
        } for i in range(n)]
        return {
            "status": "fallback",
            "reason": "Datos insuficientes o target casi constante",
            "n_samples": n,
            "features": feats,
            "baseline_mean_size_mb": pred,
            "predictions": preds
        }

    cv_splits = _safe_kfold(n, kfold)
    cv = KFold(n_splits=cv_splits, shuffle=True, random_state=42)
    pipe = _pipe_lr()

    r2_scores = cross_val_score(pipe, X, y, cv=cv, scoring="r2")
    mae_scores = -cross_val_score(pipe, X, y, cv=cv, scoring="neg_mean_absolute_error")

    pipe.fit(X, y)
    y_pred = pipe.predict(X)

    reg = pipe.named_steps["reg"]
    coefs = {f: float(c) for f, c in zip(feats, reg.coef_)}
    intercept = float(reg.intercept_)

    out_rows: List[Dict[str, Any]] = []
    for i in range(n):
        out_rows.append({
            "doc_id": df.iloc[i]["doc_id"],
            "filename": df.iloc[i]["filename"],
            "file_ext": df.iloc[i]["file_ext"],
            "id_expediente": int(df.iloc[i]["id_expediente"]) if pd.notna(df.iloc[i]["id_expediente"]) else None,
            "id_cliente": int(df.iloc[i]["id_cliente"]) if pd.notna(df.iloc[i]["id_cliente"]) else None,
            "y_true": float(y.iloc[i]),
            "y_pred": float(y_pred[i]),
            "residual": float(y.iloc[i] - y_pred[i]),
            "features": {f: float(X.iloc[i][f]) for f in feats}
        })

    return {
        "status": "ok",
        "model": "LinearRegression (impute+scale)",
        "n_samples": n,
        "features": feats,
        "target": "size_mb",
        "cv": {
            "splits": cv_splits,
            "r2_mean": float(np.mean(r2_scores)),
            "r2_std": float(np.std(r2_scores)),
            "mae_mean": float(np.mean(mae_scores)),
            "mae_std": float(np.std(mae_scores)),
        },
        "coefficients_std_space": coefs,
        "intercept_std_space": intercept,
        "predictions": out_rows
    }
