"""Chat Service - M14 AI-Augmented Q&A Chatbot"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
import httpx

from app.models.chat import (
    ChatSession,
    ChatMessage,
    ChatCitation,
    RAGConfiguration,
    MessageRole,
    FeedbackType,
)
from app.models.document import Document
from app.services.search_service import SearchService
from app.core.config import get_settings

settings = get_settings()


class ChatService:
    """
    Chat service implementing RAG (Retrieval-Augmented Generation) with Mistral AI.
    """

    MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService(db)

    def create_session(
        self,
        user_id: str,
        tenant_id: str,
        title: Optional[str] = None,
        context_document_ids: Optional[List[str]] = None,
    ) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            user_id=user_id,
            tenant_id=tenant_id,
            title=title or "New Conversation",
            context_document_ids=context_document_ids or [],
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
    ) -> Optional[ChatSession]:
        """Get a chat session"""
        return (
            self.db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.tenant_id == tenant_id,
            )
            .first()
        )

    def list_sessions(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 20,
    ) -> List[ChatSession]:
        """List user's chat sessions"""
        return (
            self.db.query(ChatSession)
            .filter(
                ChatSession.user_id == user_id,
                ChatSession.tenant_id == tenant_id,
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .all()
        )

    def chat(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        message: str,
        user_clearance_level: str = "PUBLIC",
    ) -> ChatMessage:
        """
        Process a chat message using RAG:
        1. Retrieve relevant document context
        2. Generate response with citations
        """
        # Get or create session
        session = self.get_session(session_id, user_id, tenant_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=message,
        )
        self.db.add(user_message)

        # Step 1: Retrieve relevant context
        context, citations = self._retrieve_context(
            query=message,
            tenant_id=tenant_id,
            user_id=user_id,
            user_clearance_level=user_clearance_level,
            context_document_ids=session.context_document_ids,
        )

        # Step 2: Generate response using Mistral AI
        response_content = self._generate_response(message, context)
        model_used = settings.MISTRAL_MODEL if settings.MISTRAL_API_KEY else "placeholder"

        # Save assistant message
        assistant_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response_content,
            citations=[{
                "document_id": c["document_id"],
                "chunk_text": c["chunk_text"],
                "relevance_score": c["score"],
            } for c in citations],
            context_used=context,
            model_used=model_used,
            tokens_used=len(response_content.split()),  # Rough estimate
        )
        self.db.add(assistant_message)

        # Update session
        session.message_count += 2
        session.last_message_at = datetime.utcnow()

        # Auto-generate title if first message
        if session.message_count == 2 and session.title == "New Conversation":
            session.title = self._generate_title(message)

        self.db.commit()
        self.db.refresh(assistant_message)

        return assistant_message

    def _retrieve_context(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        user_clearance_level: str,
        context_document_ids: Optional[List[str]] = None,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Retrieve relevant document chunks for context.
        Returns: (combined_context, citations)
        """
        # Get RAG configuration
        config = self._get_rag_config(tenant_id)
        top_k = config.top_k if config else 5

        # Search for relevant documents
        search_results = self.search_service.search(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            search_type="keyword",
            page=1,
            page_size=top_k,
            user_clearance_level=user_clearance_level,
        )

        # If context documents are specified, filter to those
        documents = search_results.get("items", [])
        if context_document_ids and not documents:
            # Fallback: get context documents directly
            from app.models.document import Document
            documents = self.db.query(Document).filter(
                Document.id.in_(context_document_ids),
                Document.tenant_id == tenant_id
            ).all()

        # Build context from documents
        context_parts = []
        citations = []

        for i, doc in enumerate(documents[:top_k]):
            # Get document content (OCR text or title as fallback)
            chunk_text = doc.ocr_text or doc.title
            if chunk_text:
                context_parts.append(f"[Document {i+1}: {doc.title}]\n{chunk_text[:1000]}...")
                citations.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "chunk_text": chunk_text[:500],
                    "score": 0.9 - (i * 0.1),  # Placeholder score
                })

        combined_context = "\n\n".join(context_parts)
        return combined_context, citations

    def _generate_response(
        self,
        query: str,
        context: str,
    ) -> str:
        """Generate response using Mistral AI."""
        if not context:
            return (
                "I couldn't find any relevant documents to answer your question. "
                "Please try rephrasing your query or uploading relevant documents."
            )

        if not settings.MISTRAL_API_KEY:
            return (
                f"Based on the documents I found, here's what I can tell you:\n\n"
                f"Your question was: \"{query}\"\n\n"
                f"The relevant documents contain information that may help answer this. "
                f"(Mistral API key not configured - using placeholder response)\n\n"
                f"The system retrieved {len(context.split('[Document'))-1} relevant documents."
            )

        try:
            system_prompt = (
                "You are a helpful document assistant for a government document management system. "
                "Answer questions based on the provided document context. Be concise and accurate. "
                "If the context doesn't contain enough information, say so."
            )
            
            user_prompt = f"Context from documents:\n{context}\n\nQuestion: {query}"

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.MISTRAL_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.MISTRAL_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error generating response: {str(e)}. Please try again."

    def _generate_title(self, first_message: str) -> str:
        """Generate a title from the first message"""
        # Simple truncation - in production, use LLM
        words = first_message.split()[:6]
        title = " ".join(words)
        if len(first_message.split()) > 6:
            title += "..."
        return title

    def _get_rag_config(self, tenant_id: str) -> Optional[RAGConfiguration]:
        """Get RAG configuration for tenant"""
        return (
            self.db.query(RAGConfiguration)
            .filter(RAGConfiguration.tenant_id == tenant_id)
            .first()
        )

    def add_feedback(
        self,
        message_id: str,
        user_id: str,
        tenant_id: str,
        feedback: FeedbackType,
        comment: Optional[str] = None,
    ) -> ChatMessage:
        """Add feedback to a chat message"""
        message = (
            self.db.query(ChatMessage)
            .join(ChatSession)
            .filter(
                ChatMessage.id == message_id,
                ChatSession.user_id == user_id,
                ChatSession.tenant_id == tenant_id,
            )
            .first()
        )

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        message.feedback = feedback
        message.feedback_comment = comment
        message.feedback_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)
        return message

    def delete_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
    ) -> bool:
        """Delete a chat session"""
        session = self.get_session(session_id, user_id, tenant_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        self.db.delete(session)
        self.db.commit()
        return True
