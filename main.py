"""
DermAssist – FastAPI Backend
CLIP-powered zero-shot skin condition analysis API
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clip_service import _load_model
from config import settings
from database import Base, engine
from routers import analyze_router, auth_router, history_router


# ── Startup / shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables (idempotent)
    Base.metadata.create_all(bind=engine)
    # Pre-load CLIP model so the first request isn't slow
    _load_model()
    yield
    # (nothing to teardown)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DermAssist API",
    description=(
        "Zero-shot CLIP-powered skin condition analysis backend. "
        "For educational use only — not a medical diagnostic device."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow Flutter app (and Swagger UI) to reach the API
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

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(analyze_router.router)
app.include_router(history_router.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "DermAssist API"}
