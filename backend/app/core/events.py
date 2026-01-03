from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from app.core.database import init_db
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # TODO: Initialize Celery connection
    # TODO: Initialize Redis connection

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
