from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_mentor.api.errors import AppError
from agent_mentor.application.coverage_catalog import sync_document_catalog
from agent_mentor.domain.knowledge import DocumentStatus, IngestionJobStatus, TrustLevel
from agent_mentor.infrastructure.database.models import (
    IngestionJobModel,
    KnowledgeBaseModel,
    KnowledgeCatalogSourceModel,
    KnowledgeChunkModel,
    QuestionCoverageModel,
    QuestionReferenceModel,
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

    async def enqueue_ingestion(
        self, document_id: UUID, *, job_type: str = "ingest"
    ) -> IngestionJobModel:
        async with self._sessions() as session:
            document = await session.get(SourceDocumentModel, document_id)
            if document is None:
                raise AppError("DOCUMENT_NOT_FOUND", "Document was not found.", 404)
            now = datetime.now(UTC)
            document.status = DocumentStatus.PENDING
            document.error_message = None
            document.updated_at = now
            job = IngestionJobModel(
                id=uuid4(),
                document_id=document_id,
                job_type=job_type,
                status=IngestionJobStatus.PENDING,
                attempt_count=0,
                error_message=None,
                created_at=now,
                updated_at=now,
                started_at=None,
                completed_at=None,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job

    async def process_ingestion_queue(self, *, limit: int = 3) -> int:
        processed = 0
        for _ in range(limit):
            async with self._sessions() as session:
                job = await session.scalar(
                    select(IngestionJobModel)
                    .where(IngestionJobModel.status == IngestionJobStatus.PENDING)
                    .order_by(IngestionJobModel.created_at, IngestionJobModel.id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                if job is None:
                    break
                document = await session.get(SourceDocumentModel, job.document_id)
                now = datetime.now(UTC)
                job.status = IngestionJobStatus.PROCESSING
                job.attempt_count += 1
                job.started_at = now
                job.updated_at = now
                if document is not None:
                    document.status = DocumentStatus.PROCESSING
                    document.error_message = None
                    document.updated_at = now
                document_id = job.document_id
                job_id = job.id
                await session.commit()

            await self.ingest(document_id)

            async with self._sessions() as session:
                job = await session.get(IngestionJobModel, job_id)
                document = await session.get(SourceDocumentModel, document_id)
                if job is None:
                    continue
                now = datetime.now(UTC)
                if document is not None and document.status == DocumentStatus.READY:
                    job.status = IngestionJobStatus.COMPLETED
                    job.error_message = None
                    job.completed_at = now
                else:
                    job.status = IngestionJobStatus.FAILED
                    job.error_message = (
                        document.error_message
                        if document is not None and document.error_message
                        else "文档摄入失败，请检查文件内容或重新索引。"
                    )
                job.updated_at = now
                await session.commit()
                processed += 1
        return processed

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
                existing_chunks = {
                    chunk.chunk_index: chunk
                    for chunk in (
                        await session.scalars(
                            select(KnowledgeChunkModel).where(
                                KnowledgeChunkModel.document_id == document_id
                            )
                        )
                    ).all()
                }
                for draft, vector in zip(drafts, vectors, strict=True):
                    chunk = existing_chunks.pop(draft.chunk_index, None)
                    if chunk is None:
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
                                is_active=True,
                                created_at=datetime.now(UTC),
                            )
                        )
                    else:
                        chunk.content = draft.content
                        chunk.heading_path = draft.heading_path
                        chunk.page_number = draft.page_number
                        chunk.token_count = draft.token_count
                        chunk.embedding = vector
                        chunk.search_text = None
                        chunk.is_active = True
                if existing_chunks:
                    for stale_chunk in existing_chunks.values():
                        stale_chunk.is_active = False
                        stale_chunk.search_text = None
                await session.flush()
                from sqlalchemy import text

                await session.execute(
                    text(
                        "UPDATE knowledge_chunks "
                        "SET search_text = to_tsvector('simple', content) "
                        "WHERE document_id = :document_id AND is_active = true"
                    ),
                    {"document_id": document_id},
                )
                await sync_document_catalog(
                    session,
                    knowledge_base_id=document.knowledge_base_id,
                    document_id=document.id,
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

    async def recover_interrupted_ingestions(self, *, stale_after_minutes: int = 10) -> int:
        """Mark abandoned local background jobs retryable after an API restart."""
        cutoff = datetime.now(UTC) - timedelta(minutes=stale_after_minutes)
        async with self._sessions() as session:
            result = await session.execute(
                update(SourceDocumentModel)
                .where(
                    SourceDocumentModel.status.in_(
                        (DocumentStatus.PENDING, DocumentStatus.PROCESSING)
                    ),
                    SourceDocumentModel.updated_at < cutoff,
                )
                .values(
                    status=DocumentStatus.FAILED,
                    error_message="文档处理被服务重启中断，请点击重新索引。",
                    updated_at=datetime.now(UTC),
                )
                .returning(SourceDocumentModel.id)
            )
            recovered_ids = result.scalars().all()
            await session.execute(
                update(IngestionJobModel)
                .where(
                    IngestionJobModel.status == IngestionJobStatus.PROCESSING,
                    IngestionJobModel.updated_at < cutoff,
                )
                .values(
                    status=IngestionJobStatus.PENDING,
                    error_message="服务重启后自动恢复为待处理任务。",
                    updated_at=datetime.now(UTC),
                )
            )
            await session.commit()
            return len(recovered_ids)

    async def rebuild_coverage_catalogs(self) -> int:
        """Idempotently backfill catalog links for documents ingested before Phase 13."""
        async with self._sessions() as session:
            documents = list(
                (
                    await session.scalars(
                        select(SourceDocumentModel).where(
                            SourceDocumentModel.status == DocumentStatus.READY,
                            SourceDocumentModel.is_active.is_(True),
                        )
                    )
                ).all()
            )
            linked = 0
            for document in documents:
                linked += await sync_document_catalog(
                    session,
                    knowledge_base_id=document.knowledge_base_id,
                    document_id=document.id,
                )
            existing_pairs = set(
                (
                    await session.execute(
                        select(
                            QuestionCoverageModel.question_id,
                            QuestionCoverageModel.knowledge_point_id,
                        )
                    )
                ).all()
            )
            historical_pairs = (
                await session.execute(
                    select(
                        QuestionReferenceModel.question_id,
                        KnowledgeCatalogSourceModel.knowledge_point_id,
                    ).join(
                        KnowledgeCatalogSourceModel,
                        KnowledgeCatalogSourceModel.chunk_id == QuestionReferenceModel.chunk_id,
                    )
                )
            ).all()
            for question_id, point_id in set(historical_pairs) - existing_pairs:
                session.add(
                    QuestionCoverageModel(
                        id=uuid4(),
                        question_id=question_id,
                        knowledge_point_id=point_id,
                        created_at=datetime.now(UTC),
                    )
                )
            await session.commit()
            return linked

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
            from agent_mentor.infrastructure.database.models import KnowledgeCatalogSourceModel

            await session.execute(
                delete(KnowledgeCatalogSourceModel).where(
                    KnowledgeCatalogSourceModel.document_id == document_id
                )
            )
            await session.commit()
