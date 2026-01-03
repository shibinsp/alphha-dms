"""Search & Semantic Retrieval Models - M13"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.orm import relationship
from app.core.database import Base


class DocumentEmbedding(Base):
    """Vector embeddings for semantic search"""
    __tablename__ = "document_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, unique=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Embedding data
    embedding = Column(LargeBinary)  # Serialized vector (e.g., numpy array)
    embedding_model = Column(String(100))  # Model used to generate embedding
    embedding_version = Column(String(50))  # Model version

    # Content that was embedded
    embedded_content = Column(Text)  # The text that was embedded
    content_hash = Column(String(64))  # Hash to detect if re-embedding needed

    # Chunking info (if document was chunked)
    chunk_index = Column(Integer, default=0)  # 0 for full document
    chunk_count = Column(Integer, default=1)
    chunk_start = Column(Integer)  # Character position
    chunk_end = Column(Integer)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", backref="embeddings")
    tenant = relationship("Tenant", backref="document_embeddings")


class SavedSearch(Base):
    """User saved searches"""
    __tablename__ = "saved_searches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Search details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    query = Column(Text, nullable=False)  # The search query

    # Filters as JSON
    filters = Column(JSON)  # {source_type, document_type_id, date_range, etc.}

    # Search type
    search_type = Column(String(50), default="hybrid")  # keyword, semantic, hybrid

    # Notifications
    notify_on_new_results = Column(Boolean, default=False)
    last_notified_at = Column(DateTime, nullable=True)
    last_result_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="saved_searches")
    tenant = relationship("Tenant", backref="saved_searches")


class SearchHistory(Base):
    """Search history for analytics and suggestions"""
    __tablename__ = "search_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # Null for anonymous
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Search details
    query = Column(Text, nullable=False)
    search_type = Column(String(50))  # keyword, semantic, hybrid
    filters = Column(JSON)

    # Results
    result_count = Column(Integer)
    clicked_document_ids = Column(JSON)  # List of document IDs user clicked

    # Performance
    execution_time_ms = Column(Integer)

    searched_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="search_history")
    tenant = relationship("Tenant", backref="search_history")


class SearchSuggestion(Base):
    """Popular search suggestions"""
    __tablename__ = "search_suggestions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Suggestion
    suggestion = Column(String(255), nullable=False)
    normalized = Column(String(255))  # Lowercase, trimmed for matching

    # Popularity
    search_count = Column(Integer, default=1)
    last_searched_at = Column(DateTime, default=datetime.utcnow)

    # Type
    suggestion_type = Column(String(50), default="query")  # query, tag, document_type

    # Relationships
    tenant = relationship("Tenant", backref="search_suggestions")
