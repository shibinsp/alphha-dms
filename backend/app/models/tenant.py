import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, Boolean, DateTime, Date, JSON, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    """Multi-tenant organization model."""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False, index=True)

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True, default="#1E3A5F")

    # Configuration
    config = Column(JSON, default={})

    # License
    license_key = Column(String(255), nullable=False)
    license_expires = Column(Date, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", lazy="dynamic")
    roles = relationship("Role", back_populates="tenant", lazy="dynamic")
    documents = relationship("Document", back_populates="tenant", lazy="dynamic")
    document_types = relationship("DocumentType", back_populates="tenant", lazy="dynamic")
    folders = relationship("Folder", back_populates="tenant", lazy="dynamic")
    departments = relationship("Department", back_populates="tenant", lazy="dynamic")

    def __repr__(self):
        return f"<Tenant {self.name}>"

    @property
    def is_license_valid(self) -> bool:
        """Check if tenant license is valid."""
        if not self.license_expires:
            return True
        return self.license_expires >= date.today()
