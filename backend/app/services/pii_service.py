"""PII Detection Service - M09"""
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.pii import (
    PIIPattern,
    PIIPolicy,
    DocumentPIIField,
    PIIAccessLog,
    PIIType,
    PIIAction,
)
from app.schemas.pii import (
    PIIPatternCreate,
    PIIPatternUpdate,
    PIIPolicyCreate,
    PIIPolicyUpdate,
    PIIDetectionResult,
)
from app.utils.encryption import encrypt_value, decrypt_value


# Built-in PII patterns
SYSTEM_PATTERNS = [
    {
        "name": "Credit Card",
        "pii_type": PIIType.CREDIT_CARD,
        "regex_pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "validator_function": "luhn_check",
        "mask_format": "****-****-****-{last4}",
        "sensitivity_level": "CRITICAL",
    },
    {
        "name": "Email Address",
        "pii_type": PIIType.EMAIL,
        "regex_pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "mask_format": "{first2}***@***",
        "sensitivity_level": "MEDIUM",
    },
    {
        "name": "Phone Number",
        "pii_type": PIIType.PHONE,
        "regex_pattern": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "mask_format": "***-***-{last4}",
        "sensitivity_level": "MEDIUM",
    },
    {
        "name": "Aadhaar Number",
        "pii_type": PIIType.AADHAAR,
        "regex_pattern": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "validator_function": "verhoeff_check",
        "mask_format": "****-****-{last4}",
        "sensitivity_level": "CRITICAL",
    },
    {
        "name": "PAN Card",
        "pii_type": PIIType.PAN,
        "regex_pattern": r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "mask_format": "{first2}***{last2}",
        "sensitivity_level": "HIGH",
    },
    {
        "name": "SSN (US)",
        "pii_type": PIIType.SSN,
        "regex_pattern": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "mask_format": "***-**-{last4}",
        "sensitivity_level": "CRITICAL",
    },
    {
        "name": "IBAN",
        "pii_type": PIIType.IBAN,
        "regex_pattern": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b",
        "mask_format": "{first4}****{last4}",
        "sensitivity_level": "HIGH",
    },
    {
        "name": "Passport Number",
        "pii_type": PIIType.PASSPORT,
        "regex_pattern": r"\b[A-Z]{1,2}\d{6,9}\b",
        "mask_format": "{first1}*****{last2}",
        "sensitivity_level": "HIGH",
    },
]


class PIIService:
    def __init__(self, db: Session):
        self.db = db

    # Pattern Management
    def initialize_system_patterns(self, tenant_id: str) -> None:
        """Create system PII patterns for a tenant"""
        for pattern_data in SYSTEM_PATTERNS:
            existing = (
                self.db.query(PIIPattern)
                .filter(
                    PIIPattern.tenant_id == tenant_id,
                    PIIPattern.pii_type == pattern_data["pii_type"],
                    PIIPattern.is_system == True,
                )
                .first()
            )
            if not existing:
                pattern = PIIPattern(
                    tenant_id=tenant_id,
                    is_system=True,
                    **pattern_data,
                )
                self.db.add(pattern)
        self.db.commit()

    def create_pattern(
        self,
        tenant_id: str,
        data: PIIPatternCreate,
    ) -> PIIPattern:
        pattern = PIIPattern(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.db.add(pattern)
        self.db.commit()
        self.db.refresh(pattern)
        return pattern

    def get_patterns(
        self,
        tenant_id: str,
        is_active: Optional[bool] = None,
        pii_type: Optional[PIIType] = None,
    ) -> List[PIIPattern]:
        query = self.db.query(PIIPattern).filter(PIIPattern.tenant_id == tenant_id)
        if is_active is not None:
            query = query.filter(PIIPattern.is_active == is_active)
        if pii_type:
            query = query.filter(PIIPattern.pii_type == pii_type)
        return query.all()

    def update_pattern(
        self,
        pattern_id: str,
        tenant_id: str,
        data: PIIPatternUpdate,
    ) -> PIIPattern:
        pattern = (
            self.db.query(PIIPattern)
            .filter(PIIPattern.id == pattern_id, PIIPattern.tenant_id == tenant_id)
            .first()
        )
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        if pattern.is_system:
            raise HTTPException(status_code=400, detail="Cannot modify system patterns")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(pattern, field, value)

        self.db.commit()
        self.db.refresh(pattern)
        return pattern

    def delete_pattern(self, pattern_id: str, tenant_id: str) -> bool:
        pattern = (
            self.db.query(PIIPattern)
            .filter(PIIPattern.id == pattern_id, PIIPattern.tenant_id == tenant_id)
            .first()
        )
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        if pattern.is_system:
            raise HTTPException(status_code=400, detail="Cannot delete system patterns")

        self.db.delete(pattern)
        self.db.commit()
        return True

    # Policy Management
    def create_policy(
        self,
        tenant_id: str,
        data: PIIPolicyCreate,
    ) -> PIIPolicy:
        policy = PIIPolicy(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            pii_types=[t.value for t in data.pii_types],
            document_type_ids=data.document_type_ids,
            action=data.action,
            exception_role_ids=data.exception_role_ids,
            notify_on_detection=data.notify_on_detection,
            notify_roles=data.notify_roles,
            priority=data.priority,
            is_active=data.is_active,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_policies(
        self,
        tenant_id: str,
        is_active: Optional[bool] = None,
    ) -> List[PIIPolicy]:
        query = self.db.query(PIIPolicy).filter(PIIPolicy.tenant_id == tenant_id)
        if is_active is not None:
            query = query.filter(PIIPolicy.is_active == is_active)
        return query.order_by(PIIPolicy.priority.desc()).all()

    def update_policy(
        self,
        policy_id: str,
        tenant_id: str,
        data: PIIPolicyUpdate,
    ) -> PIIPolicy:
        policy = (
            self.db.query(PIIPolicy)
            .filter(PIIPolicy.id == policy_id, PIIPolicy.tenant_id == tenant_id)
            .first()
        )
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        update_data = data.model_dump(exclude_unset=True)
        if "pii_types" in update_data:
            update_data["pii_types"] = [t.value for t in update_data["pii_types"]]

        for field, value in update_data.items():
            setattr(policy, field, value)

        self.db.commit()
        self.db.refresh(policy)
        return policy

    # Detection
    def detect_pii(
        self,
        content: str,
        tenant_id: str,
        detect_types: Optional[List[PIIType]] = None,
    ) -> List[PIIDetectionResult]:
        """Detect PII in text content"""
        patterns = self.get_patterns(tenant_id, is_active=True)
        if detect_types:
            patterns = [p for p in patterns if p.pii_type in detect_types]

        results = []
        for pattern in patterns:
            try:
                regex = re.compile(pattern.regex_pattern, re.IGNORECASE)
                for match in regex.finditer(content):
                    original = match.group()
                    masked = self._mask_value(original, pattern)

                    # Run validator if specified
                    confidence = 0.9
                    if pattern.validator_function:
                        if not self._run_validator(original, pattern.validator_function):
                            confidence = 0.5

                    results.append(
                        PIIDetectionResult(
                            pii_type=pattern.pii_type,
                            original_value=original,
                            masked_value=masked,
                            position_start=match.start(),
                            position_end=match.end(),
                            confidence_score=confidence,
                        )
                    )
            except re.error:
                continue

        return results

    def scan_document(
        self,
        document_id: str,
        content: str,
        tenant_id: str,
        user_id: str,
    ) -> List[DocumentPIIField]:
        """Scan document content and store detected PII"""
        detections = self.detect_pii(content, tenant_id)

        # Get applicable policy
        policy = self._get_applicable_policy(tenant_id)
        action = policy.action if policy else PIIAction.MASK

        pii_fields = []
        for detection in detections:
            encrypted = encrypt_value(detection.original_value)

            pii_field = DocumentPIIField(
                document_id=document_id,
                pii_type=detection.pii_type,
                encrypted_value=encrypted,
                masked_value=detection.masked_value,
                position_start=detection.position_start,
                position_end=detection.position_end,
                confidence_score=str(detection.confidence_score),
                action_taken=action,
                detected_by="AUTO",
            )
            self.db.add(pii_field)
            pii_fields.append(pii_field)

        self.db.commit()
        return pii_fields

    def get_document_pii(
        self,
        document_id: str,
        user_id: str,
        tenant_id: str,
        user_role_ids: List[str],
        include_unmasked: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get PII fields for a document, respecting access controls"""
        pii_fields = (
            self.db.query(DocumentPIIField)
            .filter(DocumentPIIField.document_id == document_id)
            .all()
        )

        # Check if user has exception to see unmasked values
        can_see_unmasked = False
        if include_unmasked:
            policy = self._get_applicable_policy(tenant_id)
            if policy and policy.exception_role_ids:
                can_see_unmasked = any(
                    role_id in policy.exception_role_ids for role_id in user_role_ids
                )

        results = []
        for field in pii_fields:
            result = {
                "id": field.id,
                "pii_type": field.pii_type,
                "masked_value": field.masked_value,
                "position_start": field.position_start,
                "position_end": field.position_end,
                "confidence_score": field.confidence_score,
            }

            if can_see_unmasked and field.encrypted_value:
                result["original_value"] = decrypt_value(field.encrypted_value)
                # Log access
                self._log_pii_access(
                    tenant_id=tenant_id,
                    pii_field_id=field.id,
                    document_id=document_id,
                    user_id=user_id,
                    access_type="VIEW_UNMASKED",
                    saw_unmasked=True,
                )
            else:
                self._log_pii_access(
                    tenant_id=tenant_id,
                    pii_field_id=field.id,
                    document_id=document_id,
                    user_id=user_id,
                    access_type="VIEW_MASKED",
                    saw_unmasked=False,
                )

            results.append(result)

        return results

    # Helper methods
    def _mask_value(self, value: str, pattern: PIIPattern) -> str:
        """Apply masking format to a value"""
        if not pattern.mask_format:
            mask_char = pattern.mask_char or "*"
            if len(value) <= 4:
                return mask_char * len(value)
            return mask_char * (len(value) - 4) + value[-4:]

        mask_format = pattern.mask_format
        clean_value = re.sub(r"[-\s]", "", value)

        # Replace placeholders
        result = mask_format
        result = result.replace("{last4}", clean_value[-4:] if len(clean_value) >= 4 else clean_value)
        result = result.replace("{last2}", clean_value[-2:] if len(clean_value) >= 2 else clean_value)
        result = result.replace("{first2}", clean_value[:2] if len(clean_value) >= 2 else clean_value)
        result = result.replace("{first4}", clean_value[:4] if len(clean_value) >= 4 else clean_value)
        result = result.replace("{first1}", clean_value[:1] if len(clean_value) >= 1 else clean_value)

        return result

    def _run_validator(self, value: str, validator: str) -> bool:
        """Run validation function on a value"""
        clean_value = re.sub(r"[-\s]", "", value)

        if validator == "luhn_check":
            return self._luhn_check(clean_value)
        elif validator == "verhoeff_check":
            return self._verhoeff_check(clean_value)

        return True

    def _luhn_check(self, number: str) -> bool:
        """Luhn algorithm for credit card validation"""
        try:
            digits = [int(d) for d in number]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(divmod(d * 2, 10))
            return checksum % 10 == 0
        except ValueError:
            return False

    def _verhoeff_check(self, number: str) -> bool:
        """Verhoeff algorithm for Aadhaar validation (simplified)"""
        try:
            digits = [int(d) for d in number]
            return len(digits) == 12
        except ValueError:
            return False

    def _get_applicable_policy(self, tenant_id: str) -> Optional[PIIPolicy]:
        """Get the highest priority active policy"""
        return (
            self.db.query(PIIPolicy)
            .filter(PIIPolicy.tenant_id == tenant_id, PIIPolicy.is_active == True)
            .order_by(PIIPolicy.priority.desc())
            .first()
        )

    def _log_pii_access(
        self,
        tenant_id: str,
        pii_field_id: str,
        document_id: str,
        user_id: str,
        access_type: str,
        saw_unmasked: bool,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log PII access for audit purposes"""
        log = PIIAccessLog(
            tenant_id=tenant_id,
            pii_field_id=pii_field_id,
            document_id=document_id,
            accessed_by=user_id,
            access_type=access_type,
            saw_unmasked=saw_unmasked,
            reason=reason,
            ip_address=ip_address,
        )
        self.db.add(log)
        self.db.commit()
