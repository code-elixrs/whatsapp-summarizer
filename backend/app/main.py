import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.middleware.error_handler import ErrorHandlerMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="LifeLog",
        description="Personal media & communication organizer",
        version="0.1.0",
    )

    application.add_middleware(ErrorHandlerMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)
    return application


app = create_app()
