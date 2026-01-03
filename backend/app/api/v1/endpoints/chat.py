"""Chat API Endpoints - M14 AI-Augmented Q&A"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.dependencies import (
    get_current_user,
    get_current_tenant_id,
    require_permissions,
)
from app.models.user import User
from app.models.chat import FeedbackType
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["AI Chat"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None
    context_document_ids: Optional[List[str]] = None


class ChatMessageRequest(BaseModel):
    message: str


class FeedbackRequest(BaseModel):
    feedback: FeedbackType
    comment: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[List[dict]] = None
    created_at: str
    feedback: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a new chat session"""
    service = ChatService(db)
    session = service.create_session(
        user_id=current_user.id,
        tenant_id=tenant_id,
        title=request.title,
        context_document_ids=request.context_document_ids,
    )
    return session


@router.get("/sessions")
async def list_sessions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List user's chat sessions"""
    service = ChatService(db)
    return service.list_sessions(current_user.id, tenant_id, limit)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a chat session with messages"""
    service = ChatService(db)
    session = service.get_session(session_id, current_user.id, tenant_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Delete a chat session"""
    service = ChatService(db)
    service.delete_session(session_id, current_user.id, tenant_id)
    return {"message": "Session deleted"}


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Send a message and get AI response"""
    service = ChatService(db)
    message = service.chat(
        session_id=session_id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        message=request.message,
        user_clearance_level=current_user.clearance_level or "PUBLIC",
    )
    return message


@router.post("/messages/{message_id}/feedback")
async def add_feedback(
    message_id: str,
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Add feedback to a chat message"""
    service = ChatService(db)
    message = service.add_feedback(
        message_id=message_id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        feedback=request.feedback,
        comment=request.comment,
    )
    return message


# Quick chat endpoint (creates session automatically)
@router.post("/")
async def quick_chat(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["chat:use"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Quick chat - creates session automatically"""
    service = ChatService(db)

    # Create a new session
    session = service.create_session(
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    # Send message
    message = service.chat(
        session_id=session.id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        message=request.message,
        user_clearance_level=current_user.clearance_level or "PUBLIC",
    )

    return {
        "session_id": session.id,
        "message": message,
    }
