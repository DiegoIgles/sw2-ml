
# ML Plazos Service – FastAPI (Supervisado, No Supervisado y Deep Learning)

Servicio **FastAPI** que consume tus endpoints de **plazos** y **documentos** para ofrecer:
- **Aprendizaje Supervisado**: predicción de **riesgo de atraso** por plazo (Regresión Logística con *fallback* heurístico).
- **No Supervisado**: **clustering (K‑Means)** y **detección de anomalías (IsolationForest)** en plazos y documentos.
- **Modelos Lineales**: regresión lineal para días al vencimiento (plazos) y tamaño estimado (docs).
- **Deep Learning**: **Autoencoders** (PyTorch) para **anomalías** en plazos y documentos.

> Diseñado para funcionar con tus endpoints existentes:
> - `PLAZOS_ENDPOINT` → por ejemplo `http://localhost:3000/plazos`
> - `DOCS_ENDPOINT` → por ejemplo `http://localhost:8081/admin/documentos`

---

## Tabla de contenidos
1. [Arquitectura y estructura](#arquitectura-y-estructura)
2. [Requisitos](#requisitos)
3. [Instalación](#instalación)
4. [Configuración](#configuración)
5. [Ejecución](#ejecución)
6. [Endpoints](#endpoints)
   - [Supervisado (riesgo de atraso)](#supervisado-riesgo-de-atraso)
   - [No supervisado (plazos)](#no-supervisado-plazos)
   - [No supervisado (documentos)](#no-supervisado-documentos)
   - [Regresión lineal](#regresión-lineal)
   - [Deep Learning (autoencoders)](#deep-learning-autoencoders)
7. [Ingeniería de características (features)](#ingeniería-de-características-features)
8. [Notas técnicas y troubleshooting](#notas-técnicas-y-troubleshooting)
9. [Buenas prácticas y tamaños mínimos de datos](#buenas-prácticas-y-tamaños-mínimos-de-datos)
10. [Extensiones futuras](#extensiones-futuras)
11. [Licencia](#licencia)

---

## Arquitectura y estructura

```
ml-plazos-service/
├─ app/
│  ├─ main.py                      # FastAPI app y registro de routers
│  ├─ clients.py                   # Clientes HTTP: fetch_plazos / fetch_docs
│  ├─ features.py                  # Flatten, agregaciones y enriquecimiento
│  ├─ models.py                    # Modelos supervisados utilitarios
│  └─ routers/
│     ├─ supervisado.py            # /ml/supervisado/*
│     ├─ no_supervisado.py         # /ml/no_supervisado/*
│     ├─ docs_no_supervisado.py    # /docs/no_supervisado/* y /docs/near_duplicados
│     ├─ lineal.py                 # /ml/lineal/*
│     └─ deep.py                   # /ml/deep/*
├─ requirements.txt
├─ .env.example
└─ README.md
```

> **Nota**: Si algún archivo no existe aún, usa los nombres indicados para mantener esta organización.

---

## Requisitos

- **Python 3.13** (recomendado, compatible con las ruedas binarias usadas).
- **Pip** actualizado: `python -m pip install --upgrade pip`
- **Windows**: se recomienda instalar ruedas binarias para evitar compilar `pandas/numpy/scipy`.
- **Conexión** a tus servicios de backend (plazos y documentos).

---

## Instalación

### 1) Crear y activar entorno virtual
```bash
python -m venv .venv
# PowerShell
. .venv/Scripts/Activate.ps1
# Git Bash / MINGW64
source .venv/Scripts/activate
```

### 2) Instalar dependencias
**Opción A (recomendada en Windows / Py3.13): solo ruedas binarias**
```bash
pip install --only-binary=:all: -r requirements.txt
```

**Opción B (normal)**
```bash
pip install -r requirements.txt
```

### 3) Instalar PyTorch CPU (Deep Learning)
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## Configuración

Crea un archivo `.env` (o exporta variables de entorno) con tus endpoints:

```dotenv
# .env
PLAZOS_ENDPOINT=http://localhost:3000/plazos
DOCS_ENDPOINT=http://localhost:8081/admin/documentos
```

> Alternativas en **PowerShell** (temporal para la sesión):
>
> ```powershell
> $env:PLAZOS_ENDPOINT="http://localhost:3000/plazos"
> $env:DOCS_ENDPOINT="http://localhost:8081/admin/documentos"
> ```
>
> En **Git Bash**:
> ```bash
> export PLAZOS_ENDPOINT=http://localhost:3000/plazos
> export DOCS_ENDPOINT=http://localhost:8081/admin/documentos
> ```

---

## Ejecución

```bash
uvicorn app.main:app --reload --port 8010
# App: http://127.0.0.1:8010
```

---

## Endpoints

### Supervisado (riesgo de atraso)
Predice `riesgo_atraso` para cada plazo. Usa **Regresión Logística** cuando hay suficientes etiquetas heurísticas; si no, cae a una **heurística** interpretable.

- **GET** `/ml/supervisado/prob_riesgo`  
  **Ejemplo (cURL):**
  ```bash
  curl "http://localhost:8010/ml/supervisado/prob_riesgo"
  ```
  **Respuesta (extracto):**
  ```json
  {
    "status": "ok | fallback",
    "total": 6,
    "data": [
      {
        "id_plazo": 5,
        "expediente_id": 1,
        "descripcion": "Presentar memorial",
        "days_to_due": 0,
        "overdue_now": false,
        "docs_count_exp": 1,
        "riesgo_atraso": 0.3775,
        "prioridad_recomendada": "MEDIA"
      }
    ]
  }
  ```

### No supervisado (plazos)
- **GET** `/ml/no_supervisado/clusters?k=3` (K-Means)
  ```bash
  curl "http://localhost:8010/ml/no_supervisado/clusters?k=3"
  ```
- **GET** `/ml/no_supervisado/anomalias?contaminacion=0.15&max_lista=50` (IsolationForest)
  ```bash
  curl "http://localhost:8010/ml/no_supervisado/anomalias"
  ```

### No supervisado (documentos)
- **GET** `/docs/no_supervisado/clusters?k=3`
  ```bash
  curl "http://localhost:8010/docs/no_supervisado/clusters?k=3"
  ```
- **GET** `/docs/no_supervisado/anomalias`
  ```bash
  curl "http://localhost:8010/docs/no_supervisado/anomalias"
  ```
- **GET** `/docs/near_duplicados?threshold=0.85&max_pairs=50`  
  Detección de **casi duplicados** por similitud de nombre y tamaño aproximado.
  ```bash
  curl "http://localhost:8010/docs/near_duplicados?threshold=0.85&max_pairs=50"
  ```

### Regresión lineal
Estimaciones interpretables con **LinearRegression** (imputer + escaler).

- **GET** `/ml/lineal/plazos`  
  Estima `days_to_due` **sin leakage** (usa features de contenido, no la propia `days_to_due`).
  ```bash
  curl "http://localhost:8010/ml/lineal/plazos"
  ```
- **GET** `/ml/lineal/docs`  
  Estima `size_mb` en documentos a partir de `days_since_created`, `name_len`, `is_pdf`.
  ```bash
  curl "http://localhost:8010/ml/lineal/docs"
  ```

### Deep Learning (autoencoders)
**PyTorch** autoencoders para **anomalías** (score 0–1).

- **GET** `/ml/deep/plazos/autoencoder?epochs=150&hidden=8&bottleneck=3&lr=0.01`
  ```bash
  curl "http://localhost:8010/ml/deep/plazos/autoencoder"
  ```
- **GET** `/ml/deep/docs/autoencoder?epochs=150&hidden=8&bottleneck=2&lr=0.01`
  ```bash
  curl "http://localhost:8010/ml/deep/docs/autoencoder"
  ```

---

## Ingeniería de características (features)

**Plazos (desde `/plazos`)**
- `days_to_due`: días hasta vencimiento (clamped ≥ 0 cuando toca).
- `desc_len`: longitud de la descripción.
- `estado_abierto`: 1 si expediente abierto, 0 en caso contrario.
- `overdue_now`: flag interno (no entra siempre como feature).

**Documentos (desde `/admin/documentos`)**
- `days_since_created`: días desde creación (clamped ≥ 0).
- `name_len`: longitud del nombre de archivo.
- `is_pdf`: 1 si extensión `.pdf`.
- Agregados por expediente (para plazos): `docs_count_exp`, `docs_total_size_mb`, `days_since_last_doc`, `recent_docs_7d`, `pdf_ratio_exp`.

> Se cuidan conversiones de fecha a `datetime64[ns]` y normalizaciones para evitar errores tz‑naive/aware.

---

## Notas técnicas y troubleshooting

- **Windows + Py3.13**: usa `pip install --only-binary=:all:` para evitar compilar `pandas/numpy/scipy`.
- **PyTorch CPU**: `pip install torch --index-url https://download.pytorch.org/whl/cpu`.
- **Error tz‑naive vs tz‑aware**: resuelto homogenizando a `datetime64[ns]` **naive** y `clip(lower=0)` para días negativos.
- **`Input X contains NaN` (sklearn)**: los pipelines incluyen **imputer**; además se hace `fillna(0.0)` en features numéricas.
- **`Not Found`** en rutas: verifica que el archivo y el `prefix` del router coincidan (`no_supervisado.py` vs `nospervisado.py`).  
- **Lanzar app**: `uvicorn app.main:app --reload --port 8010`
- **Variables**: si cambias endpoints, actualiza `.env` o variables de entorno.

---

## Buenas prácticas y tamaños mínimos de datos

- **Supervisado** (riesgo de atraso): mínimo **5–20** con etiquetas heurísticas para demo; ideal **100+** con etiquetas reales.
- **No supervisado** (K‑Means/IForest): usable desde **30–50**; mejor **100–200+**.
- **Lineal**: funciona desde **n≈5–10** (overfit alto); mejor **50–100+**.
- **Deep (Autoencoder)**: demostra ble con **n≈30–50**; recomendable **200+** para estabilidad.

Reproducibilidad: fija semillas (`numpy`, `torch`) y documenta hiperparámetros (epochs, hidden, bottleneck, lr).

---

## Extensiones futuras

- Etiquetado real de “atraso” (no solo heurística) y retraining periódico.
- Métricas de validación para deep (p. ej., comparar distribución de `deep_anomaly_score` entre semanas).
- Explicabilidad: devolver **top‑3 errores por feature** en autoencoders.
- Umbral operativo en anomalías por percentil (p. ej., 95%).

---

## Licencia

Proyecto académico/demostrativo. Ajusta la licencia según tus necesidades (MIT/Apache 2.0, etc.).

---

### Créditos
Implementado por **Ingeniero** con FastAPI, scikit‑learn y PyTorch (CPU).
