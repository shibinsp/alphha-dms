"""Taxonomy & Auto-Tagging Models - M11"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class TagType(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    SUGGESTED = "SUGGESTED"


class SuggestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Tag(Base):
    """Tag / controlled vocabulary"""
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Tag details
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)  # URL-safe version
    description = Column(Text)
    color = Column(String(7))  # Hex color code

    # Hierarchy
    parent_id = Column(String(36), ForeignKey("tags.id"), nullable=True)

    # Category / namespace
    category = Column(String(100))  # e.g., "topic", "department", "project"

    # Usage stats
    usage_count = Column(Integer, default=0)

    # Governance
    is_controlled = Column(Boolean, default=False)  # If true, only admins can manage
    requires_approval = Column(Boolean, default=False)  # Suggestions need approval

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"))

    # Relationships
    tenant = relationship("Tenant", backref="tags")
    parent = relationship("Tag", remote_side=[id], backref="children")
    creator = relationship("User", backref="created_tags")


class DocumentTag(Base):
    """Document-tag associations"""
    __tablename__ = "document_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    tag_id = Column(String(36), ForeignKey("tags.id"), nullable=False, index=True)

    # How was this tag added
    tag_type = Column(Enum(TagType), default=TagType.MANUAL, nullable=False)

    # For auto-tags: confidence score
    confidence_score = Column(Float, nullable=True)

    # Metadata
    added_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # Null for auto-tags
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", backref="tags")
    tag = relationship("Tag", backref="document_associations")
    adder = relationship("User", backref="added_document_tags")


class TagSuggestion(Base):
    """Auto-suggested tags pending review"""
    __tablename__ = "tag_suggestions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Suggestion
    suggested_tag_name = Column(String(100), nullable=False)
    suggested_tag_id = Column(String(36), ForeignKey("tags.id"), nullable=True)  # If matches existing

    # Confidence
    confidence_score = Column(Float, nullable=False)
    source = Column(String(50))  # e.g., "OCR", "NLP", "ML_MODEL"

    # Status
    status = Column(Enum(SuggestionStatus), default=SuggestionStatus.PENDING, nullable=False)

    # Review
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", backref="tag_suggestions")
    tenant = relationship("Tenant", backref="tag_suggestions")
    existing_tag = relationship("Tag", backref="suggestions")
    reviewer = relationship("User", backref="reviewed_tag_suggestions")


class TagSynonym(Base):
    """Tag synonyms for better search and auto-tagging"""
    __tablename__ = "tag_synonyms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tag_id = Column(String(36), ForeignKey("tags.id"), nullable=False)
    synonym = Column(String(100), nullable=False)

    # Relationships
    tag = relationship("Tag", backref="synonyms")
