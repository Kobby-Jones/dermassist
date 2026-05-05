"""
DermAssist – FastAPI Backend
Melanoma Detection API (EfficientNet-B0, 3-class classifier)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from model_service import load_model
from routers import analyze_router, auth_router, history_router


# Startup / shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)   # create DB tables (idempotent)
    load_model()                             # pre-load EfficientNet weights
    yield


# App
app = FastAPI(
    title="DermAssist API",
    description=(
        "EfficientNet-B0 melanoma detection backend. "
        "3 classes: Melanoma · Benign Nevus · Healthy Skin. "
        "For educational use only — not a medical diagnostic device."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

origins = (
    ["*"]
    if settings.ALLOWED_ORIGINS == "*"
    else [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(analyze_router.router)
app.include_router(history_router.router)


# Health check
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "DermAssist API", "version": "2.0.0"}
