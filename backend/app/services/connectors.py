"""External Storage Connectors (SharePoint, OneDrive, Google Drive)"""
import httpx
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class ExternalFile:
    """Represents a file from external storage."""
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    modified_at: datetime
    download_url: Optional[str] = None
    metadata: Dict[str, Any] = None


class BaseConnector(ABC):
    """Base class for external storage connectors."""
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the external service."""
        pass
    
    @abstractmethod
    async def list_files(self, folder_path: str = "/") -> List[ExternalFile]:
        """List files in a folder."""
        pass
    
    @abstractmethod
    async def download_file(self, file_id: str) -> bytes:
        """Download file content."""
        pass
    
    @abstractmethod
    async def get_file_metadata(self, file_id: str) -> ExternalFile:
        """Get file metadata."""
        pass


class SharePointConnector(BaseConnector):
    """Microsoft SharePoint connector using Graph API."""
    
    def __init__(self, site_url: str = None):
        self.client_id = settings.SHAREPOINT_CLIENT_ID
        self.client_secret = settings.SHAREPOINT_CLIENT_SECRET
        self.tenant_id = settings.SHAREPOINT_TENANT_ID
        self.site_url = site_url
        self.access_token: Optional[str] = None
        self.graph_url = "https://graph.microsoft.com/v1.0"
    
    async def authenticate(self) -> bool:
        """Get access token using client credentials."""
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            return False
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            })
            
            if response.status_code == 200:
                self.access_token = response.json()["access_token"]
                return True
            return False
    
    async def list_files(self, folder_path: str = "/") -> List[ExternalFile]:
        """List files in SharePoint folder."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            # Get site ID first
            site_response = await client.get(
                f"{self.graph_url}/sites/{self.site_url}",
                headers=headers
            )
            if site_response.status_code != 200:
                return []
            
            site_id = site_response.json()["id"]
            
            # List drive items
            items_url = f"{self.graph_url}/sites/{site_id}/drive/root"
            if folder_path != "/":
                items_url += f":/{folder_path.strip('/')}:"
            items_url += "/children"
            
            response = await client.get(items_url, headers=headers)
            if response.status_code != 200:
                return []
            
            files = []
            for item in response.json().get("value", []):
                if "file" in item:  # Skip folders
                    files.append(ExternalFile(
                        id=item["id"],
                        name=item["name"],
                        path=folder_path + "/" + item["name"],
                        size=item.get("size", 0),
                        mime_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                        modified_at=datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00")),
                        download_url=item.get("@microsoft.graph.downloadUrl")
                    ))
            return files
    
    async def download_file(self, file_id: str) -> bytes:
        """Download file from SharePoint."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.graph_url}/drives/items/{file_id}/content",
                headers=headers,
                follow_redirects=True
            )
            if response.status_code == 200:
                return response.content
            return b""
    
    async def get_file_metadata(self, file_id: str) -> Optional[ExternalFile]:
        """Get file metadata from SharePoint."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.graph_url}/drives/items/{file_id}",
                headers=headers
            )
            if response.status_code == 200:
                item = response.json()
                return ExternalFile(
                    id=item["id"],
                    name=item["name"],
                    path=item.get("parentReference", {}).get("path", "") + "/" + item["name"],
                    size=item.get("size", 0),
                    mime_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                    modified_at=datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00"))
                )
            return None


class OneDriveConnector(SharePointConnector):
    """OneDrive connector (uses same Graph API as SharePoint)."""
    
    def __init__(self, user_id: str = "me"):
        super().__init__()
        self.client_id = settings.ONEDRIVE_CLIENT_ID
        self.client_secret = settings.ONEDRIVE_CLIENT_SECRET
        self.user_id = user_id
    
    async def list_files(self, folder_path: str = "/") -> List[ExternalFile]:
        """List files in OneDrive folder."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            items_url = f"{self.graph_url}/users/{self.user_id}/drive/root"
            if folder_path != "/":
                items_url += f":/{folder_path.strip('/')}:"
            items_url += "/children"
            
            response = await client.get(items_url, headers=headers)
            if response.status_code != 200:
                return []
            
            files = []
            for item in response.json().get("value", []):
                if "file" in item:
                    files.append(ExternalFile(
                        id=item["id"],
                        name=item["name"],
                        path=folder_path + "/" + item["name"],
                        size=item.get("size", 0),
                        mime_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                        modified_at=datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00")),
                        download_url=item.get("@microsoft.graph.downloadUrl")
                    ))
            return files


class GoogleDriveConnector(BaseConnector):
    """Google Drive connector."""
    
    def __init__(self):
        self.credentials_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        self.access_token: Optional[str] = None
        self.api_url = "https://www.googleapis.com/drive/v3"
    
    async def authenticate(self) -> bool:
        """Authenticate with Google Drive using service account."""
        if not self.credentials_file:
            return False
        
        # In production, use google-auth library
        # This is a simplified placeholder
        try:
            import json
            with open(self.credentials_file) as f:
                creds = json.load(f)
            # Would use google.oauth2.service_account here
            return True
        except Exception:
            return False
    
    async def list_files(self, folder_path: str = "/") -> List[ExternalFile]:
        """List files in Google Drive folder."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            params = {
                "q": f"'{folder_path}' in parents and trashed=false",
                "fields": "files(id,name,mimeType,size,modifiedTime)"
            }
            
            response = await client.get(
                f"{self.api_url}/files",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                return []
            
            files = []
            for item in response.json().get("files", []):
                if not item["mimeType"].startswith("application/vnd.google-apps.folder"):
                    files.append(ExternalFile(
                        id=item["id"],
                        name=item["name"],
                        path=folder_path + "/" + item["name"],
                        size=int(item.get("size", 0)),
                        mime_type=item["mimeType"],
                        modified_at=datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00"))
                    ))
            return files
    
    async def download_file(self, file_id: str) -> bytes:
        """Download file from Google Drive."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/files/{file_id}?alt=media",
                headers=headers
            )
            if response.status_code == 200:
                return response.content
            return b""
    
    async def get_file_metadata(self, file_id: str) -> Optional[ExternalFile]:
        """Get file metadata from Google Drive."""
        if not self.access_token:
            await self.authenticate()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/files/{file_id}",
                headers=headers,
                params={"fields": "id,name,mimeType,size,modifiedTime,parents"}
            )
            if response.status_code == 200:
                item = response.json()
                return ExternalFile(
                    id=item["id"],
                    name=item["name"],
                    path="/" + item["name"],
                    size=int(item.get("size", 0)),
                    mime_type=item["mimeType"],
                    modified_at=datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00"))
                )
            return None


def get_connector(connector_type: str) -> Optional[BaseConnector]:
    """Factory function to get connector by type."""
    connectors = {
        "sharepoint": SharePointConnector,
        "onedrive": OneDriveConnector,
        "googledrive": GoogleDriveConnector
    }
    
    connector_class = connectors.get(connector_type.lower())
    if connector_class:
        return connector_class()
    return None
