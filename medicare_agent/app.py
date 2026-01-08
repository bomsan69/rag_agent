"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from medicare_agent.config import settings
from medicare_agent.api.routes import router, initialize_services
from medicare_agent.utils.helpers import setup_logging
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging(settings.log_level)
    logger.info("Starting Medicare AI Chatbot...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"OpenAI Model: {settings.openai_model}")

    try:
        initialize_services()
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Medicare AI Chatbot...")


# Create FastAPI app
app = FastAPI(
    title="Medicare AI Chatbot",
    description="Citation-first, regulation-safe RAG system for Medicare Handbook",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Medicare AI Chatbot",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
