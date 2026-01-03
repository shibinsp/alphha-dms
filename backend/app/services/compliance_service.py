"""Compliance Service - M06 WORM, M07 Retention, M08 Legal Hold"""
import os
import json
import zipfile
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException

from app.models.document import Document, LifecycleStatus
from app.models.compliance import (
    WORMRecord,
    RetentionPolicy,
    PolicyExecutionLog,
    LegalHold,
    LegalHoldDocument,
    EvidenceExport,
    RetentionUnit,
    RetentionAction,
    LegalHoldStatus,
)
from app.schemas.compliance import (
    WORMLockRequest,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    LegalHoldCreate,
    EvidenceExportCreate,
)
from app.utils.hashing import hash_file, hash_string
from app.services.audit_service import AuditService
from app.core.config import settings


class ComplianceService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    # M06 - WORM Records
    def lock_document_worm(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        data: WORMLockRequest,
    ) -> WORMRecord:
        """Lock a document with WORM protection"""
        document = (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.tenant_id == tenant_id)
            .first()
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Check if already locked
        existing = (
            self.db.query(WORMRecord)
            .filter(WORMRecord.document_id == document_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Document is already WORM locked")

        # Check if under legal hold
        if document.legal_hold:
            raise HTTPException(
                status_code=400,
                detail="Cannot WORM lock document under legal hold",
            )

        # Calculate content hash
        file_path = os.path.join(settings.UPLOAD_DIR, document.storage_path)
        if os.path.exists(file_path):
            content_hash = hash_file(file_path)
        else:
            content_hash = document.content_hash or hash_string(document.id)

        # Create WORM record
        worm_record = WORMRecord(
            document_id=document_id,
            tenant_id=tenant_id,
            locked_by=user_id,
            lock_reason=data.lock_reason,
            retention_until=data.retention_until,
            content_hash=content_hash,
        )
        self.db.add(worm_record)

        # Update document
        document.is_worm_locked = True

        self.db.commit()
        self.db.refresh(worm_record)

        self.audit_service.log_event(
            event_type="WORM_LOCKED",
            entity_type="document",
            entity_id=document_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={
                "retention_until": data.retention_until.isoformat(),
                "content_hash": content_hash,
            },
        )

        return worm_record

    def verify_worm_integrity(
        self,
        document_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Verify WORM document integrity"""
        worm_record = (
            self.db.query(WORMRecord)
            .filter(WORMRecord.document_id == document_id)
            .first()
        )
        if not worm_record:
            raise HTTPException(status_code=404, detail="Document is not WORM locked")

        document = (
            self.db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        # Calculate current hash
        file_path = os.path.join(settings.UPLOAD_DIR, document.storage_path)
        if os.path.exists(file_path):
            current_hash = hash_file(file_path)
        else:
            current_hash = "FILE_NOT_FOUND"

        is_valid = current_hash == worm_record.content_hash

        # Update verification record
        worm_record.last_verified_at = datetime.utcnow()
        worm_record.last_verified_hash = current_hash
        worm_record.verification_count += 1
        self.db.commit()

        return {
            "document_id": document_id,
            "is_valid": is_valid,
            "original_hash": worm_record.content_hash,
            "current_hash": current_hash,
            "verified_at": datetime.utcnow(),
            "message": "Integrity verified" if is_valid else "INTEGRITY VIOLATION DETECTED",
        }

    def extend_worm_retention(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        new_retention_until: datetime,
        reason: Optional[str] = None,
    ) -> WORMRecord:
        """Extend WORM retention period (cannot shorten)"""
        worm_record = (
            self.db.query(WORMRecord)
            .filter(WORMRecord.document_id == document_id)
            .first()
        )
        if not worm_record:
            raise HTTPException(status_code=404, detail="Document is not WORM locked")

        if new_retention_until <= worm_record.retention_until:
            raise HTTPException(
                status_code=400,
                detail="New retention date must be after current retention date",
            )

        # Store original if first extension
        if not worm_record.retention_extended:
            worm_record.original_retention_until = worm_record.retention_until
            worm_record.retention_extended = True

        old_date = worm_record.retention_until
        worm_record.retention_until = new_retention_until

        self.db.commit()
        self.db.refresh(worm_record)

        self.audit_service.log_event(
            event_type="WORM_EXTENDED",
            entity_type="document",
            entity_id=document_id,
            user_id=user_id,
            tenant_id=tenant_id,
            old_values={"retention_until": old_date.isoformat()},
            new_values={
                "retention_until": new_retention_until.isoformat(),
                "reason": reason,
            },
        )

        return worm_record

    # M07 - Retention Policies
    def create_retention_policy(
        self,
        tenant_id: str,
        user_id: str,
        data: RetentionPolicyCreate,
    ) -> RetentionPolicy:
        policy = RetentionPolicy(
            tenant_id=tenant_id,
            created_by=user_id,
            **data.model_dump(),
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        self.audit_service.log_event(
            event_type="RETENTION_POLICY_CREATED",
            entity_type="retention_policy",
            entity_id=policy.id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={"name": policy.name, "action": policy.expiry_action.value},
        )

        return policy

    def get_retention_policies(
        self,
        tenant_id: str,
        is_active: Optional[bool] = None,
    ) -> List[RetentionPolicy]:
        query = self.db.query(RetentionPolicy).filter(
            RetentionPolicy.tenant_id == tenant_id
        )
        if is_active is not None:
            query = query.filter(RetentionPolicy.is_active == is_active)
        return query.order_by(RetentionPolicy.priority.desc()).all()

    def update_retention_policy(
        self,
        policy_id: str,
        tenant_id: str,
        user_id: str,
        data: RetentionPolicyUpdate,
    ) -> RetentionPolicy:
        policy = (
            self.db.query(RetentionPolicy)
            .filter(
                RetentionPolicy.id == policy_id,
                RetentionPolicy.tenant_id == tenant_id,
            )
            .first()
        )
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(policy, field, value)

        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_expiring_documents(
        self,
        tenant_id: str,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get documents expiring within specified days"""
        policies = self.get_retention_policies(tenant_id, is_active=True)
        expiring = []

        for policy in policies:
            # Calculate retention period in days
            if policy.retention_unit == RetentionUnit.DAYS:
                retention_days = policy.retention_period
            elif policy.retention_unit == RetentionUnit.MONTHS:
                retention_days = policy.retention_period * 30
            else:  # YEARS
                retention_days = policy.retention_period * 365

            cutoff_date = datetime.utcnow() - timedelta(days=retention_days - days_ahead)

            query = self.db.query(Document).filter(
                Document.tenant_id == tenant_id,
                Document.created_at <= cutoff_date,
                Document.is_worm_locked == False,
                Document.legal_hold == False,
            )

            if policy.document_type_id:
                query = query.filter(Document.document_type_id == policy.document_type_id)
            if policy.source_type:
                query = query.filter(Document.source_type == policy.source_type)
            if policy.classification:
                query = query.filter(Document.classification == policy.classification)

            for doc in query.all():
                expiry_date = doc.created_at + timedelta(days=retention_days)
                days_until = (expiry_date - datetime.utcnow()).days

                expiring.append({
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "policy_name": policy.name,
                    "expiry_date": expiry_date,
                    "days_until_expiry": days_until,
                    "action_on_expiry": policy.expiry_action,
                })

        return expiring

    def execute_retention_policy(
        self,
        policy_id: str,
        tenant_id: str,
        dry_run: bool = True,
    ) -> List[PolicyExecutionLog]:
        """Execute retention policy on matching documents"""
        policy = (
            self.db.query(RetentionPolicy)
            .filter(
                RetentionPolicy.id == policy_id,
                RetentionPolicy.tenant_id == tenant_id,
            )
            .first()
        )
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        # Calculate cutoff date
        if policy.retention_unit == RetentionUnit.DAYS:
            retention_days = policy.retention_period
        elif policy.retention_unit == RetentionUnit.MONTHS:
            retention_days = policy.retention_period * 30
        else:
            retention_days = policy.retention_period * 365

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Find matching documents
        query = self.db.query(Document).filter(
            Document.tenant_id == tenant_id,
            Document.created_at <= cutoff_date,
            Document.is_worm_locked == False,
            Document.legal_hold == False,
        )

        if policy.document_type_id:
            query = query.filter(Document.document_type_id == policy.document_type_id)
        if policy.source_type:
            query = query.filter(Document.source_type == policy.source_type)
        if policy.classification:
            query = query.filter(Document.classification == policy.classification)

        documents = query.all()
        logs = []

        for doc in documents:
            if dry_run:
                log = PolicyExecutionLog(
                    tenant_id=tenant_id,
                    policy_id=policy.id,
                    document_id=doc.id,
                    action_taken=policy.expiry_action,
                    action_status="DRY_RUN",
                    action_result=f"Would {policy.expiry_action.value.lower()} document",
                    executed_by="SYSTEM",
                )
            else:
                try:
                    if policy.expiry_action == RetentionAction.ARCHIVE:
                        doc.lifecycle_status = LifecycleStatus.ARCHIVED
                    elif policy.expiry_action == RetentionAction.DELETE:
                        doc.lifecycle_status = LifecycleStatus.DELETED
                    # REVIEW and EXTEND require manual action

                    log = PolicyExecutionLog(
                        tenant_id=tenant_id,
                        policy_id=policy.id,
                        document_id=doc.id,
                        action_taken=policy.expiry_action,
                        action_status="SUCCESS",
                        executed_by="SYSTEM",
                    )
                except Exception as e:
                    log = PolicyExecutionLog(
                        tenant_id=tenant_id,
                        policy_id=policy.id,
                        document_id=doc.id,
                        action_taken=policy.expiry_action,
                        action_status="FAILED",
                        action_result=str(e),
                        executed_by="SYSTEM",
                    )

            self.db.add(log)
            logs.append(log)

        self.db.commit()
        return logs

    # M08 - Legal Hold
    def create_legal_hold(
        self,
        tenant_id: str,
        user_id: str,
        data: LegalHoldCreate,
    ) -> LegalHold:
        legal_hold = LegalHold(
            tenant_id=tenant_id,
            created_by=user_id,
            hold_name=data.hold_name,
            case_number=data.case_number,
            matter_name=data.matter_name,
            description=data.description,
            legal_counsel=data.legal_counsel,
            counsel_email=data.counsel_email,
            hold_end_date=data.hold_end_date,
            scope_criteria=data.scope_criteria,
        )
        self.db.add(legal_hold)
        self.db.flush()

        # Add specified documents
        if data.document_ids:
            for doc_id in data.document_ids:
                self._add_document_to_hold(legal_hold.id, doc_id, tenant_id, user_id)

        self.db.commit()
        self.db.refresh(legal_hold)

        self.audit_service.log_event(
            event_type="LEGAL_HOLD_CREATED",
            entity_type="legal_hold",
            entity_id=legal_hold.id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={
                "name": legal_hold.hold_name,
                "case_number": legal_hold.case_number,
                "documents_held": legal_hold.documents_held,
            },
        )

        return legal_hold

    def get_legal_holds(
        self,
        tenant_id: str,
        status: Optional[LegalHoldStatus] = None,
    ) -> List[LegalHold]:
        query = self.db.query(LegalHold).filter(LegalHold.tenant_id == tenant_id)
        if status:
            query = query.filter(LegalHold.status == status)
        return query.order_by(LegalHold.created_at.desc()).all()

    def get_legal_hold(
        self,
        hold_id: str,
        tenant_id: str,
    ) -> Optional[LegalHold]:
        return (
            self.db.query(LegalHold)
            .filter(LegalHold.id == hold_id, LegalHold.tenant_id == tenant_id)
            .first()
        )

    def add_documents_to_hold(
        self,
        hold_id: str,
        document_ids: List[str],
        tenant_id: str,
        user_id: str,
    ) -> LegalHold:
        legal_hold = self.get_legal_hold(hold_id, tenant_id)
        if not legal_hold:
            raise HTTPException(status_code=404, detail="Legal hold not found")

        if legal_hold.status != LegalHoldStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Legal hold is not active")

        for doc_id in document_ids:
            self._add_document_to_hold(hold_id, doc_id, tenant_id, user_id)

        self.db.commit()
        self.db.refresh(legal_hold)
        return legal_hold

    def _add_document_to_hold(
        self,
        hold_id: str,
        document_id: str,
        tenant_id: str,
        user_id: str,
    ) -> None:
        document = (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.tenant_id == tenant_id)
            .first()
        )
        if not document:
            return

        # Check if already in this hold
        existing = (
            self.db.query(LegalHoldDocument)
            .filter(
                LegalHoldDocument.legal_hold_id == hold_id,
                LegalHoldDocument.document_id == document_id,
            )
            .first()
        )
        if existing:
            return

        # Create snapshot of metadata
        snapshot = {
            "title": document.title,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "lifecycle_status": document.lifecycle_status.value,
            "created_at": document.created_at.isoformat(),
        }

        hold_doc = LegalHoldDocument(
            legal_hold_id=hold_id,
            document_id=document_id,
            added_by=user_id,
            snapshot_metadata=snapshot,
        )
        self.db.add(hold_doc)

        # Update document
        document.legal_hold = True

        # Update hold statistics
        legal_hold = self.db.query(LegalHold).filter(LegalHold.id == hold_id).first()
        legal_hold.documents_held += 1
        legal_hold.total_size_bytes += document.file_size

    def release_legal_hold(
        self,
        hold_id: str,
        tenant_id: str,
        user_id: str,
        reason: str,
    ) -> LegalHold:
        legal_hold = self.get_legal_hold(hold_id, tenant_id)
        if not legal_hold:
            raise HTTPException(status_code=404, detail="Legal hold not found")

        if legal_hold.status != LegalHoldStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Legal hold is not active")

        # Release all documents
        hold_docs = (
            self.db.query(LegalHoldDocument)
            .filter(LegalHoldDocument.legal_hold_id == hold_id)
            .all()
        )

        for hold_doc in hold_docs:
            document = (
                self.db.query(Document)
                .filter(Document.id == hold_doc.document_id)
                .first()
            )
            if document:
                # Check if document is in any other active holds
                other_holds = (
                    self.db.query(LegalHoldDocument)
                    .join(LegalHold)
                    .filter(
                        LegalHoldDocument.document_id == document.id,
                        LegalHoldDocument.legal_hold_id != hold_id,
                        LegalHold.status == LegalHoldStatus.ACTIVE,
                    )
                    .count()
                )
                if other_holds == 0:
                    document.legal_hold = False

        legal_hold.status = LegalHoldStatus.RELEASED
        legal_hold.released_by = user_id
        legal_hold.released_at = datetime.utcnow()
        legal_hold.release_reason = reason

        self.db.commit()
        self.db.refresh(legal_hold)

        self.audit_service.log_event(
            event_type="LEGAL_HOLD_RELEASED",
            entity_type="legal_hold",
            entity_id=legal_hold.id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={"reason": reason, "documents_released": legal_hold.documents_held},
        )

        return legal_hold

    def create_evidence_export(
        self,
        hold_id: str,
        tenant_id: str,
        user_id: str,
        data: EvidenceExportCreate,
    ) -> EvidenceExport:
        """Create evidence export package for legal hold"""
        legal_hold = self.get_legal_hold(hold_id, tenant_id)
        if not legal_hold:
            raise HTTPException(status_code=404, detail="Legal hold not found")

        # Get documents to export
        if data.document_ids:
            doc_ids = data.document_ids
        else:
            hold_docs = (
                self.db.query(LegalHoldDocument)
                .filter(LegalHoldDocument.legal_hold_id == hold_id)
                .all()
            )
            doc_ids = [hd.document_id for hd in hold_docs]

        documents = (
            self.db.query(Document)
            .filter(Document.id.in_(doc_ids))
            .all()
        )

        # Create export directory
        export_dir = os.path.join(settings.UPLOAD_DIR, "exports", hold_id)
        os.makedirs(export_dir, exist_ok=True)

        export_path = os.path.join(export_dir, f"{data.export_name}.zip")
        manifest = {"documents": [], "exported_at": datetime.utcnow().isoformat()}
        total_size = 0

        # Create ZIP file
        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in documents:
                source_path = os.path.join(settings.UPLOAD_DIR, doc.storage_path)
                if os.path.exists(source_path):
                    zf.write(source_path, doc.file_name)
                    file_hash = hash_file(source_path)
                    manifest["documents"].append({
                        "id": doc.id,
                        "file_name": doc.file_name,
                        "checksum": file_hash,
                        "size": doc.file_size,
                    })
                    total_size += doc.file_size

            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Calculate export hash
        export_hash = hash_file(export_path)

        export = EvidenceExport(
            tenant_id=tenant_id,
            legal_hold_id=hold_id,
            export_name=data.export_name,
            export_format=data.export_format,
            export_path=export_path,
            manifest=manifest,
            document_count=len(documents),
            total_size_bytes=total_size,
            exported_by=user_id,
            export_hash=export_hash,
        )
        self.db.add(export)
        self.db.commit()
        self.db.refresh(export)

        self.audit_service.log_event(
            event_type="EVIDENCE_EXPORTED",
            entity_type="legal_hold",
            entity_id=hold_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_values={
                "export_id": export.id,
                "document_count": len(documents),
                "export_hash": export_hash,
            },
        )

        return export
