from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.domain.knowledge import DocumentStatus, TrustLevel
from agent_mentor.infrastructure.database.models import (
    KnowledgeBaseModel,
    KnowledgeChunkModel,
    SourceDocumentModel,
)
from agent_mentor.ports.embedding_gateway import EmbeddingGateway
from agent_mentor.rag.chunking import chunk_sections
from agent_mentor.rag.documents import DocumentParser

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class KnowledgeService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        parser: DocumentParser,
        embedding: EmbeddingGateway,
        storage: Path,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int,
        max_upload_mb: int,
    ) -> None:
        self._sessions, self._parser, self._embedding = sessions, parser, embedding
        self._storage, self._chunk_size, self._chunk_overlap, self._batch_size = (
            storage.resolve(),
            chunk_size,
            chunk_overlap,
            batch_size,
        )
        self._max_upload_bytes = max_upload_mb * 1024 * 1024

    async def create_base(self, name: str, description: str | None) -> KnowledgeBaseModel:
        now = datetime.now(UTC)
        base = KnowledgeBaseModel(
            id=uuid4(),
            user_id=DEFAULT_USER_ID,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        async with self._sessions() as session:
            session.add(base)
            await session.commit()
            await session.refresh(base)
        return base

    async def list_bases(self) -> list[KnowledgeBaseModel]:
        async with self._sessions() as session:
            return list(
                (
                    await session.scalars(
                        select(KnowledgeBaseModel).order_by(KnowledgeBaseModel.created_at.desc())
                    )
                ).all()
            )

    async def get_base(self, base_id: UUID) -> KnowledgeBaseModel:
        async with self._sessions() as session:
            base = await session.get(KnowledgeBaseModel, base_id)
            if base is None:
                raise AppError("KNOWLEDGE_BASE_NOT_FOUND", "Knowledge base was not found.", 404)
            return base

    async def list_documents(self, base_id: UUID) -> list[SourceDocumentModel]:
        await self.get_base(base_id)
        async with self._sessions() as session:
            return list(
                (
                    await session.scalars(
                        select(SourceDocumentModel)
                        .where(SourceDocumentModel.knowledge_base_id == base_id)
                        .order_by(SourceDocumentModel.created_at.desc())
                    )
                ).all()
            )

    async def add_document(
        self,
        base_id: UUID,
        filename: str,
        content: bytes,
        trust: TrustLevel,
        source_url: str | None,
        author: str | None,
    ) -> tuple[SourceDocumentModel, bool]:
        await self.get_base(base_id)
        if len(content) > self._max_upload_bytes:
            raise AppError("UPLOAD_TOO_LARGE", "Document exceeds the configured upload limit.")
        suffix = Path(filename).suffix.lower()
        if suffix not in DocumentParser.supported_extensions:
            raise AppError(
                "UNSUPPORTED_DOCUMENT", "Only Markdown, TXT, PDF and DOCX are supported."
            )
        safe_name = Path(filename).name
        digest = hashlib.sha256(content).hexdigest()
        logical_name = Path(safe_name).stem
        async with self._sessions() as session:
            duplicate = await session.scalar(
                select(SourceDocumentModel).where(
                    SourceDocumentModel.knowledge_base_id == base_id,
                    SourceDocumentModel.content_hash == digest,
                )
            )
            if duplicate:
                return duplicate, True
            prior = list(
                (
                    await session.scalars(
                        select(SourceDocumentModel).where(
                            SourceDocumentModel.knowledge_base_id == base_id,
                            SourceDocumentModel.logical_name == logical_name,
                            SourceDocumentModel.is_active.is_(True),
                        )
                    )
                ).all()
            )
            for item in prior:
                item.is_active = False
            version = max((item.version for item in prior), default=0) + 1
            now = datetime.now(UTC)
            document = SourceDocumentModel(
                id=uuid4(),
                knowledge_base_id=base_id,
                title=logical_name,
                logical_name=logical_name,
                original_filename=safe_name,
                storage_path="",
                source_url=source_url,
                author=author,
                trust_level=trust,
                content_hash=digest,
                version=version,
                status=DocumentStatus.PENDING,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            path = self._storage / str(base_id) / str(document.id) / safe_name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            document.storage_path = str(path.relative_to(self._storage))
            session.add(document)
            await session.commit()
            await session.refresh(document)
            return document, False

    async def ingest(self, document_id: UUID) -> None:
        try:
            async with self._sessions() as session:
                document = await session.get(SourceDocumentModel, document_id)
                if document is None:
                    return
                document.status, document.error_message = DocumentStatus.PROCESSING, None
                await session.commit()
                data = (self._storage / document.storage_path).read_bytes()
                filename = document.original_filename
            drafts = chunk_sections(
                self._parser.parse(filename, data), self._chunk_size, self._chunk_overlap
            )
            vectors: list[list[float]] = []
            for start in range(0, len(drafts), self._batch_size):
                vectors.extend(
                    await self._embedding.embed_documents(
                        [draft.content for draft in drafts[start : start + self._batch_size]]
                    )
                )
            async with self._sessions() as session:
                document = await session.get(SourceDocumentModel, document_id)
                if document is None:
                    return
                await session.execute(
                    delete(KnowledgeChunkModel).where(
                        KnowledgeChunkModel.document_id == document_id
                    )
                )
                for draft, vector in zip(drafts, vectors, strict=True):
                    session.add(
                        KnowledgeChunkModel(
                            id=uuid4(),
                            document_id=document_id,
                            content=draft.content,
                            heading_path=draft.heading_path,
                            page_number=draft.page_number,
                            chunk_index=draft.chunk_index,
                            token_count=draft.token_count,
                            embedding=vector,
                            search_text=None,
                            created_at=datetime.now(UTC),
                        )
                    )
                await session.flush()
                from sqlalchemy import text

                await session.execute(
                    text(
                        "UPDATE knowledge_chunks "
                        "SET search_text = to_tsvector('simple', content) "
                        "WHERE document_id = :document_id"
                    ),
                    {"document_id": document_id},
                )
                document.status = DocumentStatus.READY
                await session.commit()
        except Exception as error:
            async with self._sessions() as session:
                document = await session.get(SourceDocumentModel, document_id)
                if document:
                    document.status, document.error_message = (
                        DocumentStatus.FAILED,
                        str(error)[:1000],
                    )
                    await session.commit()

    async def get_document(self, document_id: UUID) -> SourceDocumentModel:
        async with self._sessions() as session:
            document = await session.get(SourceDocumentModel, document_id)
            if document is None:
                raise AppError("DOCUMENT_NOT_FOUND", "Document was not found.", 404)
            return document

    async def archive_document(self, document_id: UUID) -> None:
        async with self._sessions() as session:
            document = await session.get(SourceDocumentModel, document_id)
            if document is None:
                raise AppError("DOCUMENT_NOT_FOUND", "Document was not found.", 404)
            document.status, document.is_active = DocumentStatus.ARCHIVED, False
            await session.commit()
