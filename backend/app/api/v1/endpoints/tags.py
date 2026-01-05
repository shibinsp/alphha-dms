"""Tags API Endpoints - M11 Auto-Tagging & Taxonomy"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.models.taxonomy import TagType
from app.services.tagging_service import TaggingService


router = APIRouter(prefix="/tags", tags=["Tags"])


# ==================== Schemas ====================

class TagCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_controlled: bool = False
    requires_approval: bool = False


class TagUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_controlled: Optional[bool] = None
    requires_approval: Optional[bool] = None


class TagResponse(BaseModel):
    id: str
    name: str
    slug: str
    category: Optional[str]
    description: Optional[str]
    color: Optional[str]
    parent_id: Optional[str]
    usage_count: int
    is_controlled: bool
    requires_approval: bool

    class Config:
        from_attributes = True


class DocumentTagCreate(BaseModel):
    tag_id: str


class DocumentTagResponse(BaseModel):
    id: str
    document_id: str
    tag_id: str
    tag_type: str
    confidence_score: Optional[float]
    tag: TagResponse

    class Config:
        from_attributes = True


class TagSuggestionResponse(BaseModel):
    id: str
    document_id: str
    suggested_tag_name: str
    suggested_tag_id: Optional[str]
    confidence_score: float
    source: Optional[str]
    status: str

    class Config:
        from_attributes = True


class SynonymCreate(BaseModel):
    synonym: str


class SynonymResponse(BaseModel):
    id: str
    tag_id: str
    synonym: str

    class Config:
        from_attributes = True


class BulkApproveRequest(BaseModel):
    suggestion_ids: List[str]


# ==================== Tag CRUD ====================

@router.get("/", response_model=List[TagResponse])
def list_tags(
    category: Optional[str] = None,
    search: Optional[str] = None,
    parent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """List all tags for the tenant"""
    service = TaggingService(db)
    tags = service.get_tags(
        tenant_id=tenant.id,
        category=category,
        search=search,
        parent_id=parent_id,
    )
    return tags


@router.post("/", response_model=TagResponse)
def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Create a new tag"""
    service = TaggingService(db)
    tag = service.create_tag(
        tenant_id=tenant.id,
        user_id=current_user.id,
        **tag_data.model_dump(),
    )
    return tag


@router.get("/categories", response_model=List[str])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get all tag categories"""
    service = TaggingService(db)
    return service.get_tag_categories(tenant.id)


@router.get("/popular", response_model=List[TagResponse])
def get_popular_tags(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get most popular tags"""
    service = TaggingService(db)
    return service.get_popular_tags(tenant.id, limit)


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get a tag by ID"""
    service = TaggingService(db)
    return service.get_tag(tag_id, tenant.id)


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Update a tag"""
    service = TaggingService(db)
    return service.update_tag(
        tag_id=tag_id,
        tenant_id=tenant.id,
        **tag_data.model_dump(exclude_unset=True),
    )


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Delete a tag"""
    service = TaggingService(db)
    service.delete_tag(tag_id, tenant.id)
    return {"success": True, "message": "Tag deleted"}


# ==================== Document Tagging ====================

@router.get("/documents/{document_id}/tags", response_model=List[DocumentTagResponse])
def get_document_tags(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get all tags for a document"""
    service = TaggingService(db)
    return service.get_document_tags(document_id, tenant.id)


@router.post("/documents/{document_id}/tags", response_model=DocumentTagResponse)
def add_tag_to_document(
    document_id: str,
    data: DocumentTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Add a tag to a document"""
    service = TaggingService(db)
    return service.add_tag_to_document(
        document_id=document_id,
        tag_id=data.tag_id,
        user_id=current_user.id,
        tenant_id=tenant.id,
        tag_type=TagType.MANUAL,
    )


@router.delete("/documents/{document_id}/tags/{tag_id}")
def remove_tag_from_document(
    document_id: str,
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Remove a tag from a document"""
    service = TaggingService(db)
    service.remove_tag_from_document(document_id, tag_id, tenant.id)
    return {"success": True, "message": "Tag removed from document"}


# ==================== Auto-Tagging ====================

@router.post("/documents/{document_id}/auto-tag", response_model=List[TagSuggestionResponse])
async def auto_tag_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Trigger auto-tagging for a document using NER"""
    service = TaggingService(db)
    suggestions = await service.auto_tag_document(document_id, tenant.id)
    return suggestions


# ==================== Suggestions ====================

@router.get("/suggestions", response_model=List[TagSuggestionResponse])
def get_pending_suggestions(
    document_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get pending tag suggestions for review"""
    service = TaggingService(db)
    return service.get_pending_suggestions(tenant.id, document_id, limit)


@router.post("/suggestions/{suggestion_id}/approve", response_model=DocumentTagResponse)
def approve_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Approve a tag suggestion"""
    service = TaggingService(db)
    return service.approve_suggestion(suggestion_id, current_user.id, tenant.id)


@router.post("/suggestions/{suggestion_id}/reject", response_model=TagSuggestionResponse)
def reject_suggestion(
    suggestion_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Reject a tag suggestion"""
    service = TaggingService(db)
    return service.reject_suggestion(suggestion_id, current_user.id, tenant.id, reason)


@router.post("/suggestions/bulk-approve")
def bulk_approve_suggestions(
    data: BulkApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Approve multiple suggestions at once"""
    service = TaggingService(db)
    approved_count = service.bulk_approve_suggestions(
        data.suggestion_ids, current_user.id, tenant.id
    )
    return {"success": True, "approved_count": approved_count}


# ==================== Synonyms ====================

@router.post("/{tag_id}/synonyms", response_model=SynonymResponse)
def add_synonym(
    tag_id: str,
    data: SynonymCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Add a synonym to a tag"""
    service = TaggingService(db)
    return service.add_synonym(tag_id, data.synonym, tenant.id)


@router.delete("/{tag_id}/synonyms/{synonym_id}")
def remove_synonym(
    tag_id: str,
    synonym_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Remove a synonym from a tag"""
    service = TaggingService(db)
    service.remove_synonym(synonym_id, tenant.id)
    return {"success": True, "message": "Synonym removed"}
