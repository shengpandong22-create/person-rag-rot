from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from pydantic import BaseModel, Field

from agent_mentor.application.knowledge_service import KnowledgeService
from agent_mentor.domain.knowledge import TrustLevel
from agent_mentor.infrastructure.database.models import KnowledgeBaseModel, SourceDocumentModel

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)


class KnowledgeBaseResponse(BaseModel):
    id: UUID
    name: str
    description: str | None


class DocumentResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    original_filename: str
    version: int
    status: str
    is_active: bool
    error_message: str | None


def base_response(item: KnowledgeBaseModel) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(id=item.id, name=item.name, description=item.description)


def document_response(item: SourceDocumentModel) -> DocumentResponse:
    return DocumentResponse(
        id=item.id,
        knowledge_base_id=item.knowledge_base_id,
        original_filename=item.original_filename,
        version=item.version,
        status=str(item.status),
        is_active=item.is_active,
        error_message=item.error_message,
    )


def service(request: Request) -> KnowledgeService:
    return request.app.state.knowledge_service


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate, request: Request
) -> KnowledgeBaseResponse:
    return base_response(await service(request).create_base(payload.name, payload.description))


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(request: Request) -> list[KnowledgeBaseResponse]:
    return [base_response(item) for item in await service(request).list_bases()]


@router.get("/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(knowledge_base_id: UUID, request: Request) -> KnowledgeBaseResponse:
    return base_response(await service(request).get_base(knowledge_base_id))


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_documents(knowledge_base_id: UUID, request: Request) -> list[DocumentResponse]:
    return [
        document_response(item) for item in await service(request).list_documents(knowledge_base_id)
    ]


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentResponse,
    status_code=202,
)
async def upload_document(
    knowledge_base_id: UUID,
    request: Request,
    tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    trust_level: Annotated[TrustLevel, Form()] = TrustLevel.UNKNOWN,
    source_url: Annotated[str | None, Form()] = None,
    author: Annotated[str | None, Form()] = None,
) -> DocumentResponse:
    document, duplicate = await service(request).add_document(
        knowledge_base_id,
        file.filename or "upload",
        await file.read(),
        trust_level,
        source_url,
        author,
    )
    if not duplicate:
        tasks.add_task(service(request).ingest, document.id)
    return document_response(document)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, request: Request) -> DocumentResponse:
    return document_response(await service(request).get_document(document_id))


@router.post("/documents/{document_id}/reindex", response_model=DocumentResponse, status_code=202)
async def reindex_document(
    document_id: UUID, request: Request, tasks: BackgroundTasks
) -> DocumentResponse:
    document = await service(request).get_document(document_id)
    tasks.add_task(service(request).ingest, document.id)
    return document_response(document)


@router.delete("/documents/{document_id}", status_code=204)
async def archive_document(document_id: UUID, request: Request) -> None:
    await service(request).archive_document(document_id)
