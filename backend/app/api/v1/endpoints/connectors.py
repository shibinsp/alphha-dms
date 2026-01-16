"""External Connectors API Endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, require_permissions
from app.models import User, Document, Tenant
from app.services.connectors import get_connector, ExternalFile

router = APIRouter(prefix="/connectors", tags=["External Connectors"])


class ConnectorStatus(BaseModel):
    name: str
    configured: bool
    connected: bool


class ExternalFileResponse(BaseModel):
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    modified_at: str


class ImportRequest(BaseModel):
    connector_type: str
    file_ids: List[str]
    target_folder_id: Optional[str] = None
    document_type_id: Optional[str] = None


@router.get("/status", response_model=List[ConnectorStatus])
async def get_connectors_status(
    current_user: User = Depends(require_permissions("documents:create"))
):
    """Get status of all external connectors."""
    from app.core.config import settings
    
    connectors = [
        ConnectorStatus(
            name="SharePoint",
            configured=bool(settings.SHAREPOINT_CLIENT_ID),
            connected=False
        ),
        ConnectorStatus(
            name="OneDrive",
            configured=bool(settings.ONEDRIVE_CLIENT_ID),
            connected=False
        ),
        ConnectorStatus(
            name="Google Drive",
            configured=bool(settings.GOOGLE_DRIVE_CREDENTIALS_FILE),
            connected=False
        )
    ]
    
    # Test connections for configured connectors
    for conn in connectors:
        if conn.configured:
            connector = get_connector(conn.name.lower().replace(" ", ""))
            if connector:
                try:
                    conn.connected = await connector.authenticate()
                except Exception:
                    conn.connected = False
    
    return connectors


@router.get("/{connector_type}/files", response_model=List[ExternalFileResponse])
async def list_external_files(
    connector_type: str,
    folder_path: str = "/",
    current_user: User = Depends(require_permissions("documents:create"))
):
    """List files from external connector."""
    connector = get_connector(connector_type)
    if not connector:
        raise HTTPException(400, f"Unknown connector type: {connector_type}")
    
    if not await connector.authenticate():
        raise HTTPException(401, f"Failed to authenticate with {connector_type}")
    
    files = await connector.list_files(folder_path)
    
    return [
        ExternalFileResponse(
            id=f.id,
            name=f.name,
            path=f.path,
            size=f.size,
            mime_type=f.mime_type,
            modified_at=f.modified_at.isoformat()
        )
        for f in files
    ]


@router.post("/import")
async def import_files(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_permissions("documents:create")),
    db: Session = Depends(get_db)
):
    """Import files from external connector."""
    connector = get_connector(request.connector_type)
    if not connector:
        raise HTTPException(400, f"Unknown connector type: {request.connector_type}")
    
    if not await connector.authenticate():
        raise HTTPException(401, f"Failed to authenticate with {request.connector_type}")
    
    # Queue import task
    background_tasks.add_task(
        _import_files_task,
        connector,
        request.file_ids,
        current_user.id,
        current_user.tenant_id,
        request.target_folder_id,
        request.document_type_id
    )
    
    return {
        "message": f"Import of {len(request.file_ids)} files queued",
        "file_count": len(request.file_ids)
    }


async def _import_files_task(
    connector,
    file_ids: List[str],
    user_id: str,
    tenant_id: str,
    folder_id: Optional[str],
    document_type_id: Optional[str]
):
    """Background task to import files."""
    from app.core.database import SessionLocal
    from app.services.virus_scanner import scan_file_content
    import hashlib
    import os
    import uuid
    from datetime import datetime
    
    db = SessionLocal()
    try:
        for file_id in file_ids:
            try:
                # Get file metadata
                metadata = await connector.get_file_metadata(file_id)
                if not metadata:
                    continue
                
                # Download file
                content = await connector.download_file(file_id)
                if not content:
                    continue
                
                # Virus scan
                is_clean, threat = scan_file_content(content)
                if not is_clean:
                    print(f"Virus detected in {metadata.name}: {threat}")
                    continue
                
                # Save file
                doc_id = str(uuid.uuid4())
                date_path = datetime.utcnow().strftime("%Y/%m/%d")
                file_path = f"./uploads/{tenant_id}/{date_path}/{doc_id}_{metadata.name}"
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(content)
                
                # Create document record
                checksum = hashlib.sha256(content).hexdigest()
                
                document = Document(
                    id=doc_id,
                    tenant_id=tenant_id,
                    title=metadata.name,
                    file_name=metadata.name,
                    file_path=file_path,
                    file_size=len(content),
                    mime_type=metadata.mime_type,
                    checksum_sha256=checksum,
                    source_type="INTERNAL",
                    folder_id=folder_id,
                    document_type_id=document_type_id,
                    created_by=user_id
                )
                db.add(document)
                db.commit()
                
            except Exception as e:
                print(f"Failed to import {file_id}: {e}")
                continue
    finally:
        db.close()
