from datetime import datetime, date
from typing import Optional, List, Dict, Any
import hashlib
import json

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.audit import AuditEvent, AuditRoot, AuditVerification, VerificationResult
from app.utils.merkle import build_merkle_tree, get_merkle_root, verify_chain_integrity


class AuditService:
    """Service for immutable audit logging with hash chain verification."""

    def __init__(self, db: Session):
        self.db = db

    def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        tenant_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log an audit event with hash chaining for integrity.
        """
        # Get the previous event's hash
        last_event = self.db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id
        ).order_by(AuditEvent.sequence_number.desc()).first()

        previous_hash = last_event.event_hash if last_event else "0" * 64

        # Get next sequence number
        max_seq = self.db.query(func.max(AuditEvent.sequence_number)).scalar() or 0
        sequence_number = max_seq + 1

        # Create the event
        event = AuditEvent(
            sequence_number=sequence_number,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            old_values=old_values,
            new_values=new_values,
            metadata=metadata,
            previous_hash=previous_hash,
            event_hash=""  # Will be computed below
        )

        self.db.add(event)
        self.db.flush()  # Get the created_at timestamp

        # Compute event hash
        event.event_hash = self._compute_event_hash(event)
        self.db.commit()

        return event

    def _compute_event_hash(self, event: AuditEvent) -> str:
        """Compute SHA-256 hash for an audit event."""
        data = (
            f"{event.sequence_number}|"
            f"{event.event_type}|"
            f"{event.entity_type}|"
            f"{event.entity_id}|"
            f"{event.user_id}|"
            f"{event.tenant_id}|"
            f"{event.created_at.isoformat()}|"
            f"{event.previous_hash}|"
            f"{json.dumps(event.old_values, sort_keys=True) if event.old_values else ''}|"
            f"{json.dumps(event.new_values, sort_keys=True) if event.new_values else ''}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def get_events(
        self,
        tenant_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[AuditEvent], int]:
        """Get audit events with filters."""
        query = self.db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id)

        if entity_type:
            query = query.filter(AuditEvent.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditEvent.entity_id == entity_id)
        if event_type:
            query = query.filter(AuditEvent.event_type == event_type)
        if user_id:
            query = query.filter(AuditEvent.user_id == user_id)
        if start_date:
            query = query.filter(AuditEvent.created_at >= start_date)
        if end_date:
            query = query.filter(AuditEvent.created_at <= end_date)

        total = query.count()
        events = query.order_by(AuditEvent.sequence_number.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return events, total

    def get_entity_trail(
        self,
        tenant_id: str,
        entity_type: str,
        entity_id: str
    ) -> List[AuditEvent]:
        """Get complete audit trail for a specific entity."""
        return self.db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id
        ).order_by(AuditEvent.sequence_number.asc()).all()

    def generate_daily_merkle_root(self, tenant_id: str, for_date: date) -> Optional[AuditRoot]:
        """Generate Merkle root for a day's audit events."""
        events = self.db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id,
            func.date(AuditEvent.created_at) == for_date
        ).order_by(AuditEvent.sequence_number.asc()).all()

        if not events:
            return None

        hashes = [e.event_hash for e in events]
        merkle_root = get_merkle_root(hashes)

        root = AuditRoot(
            date=for_date,
            merkle_root=merkle_root,
            event_count=len(events),
            first_sequence=events[0].sequence_number,
            last_sequence=events[-1].sequence_number,
            tenant_id=tenant_id
        )

        self.db.add(root)
        self.db.commit()
        return root

    def verify_integrity(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
        verified_by: str
    ) -> AuditVerification:
        """
        Verify audit integrity for a date range.
        Checks hash chain and Merkle roots.
        """
        events = self.db.query(AuditEvent).filter(
            AuditEvent.tenant_id == tenant_id,
            func.date(AuditEvent.created_at) >= start_date,
            func.date(AuditEvent.created_at) <= end_date
        ).order_by(AuditEvent.sequence_number.asc()).all()

        details = {
            "events_checked": len(events),
            "chain_errors": [],
            "hash_errors": [],
            "merkle_errors": []
        }

        result = VerificationResult.PASSED

        # Verify hash chain
        for i, event in enumerate(events):
            # Verify event hash
            computed_hash = self._compute_event_hash(event)
            if computed_hash != event.event_hash:
                result = VerificationResult.FAILED
                details["hash_errors"].append({
                    "sequence": event.sequence_number,
                    "expected": event.event_hash,
                    "computed": computed_hash
                })

            # Verify chain continuity (skip first event)
            if i > 0:
                if event.previous_hash != events[i - 1].event_hash:
                    result = VerificationResult.FAILED
                    details["chain_errors"].append({
                        "sequence": event.sequence_number,
                        "expected_previous": events[i - 1].event_hash,
                        "actual_previous": event.previous_hash
                    })

        # Verify Merkle roots
        roots = self.db.query(AuditRoot).filter(
            AuditRoot.tenant_id == tenant_id,
            AuditRoot.date >= start_date,
            AuditRoot.date <= end_date
        ).all()

        for root in roots:
            day_events = [e for e in events if e.created_at.date() == root.date]
            if day_events:
                computed_root = get_merkle_root([e.event_hash for e in day_events])
                if computed_root != root.merkle_root:
                    result = VerificationResult.FAILED
                    details["merkle_errors"].append({
                        "date": root.date.isoformat(),
                        "expected": root.merkle_root,
                        "computed": computed_root
                    })

        verification = AuditVerification(
            verified_by=verified_by,
            date_range_start=start_date,
            date_range_end=end_date,
            result=result,
            details=details
        )

        self.db.add(verification)
        self.db.commit()

        return verification

    def get_merkle_roots(
        self,
        tenant_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AuditRoot]:
        """Get Merkle roots for date range."""
        query = self.db.query(AuditRoot).filter(AuditRoot.tenant_id == tenant_id)

        if start_date:
            query = query.filter(AuditRoot.date >= start_date)
        if end_date:
            query = query.filter(AuditRoot.date <= end_date)

        return query.order_by(AuditRoot.date.desc()).all()
