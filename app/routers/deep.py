# app/routers/deep.py
from fastapi import APIRouter, Query
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd

from ..clients import fetch_plazos, fetch_docs
from ..features import flatten_plazos, enrich_plazos_with_docs, flatten_docs

# Intentar PyTorch; si falla, usamos sklearn como fallback
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

# Fallback (y también lo usamos para escalado si quieres)
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor

router = APIRouter(prefix="/ml/deep", tags=["ml-deep"])


# -----------------------------
# Utilidades comunes
# -----------------------------
def _prep_X_from_plazos() -> Tuple[pd.DataFrame, List[str], pd.DataFrame]:
    """Carga plazos, enriquece con docs, devuelve df con columnas numericas limpias."""
    payload = fetch_plazos()
    df_plazos = flatten_plazos(payload)
    if df_plazos.empty:
        return pd.DataFrame(), [], df_plazos

    df, num_feats = enrich_plazos_with_docs(df_plazos)
    if df.empty:
        return pd.DataFrame(), [], df_plazos

    # Tomar solo features numéricas (ya vienen en num_feats); rellenar NaN con 0.0
    X = df[num_feats].copy().astype(float).fillna(0.0)

    # Filtrar columnas sin varianza para evitar inestabilidad
    stds = X.std(ddof=0)
    keep = stds[stds > 1e-8].index.tolist()
    X = X[keep]
    return X, keep, df


def _prep_X_from_docs() -> Tuple[pd.DataFrame, List[str], pd.DataFrame]:
    """Carga docs, crea features simples para DL."""
    docs = fetch_docs()
    df = flatten_docs(docs)
    if df.empty:
        return pd.DataFrame(), [], df

    # Features sencillas para empezar
    df["name_len"] = df["filename"].astype(str).str.len().astype(float)
    df["is_pdf"] = (df["file_ext"].str.lower() == "pdf").astype(float)

    num_feats = ["days_since_created", "name_len", "is_pdf"]
    # Asegurar que existen
    for c in num_feats:
        if c not in df.columns:
            df[c] = 0.0

    X = df[num_feats].copy().astype(float).fillna(0.0)

    stds = X.std(ddof=0)
    keep = stds[stds > 1e-8].index.tolist()
    X = X[keep]
    return X, keep, df


def _scale_fit_transform(X: pd.DataFrame) -> Tuple[np.ndarray, StandardScaler]:
    scaler = StandardScaler(with_mean=True, with_std=True)
    Xs = scaler.fit_transform(X.values.astype(float))
    return Xs, scaler


# -----------------------------
# Modelo Autoencoder - PyTorch
# -----------------------------
class AE(nn.Module):
    def __init__(self, d_in: int, h: int, bottleneck: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(d_in, h),
            nn.ReLU(),
            nn.Linear(h, bottleneck),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck, h),
            nn.ReLU(),
            nn.Linear(h, d_in),
        )

    def forward(self, x):
        z = self.encoder(x)
        out = self.decoder(z)
        return out


def _train_ae_torch(Xs: np.ndarray, hidden: int, bottleneck: int, epochs: int, lr: float) -> Tuple[np.ndarray, float]:
    """
    Entrena un autoencoder en PyTorch (CPU). Devuelve:
    - errores de reconstrucción por fila (MSE)
    - loss final
    """
    device = torch.device("cpu")
    X_tensor = torch.tensor(Xs, dtype=torch.float32, device=device)

    d = Xs.shape[1]
    model = AE(d_in=d, h=hidden, bottleneck=bottleneck).to(device)
    opt = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        out = model(X_tensor)
        loss = loss_fn(out, X_tensor)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        recon = model(X_tensor).cpu().numpy()
    errs = ((Xs - recon) ** 2).mean(axis=1)
    return errs, float(loss.item())


def _train_ae_sklearn(Xs: np.ndarray, hidden: int, bottleneck: int, epochs: int, lr: float) -> Tuple[np.ndarray, float]:
    """
    Fallback con sklearn: usamos MLPRegressor para "reconstruir" X->X
    Arquitectura simétrica [hidden, bottleneck, hidden] con activación ReLU.
    """
    # Nota: MLPRegressor no expone loss final de forma directa; estimamos con MSE luego.
    # max_iter ~ epochs, learning_rate_init ~ lr
    mlp = MLPRegressor(
        hidden_layer_sizes=(hidden, bottleneck, hidden),
        activation="relu",
        solver="adam",
        learning_rate_init=lr,
        max_iter=max(epochs, 50),
        random_state=42,
    )
    mlp.fit(Xs, Xs)
    recon = mlp.predict(Xs)
    errs = ((Xs - recon) ** 2).mean(axis=1)
    # "loss final" aproximado
    loss = float(errs.mean())
    return errs, loss


def _run_autoencoder(X: pd.DataFrame, features: List[str], epochs: int, hidden: int, bottleneck: int, lr: float) -> Dict[str, Any]:
    if X.empty or len(features) == 0:
        return {"status": "sin_datos", "detail": "No hay features válidas (varianza ~0 o dataset vacío)."}

    # Escalar
    Xs, scaler = _scale_fit_transform(X)

    # Entrenar
    if HAS_TORCH:
        errs, loss = _train_ae_torch(Xs, hidden=hidden, bottleneck=bottleneck, epochs=epochs, lr=lr)
        backend = "torch"
    else:
        errs, loss = _train_ae_sklearn(Xs, hidden=hidden, bottleneck=bottleneck, epochs=epochs, lr=lr)
        backend = "sklearn-fallback"

    # Normalizar scores a [0,1] para presentación
    e_min, e_max = float(errs.min()), float(errs.max())
    denom = (e_max - e_min) if e_max > e_min else 1e-12
    scores = (errs - e_min) / denom

    return {
        "backend": backend,
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "features": features,
        "train_loss": loss,
        "errors_raw_mean": float(errs.mean()),
        "scores_min": float(scores.min()),
        "scores_max": float(scores.max()),
        "scores": scores.tolist(),  # (orden corresponde a X.index)
    }


# -----------------------------
# Endpoints Deep
# -----------------------------

@router.get("/plazos/autoencoder")
def deep_plazos_autoencoder(
    epochs: int = Query(120, ge=20, le=2000, description="Épocas de entrenamiento"),
    hidden: int = Query(8, ge=2, le=128, description="Neuronas capa oculta"),
    bottleneck: int = Query(3, ge=1, le=64, description="Dimensión del embebido"),
    lr: float = Query(1e-2, gt=0, le=1e-1, description="Learning rate"),
    top: int = Query(20, ge=1, description="Cuántos casos devolver ordenados por score"),
) -> Dict[str, Any]:
    """
    Autoencoder de plazos (features numéricas de enrich_plazos_with_docs).
    Devuelve los casos con **mayor score** (peor reconstrucción) como posibles **anomalías**.
    """
    X, feats, df = _prep_X_from_plazos()
    out = _run_autoencoder(X, feats, epochs=epochs, hidden=hidden, bottleneck=bottleneck, lr=lr)
    if out.get("status") == "sin_datos":
        return out

    # Armar salida ordenada por score desc
    scores = np.array(out["scores"])
    order = np.argsort(-scores)
    order = order[: min(top, len(order))]

    rows = []
    base_cols = ["id_plazo", "expediente_id", "descripcion"]
    for c in base_cols:
        if c not in df.columns:
            df[c] = None

    for idx in order:
        r = {
            "id_plazo": int(df.iloc[idx]["id_plazo"]) if pd.notna(df.iloc[idx]["id_plazo"]) else None,
            "expediente_id": int(df.iloc[idx]["expediente_id"]) if ("expediente_id" in df.columns and pd.notna(df.iloc[idx]["expediente_id"])) else None,
            "descripcion": df.iloc[idx].get("descripcion"),
            "deep_anomaly_score": float(scores[idx]),
            "features": {f: float(X.iloc[idx][f]) for f in feats},
        }
        rows.append(r)

    return {
        "status": "ok",
        "task": "plazos_autoencoder",
        **{k: v for k, v in out.items() if k not in ["scores"]},
        "top": rows,
    }


@router.get("/docs/autoencoder")
def deep_docs_autoencoder(
    epochs: int = Query(120, ge=20, le=2000),
    hidden: int = Query(8, ge=2, le=128),
    bottleneck: int = Query(2, ge=1, le=64),
    lr: float = Query(1e-2, gt=0, le=1e-1),
    top: int = Query(20, ge=1),
) -> Dict[str, Any]:
    """
    Autoencoder de documentos (features simples: days_since_created, name_len, is_pdf).
    Señala documentos “raros” por su vector de features.
    """
    X, feats, df = _prep_X_from_docs()
    out = _run_autoencoder(X, feats, epochs=epochs, hidden=hidden, bottleneck=bottleneck, lr=lr)
    if out.get("status") == "sin_datos":
        return out

    scores = np.array(out["scores"])
    order = np.argsort(-scores)
    order = order[: min(top, len(order))]

    rows = []
    base_cols = ["doc_id", "filename", "file_ext", "id_expediente", "id_cliente"]
    for c in base_cols:
        if c not in df.columns:
            df[c] = None

    for idx in order:
        r = {
            "doc_id": df.iloc[idx].get("doc_id"),
            "filename": df.iloc[idx].get("filename"),
            "file_ext": df.iloc[idx].get("file_ext"),
            "id_expediente": int(df.iloc[idx]["id_expediente"]) if pd.notna(df.iloc[idx]["id_expediente"]) else None,
            "id_cliente": int(df.iloc[idx]["id_cliente"]) if pd.notna(df.iloc[idx]["id_cliente"]) else None,
            "deep_anomaly_score": float(scores[idx]),
            "features": {f: float(X.iloc[idx][f]) for f in feats},
        }
        rows.append(r)

    return {
        "status": "ok",
        "task": "docs_autoencoder",
        **{k: v for k, v in out.items() if k not in ["scores"]},
        "top": rows,
    }
