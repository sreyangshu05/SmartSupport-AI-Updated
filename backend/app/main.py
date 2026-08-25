"""SmartSupport AI — FastAPI application entrypoint."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.ratelimit import RateLimitMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("smartsupport")
settings = get_settings()

APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SmartSupport AI backend starting (env=%s)", settings.ENV)
    yield
    logger.info("SmartSupport AI backend shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "status": "ok",
        "health": "/api/health",
        "docs": "/docs",
    }


# Sliding-window rate limiting (disabled automatically in test env).
app.add_middleware(RateLimitMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "requestId": getattr(request.state, "request_id", None),
            }
        },
    )


# Root API health-mirror so /api/health also works under the prefix.
app.include_router(api_router, prefix=settings.API_PREFIX)
