from typing import Optional, List, Tuple, Dict, Any
import math
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from .features import today_local

MIN_TRAIN_ROWS = 5
RANDOM_STATE = 42

def build_train_labels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    def label_row(row):
        fv = row["fecha_vencimiento"]   # Timestamp o NaT
        fc = row["fecha_cumplimiento"]  # Timestamp o NaT
        cumplido = row["cumplido"]
        todayd = pd.Timestamp.now().normalize()

        if cumplido:
            if pd.isna(fc) or pd.isna(fv):
                return None
            return 1 if fc > fv else 0
        else:
            if pd.isna(fv):
                return None
            return 1 if todayd > fv else None

    y = df.apply(label_row, axis=1)
    df_lab = df.copy()
    df_lab["y"] = y
    df_lab = df_lab[~df_lab["y"].isna()]
    df_lab["y"] = df_lab["y"].astype(int)
    return df_lab
def build_supervised_pipeline(num_feats: List[str]) -> Pipeline:
    text_feat = "descripcion"

    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ("scaler", StandardScaler(with_mean=False)),
    ])

    pre = ColumnTransformer(
        transformers=[
            ("txt", TfidfVectorizer(max_features=500, ngram_range=(1, 2)), text_feat),
            ("num", num_pipe, num_feats),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )

    clf = LogisticRegression(max_iter=200, random_state=42, class_weight="balanced")
    return Pipeline([("pre", pre), ("clf", clf)])
def ensure_supervised_model(df: pd.DataFrame, num_feats: List[str]) -> Tuple[Optional[Pipeline], str]:
    df_lab = build_train_labels(df)
    if df_lab.shape[0] < MIN_TRAIN_ROWS:
        return None, f"No hay suficientes datos etiquetados para entrenar (tengo {df_lab.shape[0]}/{MIN_TRAIN_ROWS}). Se usará una heurística."
    X = df_lab[["descripcion"] + num_feats]
    y = df_lab["y"]
    pipe = build_supervised_pipeline(num_feats)
    pipe.fit(X, y)
    return pipe, f"Modelo entrenado con {len(y)} ejemplos (balance={y.mean():.2f} positivos)."

def heuristic_risk(days_to_due: Optional[float]) -> float:
    if days_to_due is None or pd.isna(days_to_due):
        return 0.5
    return 1.0 / (1.0 + math.exp(0.5 * days_to_due))

def score_supervised(df: pd.DataFrame, model: Optional[Pipeline], num_feats: List[str]) -> List[Dict[str, Any]]:
    rows = []
    if df.empty:
        return rows
    X_all = df[["descripcion"] + num_feats]
    if model is not None:
        proba = model.predict_proba(X_all)[:, 1]
    else:
        proba = df["days_to_due"].apply(heuristic_risk).values
    for idx, r in df.iterrows():
        risk = float(proba[idx])
        recomendacion = "ALTA" if risk >= 0.66 else "MEDIA" if risk >= 0.33 else "BAJA"
        rows.append({
            "id_plazo": int(r["id_plazo"]),
            "expediente_id": int(r["expediente_id"]) if pd.notna(r["expediente_id"]) else None,
            "descripcion": r["descripcion"],
            "days_to_due": int(r["days_to_due"]) if pd.notna(r["days_to_due"]) else None,
            "overdue_now": bool(r["overdue_now"]),
            "docs_count_exp": int(r["docs_count_exp"]) if "docs_count_exp" in r and pd.notna(r["docs_count_exp"]) else 0,
            "riesgo_atraso": round(risk, 4),
            "prioridad_recomendada": recomendacion,
        })
    return rows

def build_unsupervised_features(df: pd.DataFrame, num_feats: List[str]):
    text = df["descripcion"].fillna("")
    tfidf = TfidfVectorizer(max_features=500, ngram_range=(1,2))
    X_text = tfidf.fit_transform(text)
    num = df[num_feats].fillna(0)
    scaler = StandardScaler(with_mean=False)
    X_num = scaler.fit_transform(num)
    from scipy.sparse import hstack
    X = hstack([X_text, X_num])
    return X, tfidf, scaler, num

def kmeans_labels(X, k: int):
    km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE)
    return km.fit_predict(X)

def isolation_forest_flags(X):
    iso = IsolationForest(n_estimators=200, contamination="auto", random_state=RANDOM_STATE)
    return iso.fit_predict(X)  # -1 anomalía, 1 normal

def near_duplicate_pairs(names: pd.Series, sizes_mb: pd.Series, threshold: float, max_pairs: int):
    tfidf = TfidfVectorizer(max_features=1000, ngram_range=(1,2))
    X = tfidf.fit_transform(names.fillna(""))
    sim = cosine_similarity(X)
    pairs = []
    n = sim.shape[0]
    for i in range(n):
        for j in range(i+1, n):
            s = float(sim[i,j])
            if s >= threshold:
                si = float(sizes_mb.iloc[i] or 0.0)
                sj = float(sizes_mb.iloc[j] or 0.0)
                size_ok = True
                if si > 0 and sj > 0:
                    size_ok = (min(si, sj) / max(si, sj)) >= 0.9
                if size_ok:
                    pairs.append((i, j, s))
            if len(pairs) >= max_pairs:
                return pairs
    return pairs
