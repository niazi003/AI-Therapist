"""FastAPI main application."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.routers import health, auth, consent, chat, memory, appointments, location

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Personal AI wellbeing companion backend",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix=settings.API_V1_PREFIX)
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(consent.router, prefix=settings.API_V1_PREFIX)
    app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
    app.include_router(memory.router, prefix=settings.API_V1_PREFIX)
    app.include_router(appointments.router, prefix=settings.API_V1_PREFIX)
    app.include_router(location.router, prefix=settings.API_V1_PREFIX)
    
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        from app.services.graph_store import close_store, initialize_store
        from app.services.langgraph_therapy import initialize_therapy_graph
        await initialize_store()
        try:
            await initialize_therapy_graph()
        except Exception:
            await close_store()
            raise
        logger.info("PostgreSQL LangGraph Store and therapy graph initialized")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        from app.services.langgraph_therapy import close_therapy_graph
        from app.services.graph_store import close_store
        try:
            await close_therapy_graph()
        finally:
            await close_store()
        logger.info(f"Shutting down {settings.APP_NAME}")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )