import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from backend.config import settings
from backend.routers import (
    submissions,
    cases,
    reviewers,
    evidence,
    decisions,
    appeals,
    audit_log,
    analytics,
    audit_reports,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIRSMS API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(submissions.router,          prefix="/submissions",       tags=["Submissions"])
    app.include_router(submissions.similarity_router, prefix="/similarity-reports", tags=["Similarity Reports"])
    app.include_router(cases.router,                prefix="/cases",             tags=["Cases"])
    app.include_router(reviewers.router,              prefix="/reviewers",    tags=["Reviewers"])
    app.include_router(reviewers.case_reviewers_router, prefix="/cases",        tags=["Reviewers"])
    app.include_router(evidence.router,      prefix="/cases",        tags=["Evidence"])
    app.include_router(decisions.router,     prefix="/cases",        tags=["Decisions"])
    app.include_router(appeals.router,       prefix="",              tags=["Appeals"])
    app.include_router(audit_log.router,     prefix="/audit-log",    tags=["Audit Log"])
    app.include_router(analytics.router,     prefix="/analytics",    tags=["Analytics"])
    app.include_router(audit_reports.router, prefix="/audit",        tags=["Audit Reports"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.exception_handler(OperationalError)
    async def db_exception_handler(request, exc):
        logger.error("Database connection error", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "Service unavailable"})

    return app


app = create_app()
