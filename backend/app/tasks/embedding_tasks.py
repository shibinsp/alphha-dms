"""Embedding Tasks - Background processing for document embeddings"""
import asyncio
from app.tasks import celery_app
from app.core.database import SessionLocal
from app.services.embedding_service import EmbeddingService


@celery_app.task(bind=True, max_retries=3)
def generate_document_embedding(self, document_id: str, tenant_id: str):
    """
    Generate embedding for a single document.
    Called after document upload or OCR completion.
    """
    db = SessionLocal()
    try:
        service = EmbeddingService(db)
        result = service.embed_document_sync(document_id, tenant_id)
        return {
            "status": "success",
            "document_id": document_id,
            "embeddings_created": len(result),
        }
    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds
    finally:
        db.close()


@celery_app.task(bind=True)
def batch_embed_documents(self, tenant_id: str, batch_size: int = 50):
    """
    Batch embed multiple documents that don't have embeddings.
    Useful for initial embedding of existing documents.
    """
    db = SessionLocal()
    try:
        service = EmbeddingService(db)
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.batch_embed_documents(tenant_id, batch_size=batch_size)
            )
        finally:
            loop.close()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            **result,
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task(bind=True)
def reembed_outdated_documents(self, tenant_id: str, batch_size: int = 20):
    """
    Re-embed documents whose content has changed.
    Checks content hash to detect changes.
    """
    db = SessionLocal()
    try:
        from app.models.document import Document
        from app.models.search import DocumentEmbedding
        import hashlib

        service = EmbeddingService(db)

        # Get documents with embeddings
        embedded_docs = (
            db.query(Document, DocumentEmbedding)
            .join(DocumentEmbedding, Document.id == DocumentEmbedding.document_id)
            .filter(Document.tenant_id == tenant_id)
            .limit(batch_size)
            .all()
        )

        reembedded = 0
        for doc, embedding in embedded_docs:
            # Build content and check hash
            content_parts = [doc.title or ""]
            if doc.ocr_text:
                content_parts.append(doc.ocr_text)
            content = "\n\n".join(filter(None, content_parts))

            if not content.strip():
                continue

            current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

            if current_hash != embedding.content_hash:
                # Content changed, re-embed
                service.embed_document_sync(doc.id, tenant_id, force=True)
                reembedded += 1

        return {
            "status": "success",
            "checked": len(embedded_docs),
            "reembedded": reembedded,
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task
def get_embedding_stats(tenant_id: str):
    """Get embedding statistics for a tenant."""
    db = SessionLocal()
    try:
        service = EmbeddingService(db)
        return service.get_embedding_stats(tenant_id)
    finally:
        db.close()
