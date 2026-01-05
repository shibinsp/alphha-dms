"""Embedding Service - Vector embeddings using Mistral AI"""
import hashlib
import json
import struct
from typing import List, Optional, Tuple
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.config import settings
from app.models.document import Document
from app.models.search import DocumentEmbedding


class EmbeddingService:
    """Service for generating and managing document embeddings using Mistral AI"""

    EMBEDDING_MODEL = "mistral-embed"
    EMBEDDING_DIMENSION = 1024  # Mistral embed dimension
    MAX_TOKENS = 8000  # Max tokens for embedding
    CHUNK_SIZE = 6000  # Characters per chunk (roughly 1500 tokens)
    CHUNK_OVERLAP = 200  # Overlap between chunks

    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.MISTRAL_API_KEY
        self.api_url = "https://api.mistral.ai/v1/embeddings"

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using Mistral AI API"""
        if not self.api_key:
            return None

        # Truncate if too long
        if len(text) > self.MAX_TOKENS * 4:  # Rough char to token ratio
            text = text[:self.MAX_TOKENS * 4]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.EMBEDDING_MODEL,
                        "input": [text],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            print(f"Embedding generation error: {e}")
            return None

    def generate_embedding_sync(self, text: str) -> Optional[List[float]]:
        """Synchronous version of embedding generation"""
        if not self.api_key:
            return None

        if len(text) > self.MAX_TOKENS * 4:
            text = text[:self.MAX_TOKENS * 4]

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.EMBEDDING_MODEL,
                        "input": [text],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            print(f"Embedding generation error: {e}")
            return None

    def serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding to bytes for storage"""
        return struct.pack(f'{len(embedding)}f', *embedding)

    def deserialize_embedding(self, data: bytes) -> List[float]:
        """Deserialize embedding from bytes"""
        count = len(data) // 4  # 4 bytes per float
        return list(struct.unpack(f'{count}f', data))

    def compute_content_hash(self, content: str) -> str:
        """Compute hash of content to detect changes"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into chunks for embedding.
        Returns list of (chunk_text, start_pos, end_pos).
        """
        if len(text) <= self.CHUNK_SIZE:
            return [(text, 0, len(text))]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end in last 200 chars
                search_start = max(end - 200, start)
                last_period = text.rfind('. ', search_start, end)
                last_newline = text.rfind('\n', search_start, end)
                break_point = max(last_period, last_newline)

                if break_point > start:
                    end = break_point + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append((chunk, start, end))

            # Next chunk starts with overlap
            start = end - self.CHUNK_OVERLAP

        return chunks

    async def embed_document(
        self,
        document_id: str,
        tenant_id: str,
        force: bool = False,
    ) -> List[DocumentEmbedding]:
        """
        Generate embeddings for a document.
        Handles chunking for long documents.
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        ).first()

        if not document:
            return []

        # Build content to embed (title + OCR text)
        content_parts = [document.title or ""]
        if document.ocr_text:
            content_parts.append(document.ocr_text)
        content = "\n\n".join(filter(None, content_parts))

        if not content.strip():
            return []

        content_hash = self.compute_content_hash(content)

        # Check if already embedded with same content
        if not force:
            existing = self.db.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_id == document_id,
                DocumentEmbedding.content_hash == content_hash,
            ).first()
            if existing:
                return [existing]

        # Delete old embeddings
        self.db.query(DocumentEmbedding).filter(
            DocumentEmbedding.document_id == document_id,
        ).delete()

        # Chunk the content
        chunks = self.chunk_text(content)
        embeddings = []

        for idx, (chunk_text, chunk_start, chunk_end) in enumerate(chunks):
            # Generate embedding
            embedding_vector = await self.generate_embedding(chunk_text)
            if not embedding_vector:
                continue

            # Create embedding record
            doc_embedding = DocumentEmbedding(
                document_id=document_id,
                tenant_id=tenant_id,
                embedding=self.serialize_embedding(embedding_vector),
                embedding_model=self.EMBEDDING_MODEL,
                embedding_version="1.0",
                embedded_content=chunk_text[:1000],  # Store first 1000 chars
                content_hash=content_hash,
                chunk_index=idx,
                chunk_count=len(chunks),
                chunk_start=chunk_start,
                chunk_end=chunk_end,
            )
            self.db.add(doc_embedding)
            embeddings.append(doc_embedding)

        self.db.commit()
        return embeddings

    def embed_document_sync(
        self,
        document_id: str,
        tenant_id: str,
        force: bool = False,
    ) -> List[DocumentEmbedding]:
        """Synchronous version of embed_document"""
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        ).first()

        if not document:
            return []

        content_parts = [document.title or ""]
        if document.ocr_text:
            content_parts.append(document.ocr_text)
        content = "\n\n".join(filter(None, content_parts))

        if not content.strip():
            return []

        content_hash = self.compute_content_hash(content)

        if not force:
            existing = self.db.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_id == document_id,
                DocumentEmbedding.content_hash == content_hash,
            ).first()
            if existing:
                return [existing]

        self.db.query(DocumentEmbedding).filter(
            DocumentEmbedding.document_id == document_id,
        ).delete()

        chunks = self.chunk_text(content)
        embeddings = []

        for idx, (chunk_text, chunk_start, chunk_end) in enumerate(chunks):
            embedding_vector = self.generate_embedding_sync(chunk_text)
            if not embedding_vector:
                continue

            doc_embedding = DocumentEmbedding(
                document_id=document_id,
                tenant_id=tenant_id,
                embedding=self.serialize_embedding(embedding_vector),
                embedding_model=self.EMBEDDING_MODEL,
                embedding_version="1.0",
                embedded_content=chunk_text[:1000],
                content_hash=content_hash,
                chunk_index=idx,
                chunk_count=len(chunks),
                chunk_start=chunk_start,
                chunk_end=chunk_end,
            )
            self.db.add(doc_embedding)
            embeddings.append(doc_embedding)

        self.db.commit()
        return embeddings

    async def search_similar(
        self,
        query: str,
        tenant_id: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        Find documents similar to query using embedding similarity.
        Returns list of (document_id, similarity_score).
        """
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        if not query_embedding:
            return []

        # Get all embeddings for tenant
        query = self.db.query(DocumentEmbedding).filter(
            DocumentEmbedding.tenant_id == tenant_id,
            DocumentEmbedding.embedding.isnot(None),
        )

        if document_ids:
            query = query.filter(DocumentEmbedding.document_id.in_(document_ids))

        embeddings = query.all()

        # Compute similarities
        scores = {}
        for emb in embeddings:
            doc_embedding = self.deserialize_embedding(emb.embedding)
            similarity = self.cosine_similarity(query_embedding, doc_embedding)

            # For chunked documents, take max similarity
            doc_id = emb.document_id
            if doc_id not in scores or similarity > scores[doc_id]:
                scores[doc_id] = similarity

        # Sort by similarity
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def search_similar_sync(
        self,
        query: str,
        tenant_id: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 20,
    ) -> List[Tuple[str, float]]:
        """Synchronous version of search_similar"""
        query_embedding = self.generate_embedding_sync(query)
        if not query_embedding:
            return []

        db_query = self.db.query(DocumentEmbedding).filter(
            DocumentEmbedding.tenant_id == tenant_id,
            DocumentEmbedding.embedding.isnot(None),
        )

        if document_ids:
            db_query = db_query.filter(DocumentEmbedding.document_id.in_(document_ids))

        embeddings = db_query.all()

        scores = {}
        for emb in embeddings:
            doc_embedding = self.deserialize_embedding(emb.embedding)
            similarity = self.cosine_similarity(query_embedding, doc_embedding)

            doc_id = emb.document_id
            if doc_id not in scores or similarity > scores[doc_id]:
                scores[doc_id] = similarity

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def get_embedding_stats(self, tenant_id: str) -> dict:
        """Get embedding statistics for a tenant"""
        total = self.db.query(DocumentEmbedding).filter(
            DocumentEmbedding.tenant_id == tenant_id,
        ).count()

        unique_docs = self.db.query(DocumentEmbedding.document_id).filter(
            DocumentEmbedding.tenant_id == tenant_id,
        ).distinct().count()

        return {
            "total_embeddings": total,
            "embedded_documents": unique_docs,
            "model": self.EMBEDDING_MODEL,
        }

    async def batch_embed_documents(
        self,
        tenant_id: str,
        document_ids: Optional[List[str]] = None,
        batch_size: int = 10,
    ) -> dict:
        """Batch embed multiple documents"""
        # Get documents without embeddings
        query = self.db.query(Document).filter(
            Document.tenant_id == tenant_id,
            Document.ocr_text.isnot(None),
        )

        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        else:
            # Get documents without embeddings
            embedded_ids = self.db.query(DocumentEmbedding.document_id).filter(
                DocumentEmbedding.tenant_id == tenant_id,
            ).distinct().subquery()

            query = query.filter(~Document.id.in_(embedded_ids))

        documents = query.limit(batch_size).all()

        success_count = 0
        failed_count = 0

        for doc in documents:
            try:
                result = await self.embed_document(doc.id, tenant_id)
                if result:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Failed to embed document {doc.id}: {e}")
                failed_count += 1

        return {
            "processed": len(documents),
            "success": success_count,
            "failed": failed_count,
        }
