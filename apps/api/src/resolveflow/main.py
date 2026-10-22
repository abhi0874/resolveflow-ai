from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from resolveflow import __version__
from resolveflow.ai.providers import select_provider
from resolveflow.api.router import api_router
from resolveflow.core.config import Settings
from resolveflow.core.errors import register_error_handlers
from resolveflow.core.observability import RequestDiagnostics
from resolveflow.core.security import SecurityMiddleware
from resolveflow.db.session import Database
from resolveflow.documents.storage import LocalFileStorage
from resolveflow.ml.classifier import LocalTicketClassifier
from resolveflow.retrieval.provider import LocalSentenceTransformerProvider


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated app; future services belong behind application interfaces."""
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Engine/pool setup is lazy: no network connection until the first query.
        database = Database(config) if config.database_url is not None else None
        app.state.database = database
        app.state.classifier = LocalTicketClassifier(
            config.classifier_artifact_root,
            config.classifier_model_version,
            config.classifier_threshold,
        )
        app.state.ai_provider = select_provider(config)
        app.state.embeddings = LocalSentenceTransformerProvider(
            config.embedding_model_root, config.embedding_device, config.embedding_batch_size
        )
        try:
            yield
        finally:
            app.state.ai_provider.close()
            if database is not None:
                database.dispose()

    application = FastAPI(
        title="ResolveFlow AI",
        version=__version__,
        description="AI-powered customer support platform",
        docs_url="/docs" if config.docs_enabled else None,
        redoc_url="/redoc" if config.docs_enabled else None,
        openapi_url="/openapi.json" if config.docs_enabled else None,
        lifespan=lifespan,
    )
    application.state.document_storage = LocalFileStorage(config.document_storage_root)
    application.state.settings = config
    application.state.database = None
    application.add_middleware(SecurityMiddleware, upload_limit=config.document_upload_max_bytes)
    register_error_handlers(application)
    application.include_router(api_router)
    return application


def create_asgi_app(settings: Settings | None = None) -> CORSMiddleware:
    """Wrap the entire app so even unhandled-error responses receive CORS headers."""
    application = create_app(settings)
    return CORSMiddleware(
        RequestDiagnostics(application),
        allow_origins=application.state.settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )


app = create_asgi_app()
