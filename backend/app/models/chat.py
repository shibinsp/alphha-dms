"""AI-Augmented Q&A Chatbot Models - M14"""
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class MessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class FeedbackType(str, enum.Enum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    INCORRECT = "INCORRECT"
    PARTIAL = "PARTIAL"


class ChatSession(Base):
    """Conversation sessions"""
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Session details
    title = Column(String(255))  # Auto-generated or user-set
    is_active = Column(Boolean, default=True)

    # Context - documents being discussed
    context_document_ids = Column(JSON)  # List of document IDs

    # Metadata
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="chat_sessions")
    tenant = relationship("Tenant", backref="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """Individual chat messages"""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False, index=True)

    # Message content
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # For assistant messages: citations
    citations = Column(JSON)  # List of {document_id, chunk_text, relevance_score}

    # RAG metadata
    context_used = Column(Text)  # The context retrieved for this response
    retrieval_scores = Column(JSON)  # {document_id: score} for transparency

    # Model info
    model_used = Column(String(100))
    tokens_used = Column(Integer)

    # Feedback
    feedback = Column(Enum(FeedbackType), nullable=True)
    feedback_comment = Column(Text)
    feedback_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class ChatCitation(Base):
    """Citations in chat responses"""
    __tablename__ = "chat_citations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("chat_messages.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)

    # Citation details
    cited_text = Column(Text)  # The specific text cited
    page_number = Column(Integer)
    relevance_score = Column(Float)

    # Position in response
    citation_index = Column(Integer)  # Order of citation in response

    # Relationships
    message = relationship("ChatMessage", backref="citation_records")
    document = relationship("Document", backref="chat_citations")


class RAGConfiguration(Base):
    """RAG system configuration per tenant"""
    __tablename__ = "rag_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, unique=True)

    # Retrieval settings
    retrieval_model = Column(String(100), default="sentence-transformers/all-MiniLM-L6-v2")
    top_k = Column(Integer, default=5)  # Number of chunks to retrieve
    similarity_threshold = Column(Float, default=0.7)

    # Generation settings
    llm_model = Column(String(100), default="gpt-4-turbo")
    max_tokens = Column(Integer, default=1000)
    temperature = Column(Float, default=0.7)

    # System prompt
    system_prompt = Column(Text)

    # Features
    include_citations = Column(Boolean, default=True)
    enable_follow_up = Column(Boolean, default=True)
    max_context_documents = Column(Integer, default=10)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(36), ForeignKey("users.id"))

    # Relationships
    tenant = relationship("Tenant", backref="rag_config")
