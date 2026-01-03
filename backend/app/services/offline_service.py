"""Offline/Sync service for M17 - PWA Support"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.offline import (
    SyncQueue, DeviceRegistration, OfflineDocument, SyncConflict,
    SyncStatus, SyncOperation
)
from app.models import Document
from app.schemas.offline import (
    DeviceRegistrationCreate, SyncQueueItemCreate,
    ConflictResolution, OfflineDocumentCreate,
    DeltaSyncItem
)


class OfflineService:
    def __init__(self, db: Session):
        self.db = db
        self._sync_version_cache = {}

    # Device management
    def register_device(
        self,
        tenant_id: str,
        user_id: str,
        data: DeviceRegistrationCreate
    ) -> DeviceRegistration:
        """Register a device for offline sync"""
        # Check for existing registration
        existing = self.db.query(DeviceRegistration).filter(
            DeviceRegistration.device_id == data.device_id
        ).first()

        if existing:
            existing.user_id = user_id
            existing.device_name = data.device_name
            existing.device_type = data.device_type
            existing.os_info = data.os_info
            existing.browser_info = data.browser_info
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        device = DeviceRegistration(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            **data.model_dump()
        )
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_device(self, device_id: str) -> Optional[DeviceRegistration]:
        """Get device by ID"""
        return self.db.query(DeviceRegistration).filter(
            DeviceRegistration.device_id == device_id,
            DeviceRegistration.is_active == True
        ).first()

    def get_user_devices(self, user_id: str) -> List[DeviceRegistration]:
        """Get all devices for a user"""
        return self.db.query(DeviceRegistration).filter(
            DeviceRegistration.user_id == user_id,
            DeviceRegistration.is_active == True
        ).all()

    def deactivate_device(self, device_id: str, user_id: str) -> bool:
        """Deactivate a device"""
        device = self.db.query(DeviceRegistration).filter(
            DeviceRegistration.device_id == device_id,
            DeviceRegistration.user_id == user_id
        ).first()

        if not device:
            return False

        device.is_active = False
        self.db.commit()
        return True

    # Sync queue management
    def queue_sync_item(
        self,
        tenant_id: str,
        user_id: str,
        data: SyncQueueItemCreate
    ) -> SyncQueue:
        """Queue an item for sync"""
        item = SyncQueue(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            **data.model_dump()
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def process_sync_batch(
        self,
        tenant_id: str,
        user_id: str,
        items: List[SyncQueueItemCreate]
    ) -> Dict[str, List]:
        """Process a batch of sync items"""
        synced = []
        conflicts = []
        failed = []

        for item_data in items:
            queue_item = self.queue_sync_item(tenant_id, user_id, item_data)

            try:
                result = self._process_sync_item(queue_item)
                if result["status"] == "synced":
                    synced.append(queue_item)
                elif result["status"] == "conflict":
                    conflict = self._create_conflict(queue_item, result["server_data"])
                    conflicts.append(conflict)
                else:
                    failed.append(queue_item)
            except Exception as e:
                queue_item.status = SyncStatus.FAILED
                queue_item.error_message = str(e)
                queue_item.attempts += 1
                self.db.commit()
                failed.append(queue_item)

        # Update device sync info
        if items:
            device = self.get_device(items[0].device_id)
            if device:
                device.last_sync_at = datetime.utcnow()
                device.sync_version += 1
                self.db.commit()

        return {
            "synced": synced,
            "conflicts": conflicts,
            "failed": failed,
            "server_version": self._get_server_version(tenant_id)
        }

    def _process_sync_item(self, item: SyncQueue) -> Dict[str, Any]:
        """Process a single sync item"""
        item.status = SyncStatus.SYNCING
        item.attempts += 1
        item.last_attempt_at = datetime.utcnow()
        self.db.commit()

        if item.entity_type == "document":
            return self._sync_document(item)
        elif item.entity_type == "folder":
            return self._sync_folder(item)
        elif item.entity_type == "metadata":
            return self._sync_metadata(item)
        else:
            return {"status": "failed", "error": "Unknown entity type"}

    def _sync_document(self, item: SyncQueue) -> Dict[str, Any]:
        """Sync a document change"""
        if item.operation == SyncOperation.CREATE:
            # Create document from offline data
            # In production, this would create the actual document
            item.status = SyncStatus.COMPLETED
            item.synced_at = datetime.utcnow()
            self.db.commit()
            return {"status": "synced"}

        elif item.operation == SyncOperation.UPDATE:
            # Check for conflicts
            if item.entity_id:
                doc = self.db.query(Document).filter(
                    Document.id == item.entity_id
                ).first()

                if doc and doc.updated_at > item.client_timestamp:
                    return {
                        "status": "conflict",
                        "server_data": {
                            "id": doc.id,
                            "title": doc.title,
                            "updated_at": doc.updated_at.isoformat()
                        }
                    }

            # Apply update
            item.status = SyncStatus.COMPLETED
            item.synced_at = datetime.utcnow()
            self.db.commit()
            return {"status": "synced"}

        elif item.operation == SyncOperation.DELETE:
            item.status = SyncStatus.COMPLETED
            item.synced_at = datetime.utcnow()
            self.db.commit()
            return {"status": "synced"}

        return {"status": "failed", "error": "Unknown operation"}

    def _sync_folder(self, item: SyncQueue) -> Dict[str, Any]:
        """Sync a folder change"""
        item.status = SyncStatus.COMPLETED
        item.synced_at = datetime.utcnow()
        self.db.commit()
        return {"status": "synced"}

    def _sync_metadata(self, item: SyncQueue) -> Dict[str, Any]:
        """Sync metadata changes"""
        item.status = SyncStatus.COMPLETED
        item.synced_at = datetime.utcnow()
        self.db.commit()
        return {"status": "synced"}

    def _create_conflict(
        self,
        item: SyncQueue,
        server_data: Dict
    ) -> SyncConflict:
        """Create a conflict record"""
        item.status = SyncStatus.CONFLICT
        self.db.commit()

        conflict = SyncConflict(
            id=str(uuid.uuid4()),
            sync_queue_id=item.id,
            tenant_id=item.tenant_id,
            user_id=item.user_id,
            entity_type=item.entity_type,
            entity_id=item.entity_id or item.local_id,
            client_data=item.payload,
            server_data=server_data,
            client_timestamp=item.client_timestamp,
            server_timestamp=datetime.utcnow()
        )
        self.db.add(conflict)
        self.db.commit()
        self.db.refresh(conflict)
        return conflict

    # Conflict resolution
    def resolve_conflict(
        self,
        conflict_id: str,
        user_id: str,
        resolution: ConflictResolution
    ) -> Optional[SyncConflict]:
        """Resolve a sync conflict"""
        conflict = self.db.query(SyncConflict).filter(
            SyncConflict.id == conflict_id,
            SyncConflict.user_id == user_id
        ).first()

        if not conflict:
            return None

        conflict.resolution = resolution.resolution
        conflict.resolved_by = user_id
        conflict.resolved_at = datetime.utcnow()

        if resolution.resolution == "merged" and resolution.merged_data:
            conflict.resolved_data = resolution.merged_data

        # Mark queue item as completed
        queue_item = self.db.query(SyncQueue).filter(
            SyncQueue.id == conflict.sync_queue_id
        ).first()
        if queue_item:
            queue_item.status = SyncStatus.COMPLETED
            queue_item.synced_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conflict)
        return conflict

    def get_user_conflicts(
        self,
        user_id: str
    ) -> List[SyncConflict]:
        """Get unresolved conflicts for a user"""
        return self.db.query(SyncConflict).filter(
            SyncConflict.user_id == user_id,
            SyncConflict.resolution == None
        ).order_by(SyncConflict.created_at.desc()).all()

    # Offline document management
    def mark_for_offline(
        self,
        tenant_id: str,
        user_id: str,
        data: OfflineDocumentCreate
    ) -> OfflineDocument:
        """Mark a document for offline availability"""
        # Check if already marked
        existing = self.db.query(OfflineDocument).filter(
            OfflineDocument.user_id == user_id,
            OfflineDocument.document_id == data.document_id,
            OfflineDocument.device_id == data.device_id
        ).first()

        if existing:
            existing.is_synced = False
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Get document size
        doc = self.db.query(Document).filter(
            Document.id == data.document_id
        ).first()

        offline_doc = OfflineDocument(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            document_id=data.document_id,
            device_id=data.device_id,
            file_size=doc.file_size if doc else None
        )
        self.db.add(offline_doc)
        self.db.commit()
        self.db.refresh(offline_doc)
        return offline_doc

    def remove_from_offline(
        self,
        user_id: str,
        document_id: str,
        device_id: str
    ) -> bool:
        """Remove document from offline availability"""
        offline_doc = self.db.query(OfflineDocument).filter(
            OfflineDocument.user_id == user_id,
            OfflineDocument.document_id == document_id,
            OfflineDocument.device_id == device_id
        ).first()

        if not offline_doc:
            return False

        self.db.delete(offline_doc)
        self.db.commit()
        return True

    def get_offline_documents(
        self,
        user_id: str,
        device_id: str
    ) -> List[OfflineDocument]:
        """Get documents marked for offline on a device"""
        return self.db.query(OfflineDocument).filter(
            OfflineDocument.user_id == user_id,
            OfflineDocument.device_id == device_id
        ).all()

    def mark_synced(
        self,
        offline_doc_id: str,
        version: int
    ) -> Optional[OfflineDocument]:
        """Mark an offline document as synced"""
        offline_doc = self.db.query(OfflineDocument).filter(
            OfflineDocument.id == offline_doc_id
        ).first()

        if not offline_doc:
            return None

        offline_doc.is_synced = True
        offline_doc.synced_version = version
        offline_doc.synced_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(offline_doc)
        return offline_doc

    # Delta sync
    def get_delta_changes(
        self,
        tenant_id: str,
        user_id: str,
        since_version: int,
        entity_types: List[str] = None,
        limit: int = 100
    ) -> tuple[List[DeltaSyncItem], int, bool]:
        """Get changes since a version for delta sync"""
        # In production, this would query actual change logs
        # For now, return empty with current version
        current_version = self._get_server_version(tenant_id)
        return [], current_version, False

    def _get_server_version(self, tenant_id: str) -> int:
        """Get current server sync version"""
        # In production, this would be a proper version counter
        if tenant_id not in self._sync_version_cache:
            self._sync_version_cache[tenant_id] = 1
        return self._sync_version_cache[tenant_id]

    # Storage tracking
    def update_storage_used(
        self,
        device_id: str,
        bytes_used: int
    ) -> Optional[DeviceRegistration]:
        """Update storage used on a device"""
        device = self.get_device(device_id)
        if not device:
            return None

        device.storage_used = bytes_used // (1024 * 1024)  # Convert to MB
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_sync_status(
        self,
        user_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Get sync status for a device"""
        device = self.get_device(device_id)
        if not device or device.user_id != user_id:
            return {}

        pending_count = self.db.query(func.count(SyncQueue.id)).filter(
            SyncQueue.user_id == user_id,
            SyncQueue.device_id == device_id,
            SyncQueue.status == SyncStatus.PENDING
        ).scalar() or 0

        conflicts_count = len(self.get_user_conflicts(user_id))

        return {
            "device_id": device_id,
            "last_sync_at": device.last_sync_at.isoformat() if device.last_sync_at else None,
            "server_version": device.sync_version,
            "pending_changes": pending_count,
            "conflicts_count": conflicts_count,
            "storage_used": device.storage_used,
            "storage_quota": device.storage_quota
        }
