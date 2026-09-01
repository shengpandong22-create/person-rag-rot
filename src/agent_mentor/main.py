from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from agent_mentor.api.chat import router as chat_router
from agent_mentor.api.demo import router as demo_router
from agent_mentor.api.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from agent_mentor.api.evaluations import router as evaluations_router
from agent_mentor.api.health import router as health_router
from agent_mentor.api.interviews import router as interviews_router
from agent_mentor.api.knowledge import router as knowledge_router
from agent_mentor.api.profiles import router as profiles_router
from agent_mentor.application.answer_service import AnswerService
from agent_mentor.application.demo_readiness_service import DemoReadinessService
from agent_mentor.application.evaluation_service import EvaluationService
from agent_mentor.application.interview_service import InterviewService
from agent_mentor.application.knowledge_service import DEFAULT_USER_ID, KnowledgeService
from agent_mentor.application.profile_service import ProfileService
from agent_mentor.config import EmbeddingProvider, Settings, get_settings
from agent_mentor.infrastructure.bge_embedding import BgeEmbeddingGateway
from agent_mentor.infrastructure.database.session import (
    DatabaseHealthChecker,
    create_database_engine,
    create_session_factory,
)
from agent_mentor.infrastructure.embedding import DevelopmentEmbeddingGateway
from agent_mentor.infrastructure.llm import OpenAICompatibleLLMGateway
from agent_mentor.infrastructure.retriever import PostgresHybridRetriever
from agent_mentor.logging import configure_logging, trace_logging_middleware
from agent_mentor.rag.documents import DocumentParser


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await app.state.knowledge_service.recover_interrupted_ingestions()
    await app.state.knowledge_service.rebuild_coverage_catalogs()
    await app.state.profile_service.backfill_two_layer_profiles(DEFAULT_USER_ID)
    yield
    await app.state.database_engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AgentMentor API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        lifespan=lifespan,
    )
    engine = create_database_engine(settings.database_url)
    app.state.database_engine = engine
    session_factory = create_session_factory(engine)
    if settings.embedding_provider is EmbeddingProvider.BGE:
        embedding = BgeEmbeddingGateway(
            model_name=settings.embedding_model or "BAAI/bge-small-zh-v1.5",
            dimension=settings.embedding_dimension,
            batch_size=settings.embedding_batch_size,
        )
    else:
        embedding = DevelopmentEmbeddingGateway(settings.embedding_dimension)
    app.state.embedding_provider = settings.embedding_provider
    app.state.embedding_model = (
        settings.embedding_model
        if settings.embedding_provider is EmbeddingProvider.BGE
        else "development-feature-hash"
    )
    app.state.embedding_dimension = settings.embedding_dimension
    llm = None
    if settings.llm_base_url and settings.llm_api_key and settings.llm_default_model:
        llm = OpenAICompatibleLLMGateway(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            default_model=settings.llm_default_model,
        )
    app.state.llm_gateway = llm
    app.state.llm_enabled = llm is not None
    app.state.llm_model = settings.llm_default_model if llm is not None else None
    app.state.database_health_checker = DatabaseHealthChecker(session_factory)
    app.state.knowledge_service = KnowledgeService(
        session_factory,
        DocumentParser(settings.max_pdf_pages),
        embedding,
        Path(settings.document_storage_path),
        settings.chunk_size,
        settings.chunk_overlap,
        settings.embedding_batch_size,
        settings.max_upload_mb,
    )
    app.state.knowledge_retriever = PostgresHybridRetriever(
        session_factory,
        embedding,
        max_chunks_per_document=settings.retrieval_max_chunks_per_document,
    )
    app.state.answer_service = AnswerService(
        session_factory,
        app.state.knowledge_retriever,
        llm,
        default_top_k=settings.retrieval_top_k,
        default_candidate_k=settings.retrieval_candidate_k,
        min_evidence_score=settings.retrieval_min_score,
        default_model=settings.llm_default_model,
    )
    app.state.interview_service = InterviewService(
        session_factory,
        app.state.knowledge_retriever,
        llm,
        retrieval_candidate_k=settings.retrieval_candidate_k,
        default_model=settings.llm_default_model,
    )
    app.state.evaluation_service = EvaluationService(
        session_factory,
        llm,
        default_model=settings.llm_default_model,
    )
    app.state.profile_service = ProfileService(session_factory)
    app.state.demo_readiness_service = DemoReadinessService(session_factory)

    app.middleware("http")(trace_logging_middleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(health_router)
    app.include_router(knowledge_router)
    app.include_router(chat_router)
    app.include_router(interviews_router)
    app.include_router(evaluations_router)
    app.include_router(profiles_router)
    app.include_router(demo_router)

    return app


app = create_app()
