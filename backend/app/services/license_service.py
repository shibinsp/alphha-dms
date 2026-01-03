"""License Management Service."""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.entities import License
from app.models import Tenant


class LicenseService:
    """Service for license key management."""

    @staticmethod
    def generate_license_key(tenant_id: str, validity_days: int = 365) -> str:
        """Generate a new license key."""
        # Create unique key components
        timestamp = datetime.utcnow().isoformat()
        random_part = secrets.token_hex(16)
        raw_key = f"{tenant_id}:{timestamp}:{random_part}"
        
        # Create formatted license key
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()[:32].upper()
        formatted_key = f"ADMS-{key_hash[:8]}-{key_hash[8:16]}-{key_hash[16:24]}-{key_hash[24:32]}"
        
        return formatted_key

    @staticmethod
    def create_license(
        db: Session,
        tenant_id: str,
        validity_days: int = 365,
        grace_period_days: int = 30
    ) -> License:
        """Create a new license for a tenant."""
        license_key = LicenseService.generate_license_key(tenant_id, validity_days)
        expires_at = datetime.utcnow() + timedelta(days=validity_days)
        
        # Create checksum for tamper detection
        checksum_data = f"{license_key}:{tenant_id}:{expires_at.isoformat()}"
        checksum = hashlib.sha256(checksum_data.encode()).hexdigest()
        
        license = License(
            license_key=license_key,
            tenant_id=tenant_id,
            expires_at=expires_at,
            grace_period_days=grace_period_days,
            checksum=checksum
        )
        
        db.add(license)
        db.commit()
        return license

    @staticmethod
    def validate_license(db: Session, license_key: str) -> dict:
        """Validate a license key."""
        license = db.query(License).filter(
            License.license_key == license_key
        ).first()
        
        if not license:
            return {
                "is_valid": False,
                "message": "License key not found",
                "expires_at": None,
                "days_remaining": None,
                "in_grace_period": False
            }
        
        # Check for tampering
        checksum_data = f"{license.license_key}:{license.tenant_id}:{license.expires_at.isoformat()}"
        expected_checksum = hashlib.sha256(checksum_data.encode()).hexdigest()
        
        if license.checksum != expected_checksum or license.is_tampered:
            license.is_tampered = True
            license.is_active = False
            db.commit()
            return {
                "is_valid": False,
                "message": "License has been tampered with. Platform locked.",
                "expires_at": None,
                "days_remaining": None,
                "in_grace_period": False
            }
        
        if not license.is_active:
            return {
                "is_valid": False,
                "message": "License is deactivated",
                "expires_at": license.expires_at,
                "days_remaining": None,
                "in_grace_period": False
            }
        
        now = datetime.utcnow()
        days_remaining = (license.expires_at - now).days
        grace_end = license.expires_at + timedelta(days=license.grace_period_days)
        
        # Update validation timestamp
        license.last_validated_at = now
        db.commit()
        
        if now > grace_end:
            # Past grace period - lock platform
            license.is_active = False
            db.commit()
            return {
                "is_valid": False,
                "message": "License expired and grace period ended. Platform locked.",
                "expires_at": license.expires_at,
                "days_remaining": days_remaining,
                "in_grace_period": False
            }
        
        if now > license.expires_at:
            # In grace period
            grace_days_remaining = (grace_end - now).days
            return {
                "is_valid": True,
                "message": f"License expired. {grace_days_remaining} days remaining in grace period.",
                "expires_at": license.expires_at,
                "days_remaining": days_remaining,
                "in_grace_period": True
            }
        
        return {
            "is_valid": True,
            "message": "License is valid",
            "expires_at": license.expires_at,
            "days_remaining": days_remaining,
            "in_grace_period": False
        }

    @staticmethod
    def renew_license(
        db: Session,
        license_key: str,
        additional_days: int = 365
    ) -> Optional[License]:
        """Renew an existing license."""
        license = db.query(License).filter(
            License.license_key == license_key
        ).first()
        
        if not license:
            return None
        
        # Extend from current expiry or now, whichever is later
        base_date = max(license.expires_at, datetime.utcnow())
        license.expires_at = base_date + timedelta(days=additional_days)
        license.is_active = True
        license.is_tampered = False
        license.validation_failures = 0
        
        # Update checksum
        checksum_data = f"{license.license_key}:{license.tenant_id}:{license.expires_at.isoformat()}"
        license.checksum = hashlib.sha256(checksum_data.encode()).hexdigest()
        
        db.commit()
        return license

    @staticmethod
    def get_tenant_license(db: Session, tenant_id: str) -> Optional[License]:
        """Get the active license for a tenant."""
        return db.query(License).filter(
            License.tenant_id == tenant_id,
            License.is_active == True
        ).first()

    @staticmethod
    def check_platform_access(db: Session, tenant_id: str) -> dict:
        """Check if platform access is allowed for a tenant."""
        license = LicenseService.get_tenant_license(db, tenant_id)
        
        if not license:
            return {
                "allowed": False,
                "reason": "No active license found"
            }
        
        validation = LicenseService.validate_license(db, license.license_key)
        
        return {
            "allowed": validation["is_valid"],
            "reason": validation["message"],
            "expires_at": validation["expires_at"],
            "in_grace_period": validation["in_grace_period"]
        }
