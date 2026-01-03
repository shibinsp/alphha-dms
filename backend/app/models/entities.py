"""Customer, Vendor, and Entity Models for Document Source Classification."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Boolean, Index, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    """Customer entity linked from CRM."""
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = Column(String(100), nullable=False, index=True)  # CRM Customer ID
    
    # Basic info (synced from CRM)
    name = Column(String(255), nullable=False)
    id_number = Column(String(50), nullable=True)  # National ID/Passport
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    
    # Additional CRM data
    crm_data = Column(JSON, default={})
    
    # Sync tracking
    last_synced_at = Column(DateTime, nullable=True)
    
    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_customer_external", "tenant_id", "external_id", unique=True),
    )

    def __repr__(self):
        return f"<Customer {self.name}>"


class Vendor(Base):
    """Vendor entity linked from ERP."""
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = Column(String(100), nullable=False, index=True)  # ERP Vendor ID
    
    # Basic info
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    
    # Additional ERP data
    erp_data = Column(JSON, default={})
    
    # Sync tracking
    last_synced_at = Column(DateTime, nullable=True)
    
    # Tenant
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_vendor_external", "tenant_id", "external_id", unique=True),
    )

    def __repr__(self):
        return f"<Vendor {self.name}>"


class License(Base):
    """License key management for deployment."""
    __tablename__ = "licenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_key = Column(String(255), unique=True, nullable=False)
    
    # License details
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    grace_period_days = Column(Integer, default=30)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_tampered = Column(Boolean, default=False)
    
    # Validation
    checksum = Column(String(64), nullable=False)  # SHA256 of license data
    last_validated_at = Column(DateTime, nullable=True)
    validation_failures = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<License {self.license_key[:8]}...>"
