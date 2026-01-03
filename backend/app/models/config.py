"""Dynamic configuration options for dropdowns."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from app.core.database import Base


class ConfigOption(Base):
    """Configurable dropdown options."""
    __tablename__ = "config_options"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # source_type, classification, folder
    value = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)  # For UI display
    icon = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System defaults can't be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
