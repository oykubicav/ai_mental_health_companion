"""CBT chatbot API — FastAPI app.

Startup:
  - Structured JSON logging
  - Preload cards + rules so first request is fast
  - Optional slowapi rate limiter (if installed)
  - CORS for local frontend + configurable prod origin
  - Request-ID middleware

Endpoints:
  /health              GET   — liveness
  /readyz              GET   — readiness (cards + rules + LLM key)
  /chat                POST  — main pipeline
  /chat/session/{id}   DELETE — KVKK: kullanıcı silme
  /cards               GET   — CBT card list
  /cards/topics        GET   — topics + counts
  /cards/{card_id}     GET   — single CBT card
  /cards/safety        GET   — safety cards (admin)
  /cards/safety/{id}   GET   — single safety card (admin)
  /feedback            POST  — thumbs up/down
  /eval/run            POST  — trigger async eval (admin)
  /eval/results/{id}   GET   — eval status/summary (admin)
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import __version__
from api.logging_setup import setup_logging, get_logger
from api.middleware.request_id import RequestIdMiddleware
from api.routes import health, chat, cards, feedback, consent,assessments,transparency,auth,exercises,journal
from api.routes import eval as eval_route


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

setup_logging()
log = get_logger("api.main")


# ------------------------------------------------------------
# App
# ------------------------------------------------------------

app = FastAPI(
    title="CBT Knowledge Base API",
    version=__version__,
    description=(
        "Backend services for the Turkish CBT self-help platform. "
        "Wraps the offline pipeline (safety_classifier + intent_classifier + "
        "retriever + composer + output_critic) behind HTTP."
    ),
)


# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

_cors_origins = os.environ.get(
    "CBT_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

# Vercel preview URL'leri her deploy'da değişir (`xxx-oykubicavs-projects.vercel.app`).
# Explicit list + regex kombinasyonu — hem custom domain hem tüm Vercel deploy'ları.
_cors_regex = os.environ.get(
    "CBT_CORS_ORIGIN_REGEX",
    r"https://.*\.vercel\.app",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)


# ------------------------------------------------------------
# Request-ID + access log
# ------------------------------------------------------------

app.add_middleware(RequestIdMiddleware)


# ------------------------------------------------------------
# Rate limit (slowapi, optional)
# ------------------------------------------------------------

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    _limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    log.info("rate_limit_enabled", extra={"route": "startup"})
except ImportError:
    log.info("rate_limit_disabled_slowapi_not_installed", extra={"route": "startup"})


# ------------------------------------------------------------
# Global exception fallback — never leak stack traces to clients
# ------------------------------------------------------------

@app.exception_handler(Exception)
async def _unhandled_exc(request: Request, exc: Exception):
    log.exception(
        "unhandled_exception",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "route": f"{request.method} {request.url.path}",
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "internal error"},
    )


# ------------------------------------------------------------
# Startup: preload cards + rules (first request should be fast)
# ------------------------------------------------------------

@app.on_event("startup")
async def _preload():
    # DB engine — fail fast if URL is bad
    from api.db import init_engine
    init_engine()

    from api.auth.jwt_utils import secret_is_configured
    if not secret_is_configured():
        log.warning(
            "jwt_secret_missing",
            extra={"route": "startup"},
        )
    # Pipeline warm-up
    from pipeline import cards as pcards
    from pipeline import safety_rules
    pcards.all_cbt_cards()
    pcards.all_safety_cards()
    safety_rules._load_rules()

    # Embedding index'lerini burada kur. Aksi hâlde ilk kullanıcı mesajı
    # TF-IDF fit'ini (~3 sn) beklemek zorunda kalıyor; sonraki istekler
    # lru_cache'ten geliyor.
    import time
    t0 = time.time()
    from pipeline import retriever, safety_classifier
    retriever._build_card_index()
    safety_classifier._build_anchor_index()
    log.info(
        "startup_preload_done",
        extra={"route": "startup", "index_build_ms": round((time.time() - t0) * 1000)},
    )


# ------------------------------------------------------------
# Routers
# ------------------------------------------------------------

app.include_router(health.router)
app.include_router(consent.router)
app.include_router(chat.router)
app.include_router(cards.router)
app.include_router(feedback.router)
app.include_router(eval_route.router)
app.include_router(assessments.router)
app.include_router(transparency.router)
app.include_router(auth.router)
app.include_router(exercises.router)
app.include_router(journal.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "CBT API is up. See /docs for Swagger UI.",
        "version": __version__,
    }