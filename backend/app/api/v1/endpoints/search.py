"""Search API Endpoints - M13"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import (
    get_current_user,
    get_current_tenant_id,
    require_permissions,
)
from app.models.user import User
from app.services.search_service import SearchService
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"  # keyword, semantic, hybrid
    source_type: Optional[str] = None
    document_type_id: Optional[str] = None
    folder_id: Optional[str] = None
    lifecycle_status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    customer_id: Optional[str] = None
    vendor_id: Optional[str] = None
    tag_ids: Optional[List[str]] = None
    page: int = 1
    page_size: int = 20


class SaveSearchRequest(BaseModel):
    name: str
    query: str
    search_type: str = "hybrid"
    filters: Optional[dict] = None
    notify_on_new_results: bool = False


@router.get("/")
async def search_documents(
    query: str,
    search_type: str = "hybrid",
    source_type: Optional[str] = None,
    document_type_id: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Search documents with keyword, semantic, or hybrid mode"""
    service = SearchService(db)

    filters = {}
    if source_type:
        filters["source_type"] = source_type
    if document_type_id:
        filters["document_type_id"] = document_type_id
    if lifecycle_status:
        filters["lifecycle_status"] = lifecycle_status

    return service.search(
        query=query,
        tenant_id=tenant_id,
        user_id=current_user.id,
        search_type=search_type,
        filters=filters,
        page=page,
        page_size=page_size,
        user_clearance_level=current_user.clearance_level or "PUBLIC",
    )


@router.post("/advanced")
async def advanced_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["search:advanced"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Advanced search with full filter options"""
    service = SearchService(db)

    filters = {
        "source_type": request.source_type,
        "document_type_id": request.document_type_id,
        "folder_id": request.folder_id,
        "lifecycle_status": request.lifecycle_status,
        "date_from": request.date_from,
        "date_to": request.date_to,
        "customer_id": request.customer_id,
        "vendor_id": request.vendor_id,
        "tag_ids": request.tag_ids,
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    return service.search(
        query=request.query,
        tenant_id=tenant_id,
        user_id=current_user.id,
        search_type=request.search_type,
        filters=filters,
        page=request.page,
        page_size=request.page_size,
        user_clearance_level=current_user.clearance_level or "PUBLIC",
    )


@router.get("/suggestions")
async def get_suggestions(
    prefix: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get search suggestions based on prefix"""
    service = SearchService(db)
    suggestions = service.get_suggestions(prefix, tenant_id)
    return {"suggestions": suggestions}


@router.get("/recent")
async def get_recent_searches(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get user's recent searches"""
    service = SearchService(db)
    recent = service.get_recent_searches(current_user.id, tenant_id, limit)
    return {"recent": recent}


# Saved Searches
@router.post("/saved")
async def save_search(
    request: SaveSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Save a search for later use"""
    service = SearchService(db)
    saved = service.save_search(
        user_id=current_user.id,
        tenant_id=tenant_id,
        name=request.name,
        query=request.query,
        filters=request.filters,
        search_type=request.search_type,
        notify_on_new=request.notify_on_new_results,
    )
    return saved


@router.get("/saved")
async def get_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get user's saved searches"""
    service = SearchService(db)
    return service.get_saved_searches(current_user.id, tenant_id)


@router.delete("/saved/{search_id}")
async def delete_saved_search(
    search_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Delete a saved search"""
    service = SearchService(db)
    service.delete_saved_search(search_id, current_user.id, tenant_id)
    return {"message": "Search deleted"}
