from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.supervisado import router as sup_router
from .routers.nosupervisado import router as nosup_router
from .routers.debug import router as dbg_router
from .routers.docs_analytics import router as docs_router
from .routers.regresion import router as reg_router
from .routers.deep import router as deep_router
app = FastAPI(
    title="ML Plazos Service",
    description="Supervisado, no supervisado (plazos y docs) y planificador.",
    version="1.0.0",
)

# CORS (ajusta dominios en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

# Rutas
app.include_router(sup_router)
app.include_router(nosup_router)
app.include_router(docs_router)
app.include_router(dbg_router)
app.include_router(docs_router)
app.include_router(reg_router)
app.include_router(deep_router) 