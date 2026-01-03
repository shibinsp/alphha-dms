"""Config options API for managing dropdown values."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.models import ConfigOption, User
import uuid

router = APIRouter(prefix="/config", tags=["config"])


class ConfigOptionCreate(BaseModel):
    category: str
    value: str
    label: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0


class ConfigOptionUpdate(BaseModel):
    value: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ConfigOptionResponse(BaseModel):
    id: str
    category: str
    value: str
    label: str
    description: Optional[str]
    color: Optional[str]
    icon: Optional[str]
    sort_order: int
    is_active: bool
    is_system: bool

    class Config:
        from_attributes = True


@router.get("/options", response_model=List[ConfigOptionResponse])
def list_options(
    category: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List config options, optionally filtered by category."""
    query = db.query(ConfigOption).filter(ConfigOption.tenant_id == current_user.tenant_id)
    if category:
        query = query.filter(ConfigOption.category == category)
    if not include_inactive:
        query = query.filter(ConfigOption.is_active == True)
    return query.order_by(ConfigOption.category, ConfigOption.sort_order).all()


@router.post("/options", response_model=ConfigOptionResponse)
def create_option(
    data: ConfigOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new config option."""
    option = ConfigOption(
        id=str(uuid.uuid4()),
        tenant_id=current_user.tenant_id,
        **data.model_dump()
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.put("/options/{option_id}", response_model=ConfigOptionResponse)
def update_option(
    option_id: str,
    data: ConfigOptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a config option."""
    option = db.query(ConfigOption).filter(
        ConfigOption.id == option_id,
        ConfigOption.tenant_id == current_user.tenant_id
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(option, key, value)
    db.commit()
    db.refresh(option)
    return option


@router.delete("/options/{option_id}")
def delete_option(
    option_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a config option (soft delete by setting inactive)."""
    option = db.query(ConfigOption).filter(
        ConfigOption.id == option_id,
        ConfigOption.tenant_id == current_user.tenant_id
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    if option.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system option")
    
    db.delete(option)
    db.commit()
    return {"status": "deleted"}


@router.post("/options/seed-defaults")
def seed_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seed default config options for tenant."""
    defaults = [
        # Source Types
        {"category": "source_type", "value": "CUSTOMER", "label": "Customer", "color": "#1890ff", "is_system": True},
        {"category": "source_type", "value": "VENDOR", "label": "Vendor", "color": "#52c41a", "is_system": True},
        {"category": "source_type", "value": "INTERNAL", "label": "Internal", "color": "#722ed1", "is_system": True},
        # Classifications
        {"category": "classification", "value": "PUBLIC", "label": "Public", "color": "#52c41a", "is_system": True},
        {"category": "classification", "value": "INTERNAL", "label": "Internal", "color": "#1890ff", "is_system": True},
        {"category": "classification", "value": "CONFIDENTIAL", "label": "Confidential", "color": "#fa8c16", "is_system": True},
        {"category": "classification", "value": "RESTRICTED", "label": "Restricted", "color": "#f5222d", "is_system": True},
    ]
    
    created = 0
    for d in defaults:
        exists = db.query(ConfigOption).filter(
            ConfigOption.tenant_id == current_user.tenant_id,
            ConfigOption.category == d["category"],
            ConfigOption.value == d["value"]
        ).first()
        if not exists:
            option = ConfigOption(
                id=str(uuid.uuid4()),
                tenant_id=current_user.tenant_id,
                sort_order=created,
                **d
            )
            db.add(option)
            created += 1
    
    db.commit()
    return {"created": created}
