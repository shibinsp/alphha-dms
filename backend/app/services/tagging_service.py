"""Tagging Service - M11 Auto-Tagging & NER"""
import re
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.core.config import settings
from app.models.document import Document
from app.models.taxonomy import Tag, DocumentTag, TagSuggestion, TagSynonym, TagType, SuggestionStatus


class TaggingService:
    """Service for tag management and NER-based auto-tagging"""

    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.MISTRAL_API_KEY
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.model = settings.MISTRAL_MODEL

    # ==================== Tag CRUD ====================

    def create_tag(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_controlled: bool = False,
        requires_approval: bool = False,
    ) -> Tag:
        """Create a new tag"""
        # Generate slug from name
        slug = self._generate_slug(name)

        # Check for duplicate
        existing = self.db.query(Tag).filter(
            Tag.tenant_id == tenant_id,
            Tag.slug == slug,
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Tag with this name already exists")

        tag = Tag(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            category=category,
            description=description,
            color=color,
            parent_id=parent_id,
            is_controlled=is_controlled,
            requires_approval=requires_approval,
            created_by=user_id,
        )

        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def get_tags(
        self,
        tenant_id: str,
        category: Optional[str] = None,
        search: Optional[str] = None,
        parent_id: Optional[str] = None,
        include_children: bool = True,
    ) -> List[Tag]:
        """Get tags for tenant with optional filters"""
        query = self.db.query(Tag).filter(Tag.tenant_id == tenant_id)

        if category:
            query = query.filter(Tag.category == category)

        if search:
            pattern = f"%{search.lower()}%"
            query = query.filter(Tag.name.ilike(pattern))

        if parent_id is not None:
            query = query.filter(Tag.parent_id == parent_id)
        elif not include_children:
            query = query.filter(Tag.parent_id.is_(None))

        return query.order_by(Tag.usage_count.desc(), Tag.name).all()

    def get_tag(self, tag_id: str, tenant_id: str) -> Tag:
        """Get a single tag by ID"""
        tag = self.db.query(Tag).filter(
            Tag.id == tag_id,
            Tag.tenant_id == tenant_id,
        ).first()

        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        return tag

    def update_tag(
        self,
        tag_id: str,
        tenant_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        category: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_controlled: Optional[bool] = None,
        requires_approval: Optional[bool] = None,
    ) -> Tag:
        """Update a tag"""
        tag = self.get_tag(tag_id, tenant_id)

        if name:
            tag.name = name
            tag.slug = self._generate_slug(name)
        if description is not None:
            tag.description = description
        if color is not None:
            tag.color = color
        if category is not None:
            tag.category = category
        if parent_id is not None:
            tag.parent_id = parent_id
        if is_controlled is not None:
            tag.is_controlled = is_controlled
        if requires_approval is not None:
            tag.requires_approval = requires_approval

        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete_tag(self, tag_id: str, tenant_id: str) -> bool:
        """Delete a tag"""
        tag = self.get_tag(tag_id, tenant_id)

        # Delete associated document tags
        self.db.query(DocumentTag).filter(DocumentTag.tag_id == tag_id).delete()

        # Delete synonyms
        self.db.query(TagSynonym).filter(TagSynonym.tag_id == tag_id).delete()

        # Delete suggestions referencing this tag
        self.db.query(TagSuggestion).filter(TagSuggestion.suggested_tag_id == tag_id).update(
            {"suggested_tag_id": None}
        )

        self.db.delete(tag)
        self.db.commit()
        return True

    # ==================== Document Tagging ====================

    def add_tag_to_document(
        self,
        document_id: str,
        tag_id: str,
        user_id: str,
        tenant_id: str,
        tag_type: TagType = TagType.MANUAL,
        confidence_score: Optional[float] = None,
    ) -> DocumentTag:
        """Add a tag to a document"""
        # Verify document exists and belongs to tenant
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        ).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Verify tag exists
        tag = self.get_tag(tag_id, tenant_id)

        # Check if already tagged
        existing = self.db.query(DocumentTag).filter(
            DocumentTag.document_id == document_id,
            DocumentTag.tag_id == tag_id,
        ).first()

        if existing:
            return existing  # Already tagged

        doc_tag = DocumentTag(
            document_id=document_id,
            tag_id=tag_id,
            tag_type=tag_type,
            confidence_score=confidence_score,
            added_by=user_id if tag_type == TagType.MANUAL else None,
        )

        self.db.add(doc_tag)

        # Update tag usage count
        tag.usage_count += 1

        self.db.commit()
        self.db.refresh(doc_tag)
        return doc_tag

    def remove_tag_from_document(
        self,
        document_id: str,
        tag_id: str,
        tenant_id: str,
    ) -> bool:
        """Remove a tag from a document"""
        # Verify tag belongs to tenant
        tag = self.get_tag(tag_id, tenant_id)

        doc_tag = self.db.query(DocumentTag).filter(
            DocumentTag.document_id == document_id,
            DocumentTag.tag_id == tag_id,
        ).first()

        if not doc_tag:
            raise HTTPException(status_code=404, detail="Tag not found on document")

        self.db.delete(doc_tag)

        # Update tag usage count
        if tag.usage_count > 0:
            tag.usage_count -= 1

        self.db.commit()
        return True

    def get_document_tags(self, document_id: str, tenant_id: str) -> List[DocumentTag]:
        """Get all tags for a document"""
        return (
            self.db.query(DocumentTag)
            .join(Tag)
            .filter(
                DocumentTag.document_id == document_id,
                Tag.tenant_id == tenant_id,
            )
            .all()
        )

    # ==================== Auto-Tagging / NER ====================

    async def auto_tag_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> List[TagSuggestion]:
        """
        Auto-tag a document using NER extraction with Mistral AI.
        Creates suggestions for review.
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        ).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get text to analyze
        text = ""
        if document.ocr_text:
            text = document.ocr_text[:10000]  # Limit to 10k chars
        elif document.title:
            text = document.title

        if not text.strip():
            return []

        # Extract entities using Mistral
        entities = await self.extract_entities(text)

        if not entities:
            return []

        # Get existing tags for matching
        existing_tags = self.get_tags(tenant_id)
        tag_map = {tag.name.lower(): tag for tag in existing_tags}

        # Also build synonym map
        synonyms = self.db.query(TagSynonym).join(Tag).filter(Tag.tenant_id == tenant_id).all()
        synonym_map = {s.synonym.lower(): s.tag for s in synonyms}

        suggestions = []

        for entity_type, entity_list in entities.items():
            for entity_info in entity_list:
                entity_name = entity_info.get("name", entity_info) if isinstance(entity_info, dict) else entity_info
                confidence = entity_info.get("confidence", 0.8) if isinstance(entity_info, dict) else 0.8

                # Check if matches existing tag
                matched_tag = None
                entity_lower = entity_name.lower()

                if entity_lower in tag_map:
                    matched_tag = tag_map[entity_lower]
                elif entity_lower in synonym_map:
                    matched_tag = synonym_map[entity_lower]

                # Check for existing suggestion
                existing_suggestion = self.db.query(TagSuggestion).filter(
                    TagSuggestion.document_id == document_id,
                    TagSuggestion.suggested_tag_name == entity_name,
                    TagSuggestion.status == SuggestionStatus.PENDING,
                ).first()

                if existing_suggestion:
                    continue

                # Create suggestion
                suggestion = TagSuggestion(
                    document_id=document_id,
                    tenant_id=tenant_id,
                    suggested_tag_name=entity_name,
                    suggested_tag_id=matched_tag.id if matched_tag else None,
                    confidence_score=confidence,
                    source=f"NER_{entity_type}",
                    status=SuggestionStatus.PENDING,
                )

                self.db.add(suggestion)
                suggestions.append(suggestion)

        self.db.commit()
        return suggestions

    async def extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract named entities from text using Mistral AI.
        Returns dict with entity types as keys and lists of entities.
        """
        if not self.api_key:
            return {}

        prompt = f"""Extract named entities from the following text. Return a JSON object with entity types as keys.

Entity types to extract:
- PERSON: Names of people
- ORGANIZATION: Company names, institutions, agencies
- LOCATION: Places, cities, countries, addresses
- DATE: Dates and time references
- MONEY: Monetary amounts
- DOCUMENT_TYPE: Types of documents mentioned (invoice, contract, report, etc.)
- PRODUCT: Product or service names

For each entity, provide:
- name: The entity text
- confidence: A confidence score from 0.5 to 1.0

Text to analyze:
\"\"\"
{text[:5000]}
\"\"\"

Return ONLY valid JSON in this format:
{{
  "PERSON": [{{"name": "John Doe", "confidence": 0.95}}],
  "ORGANIZATION": [{{"name": "Acme Corp", "confidence": 0.9}}],
  ...
}}
"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 2000,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract response text
                content = data["choices"][0]["message"]["content"]

                # Parse JSON from response
                # Try to extract JSON if wrapped in markdown
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                if json_match:
                    content = json_match.group(1)

                return json.loads(content)

        except json.JSONDecodeError:
            return {}
        except Exception as e:
            print(f"NER extraction error: {e}")
            return {}

    def extract_entities_sync(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Synchronous version of extract_entities"""
        if not self.api_key:
            return {}

        prompt = f"""Extract named entities from the following text. Return a JSON object with entity types as keys.

Entity types to extract:
- PERSON: Names of people
- ORGANIZATION: Company names, institutions, agencies
- LOCATION: Places, cities, countries, addresses
- DATE: Dates and time references
- MONEY: Monetary amounts
- DOCUMENT_TYPE: Types of documents mentioned

For each entity, provide:
- name: The entity text
- confidence: A confidence score from 0.5 to 1.0

Text:
\"\"\"
{text[:5000]}
\"\"\"

Return ONLY valid JSON."""

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 2000,
                    },
                )
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                if json_match:
                    content = json_match.group(1)

                return json.loads(content)

        except Exception as e:
            print(f"NER extraction error: {e}")
            return {}

    # ==================== Suggestion Management ====================

    def get_pending_suggestions(
        self,
        tenant_id: str,
        document_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TagSuggestion]:
        """Get pending tag suggestions for review"""
        query = self.db.query(TagSuggestion).filter(
            TagSuggestion.tenant_id == tenant_id,
            TagSuggestion.status == SuggestionStatus.PENDING,
        )

        if document_id:
            query = query.filter(TagSuggestion.document_id == document_id)

        return query.order_by(TagSuggestion.confidence_score.desc()).limit(limit).all()

    def approve_suggestion(
        self,
        suggestion_id: str,
        user_id: str,
        tenant_id: str,
        create_tag_if_needed: bool = True,
    ) -> DocumentTag:
        """Approve a tag suggestion"""
        suggestion = self.db.query(TagSuggestion).filter(
            TagSuggestion.id == suggestion_id,
            TagSuggestion.tenant_id == tenant_id,
            TagSuggestion.status == SuggestionStatus.PENDING,
        ).first()

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        # Get or create tag
        tag = None
        if suggestion.suggested_tag_id:
            tag = self.db.query(Tag).filter(Tag.id == suggestion.suggested_tag_id).first()

        if not tag and create_tag_if_needed:
            # Create new tag from suggestion
            tag = self.create_tag(
                tenant_id=tenant_id,
                user_id=user_id,
                name=suggestion.suggested_tag_name,
                category=suggestion.source,  # Use NER type as category
            )

        if not tag:
            raise HTTPException(status_code=400, detail="Could not create or find tag")

        # Add tag to document
        doc_tag = self.add_tag_to_document(
            document_id=suggestion.document_id,
            tag_id=tag.id,
            user_id=user_id,
            tenant_id=tenant_id,
            tag_type=TagType.AUTO,
            confidence_score=suggestion.confidence_score,
        )

        # Update suggestion status
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.reviewed_by = user_id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.suggested_tag_id = tag.id

        self.db.commit()
        return doc_tag

    def reject_suggestion(
        self,
        suggestion_id: str,
        user_id: str,
        tenant_id: str,
        reason: Optional[str] = None,
    ) -> TagSuggestion:
        """Reject a tag suggestion"""
        suggestion = self.db.query(TagSuggestion).filter(
            TagSuggestion.id == suggestion_id,
            TagSuggestion.tenant_id == tenant_id,
            TagSuggestion.status == SuggestionStatus.PENDING,
        ).first()

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        suggestion.status = SuggestionStatus.REJECTED
        suggestion.reviewed_by = user_id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.review_notes = reason

        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def bulk_approve_suggestions(
        self,
        suggestion_ids: List[str],
        user_id: str,
        tenant_id: str,
    ) -> int:
        """Approve multiple suggestions at once"""
        approved_count = 0
        for sid in suggestion_ids:
            try:
                self.approve_suggestion(sid, user_id, tenant_id)
                approved_count += 1
            except Exception:
                continue
        return approved_count

    # ==================== Tag Synonyms ====================

    def add_synonym(self, tag_id: str, synonym: str, tenant_id: str) -> TagSynonym:
        """Add a synonym to a tag"""
        tag = self.get_tag(tag_id, tenant_id)

        # Check for duplicate
        existing = self.db.query(TagSynonym).filter(
            TagSynonym.tag_id == tag_id,
            func.lower(TagSynonym.synonym) == synonym.lower(),
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Synonym already exists")

        tag_synonym = TagSynonym(tag_id=tag_id, synonym=synonym)
        self.db.add(tag_synonym)
        self.db.commit()
        self.db.refresh(tag_synonym)
        return tag_synonym

    def remove_synonym(self, synonym_id: str, tenant_id: str) -> bool:
        """Remove a synonym"""
        synonym = (
            self.db.query(TagSynonym)
            .join(Tag)
            .filter(TagSynonym.id == synonym_id, Tag.tenant_id == tenant_id)
            .first()
        )

        if not synonym:
            raise HTTPException(status_code=404, detail="Synonym not found")

        self.db.delete(synonym)
        self.db.commit()
        return True

    # ==================== Utilities ====================

    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from name"""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')

    def get_popular_tags(self, tenant_id: str, limit: int = 20) -> List[Tag]:
        """Get most used tags"""
        return (
            self.db.query(Tag)
            .filter(Tag.tenant_id == tenant_id)
            .order_by(Tag.usage_count.desc())
            .limit(limit)
            .all()
        )

    def get_tag_categories(self, tenant_id: str) -> List[str]:
        """Get distinct tag categories"""
        result = (
            self.db.query(Tag.category)
            .filter(Tag.tenant_id == tenant_id, Tag.category.isnot(None))
            .distinct()
            .all()
        )
        return [r[0] for r in result]
