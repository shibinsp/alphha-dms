import pytest
from fastapi.testclient import TestClient
from app.models.document import Document, DocumentType, LifecycleStatus


@pytest.fixture
def test_document_type(db, test_tenant):
    """Create a test document type."""
    doc_type = DocumentType(
        id="test-doctype-id",
        name="Contract",
        description="Test contracts",
        tenant_id=test_tenant.id,
    )
    db.add(doc_type)
    db.commit()
    db.refresh(doc_type)
    return doc_type


@pytest.fixture
def test_document(db, test_tenant, test_user, test_document_type):
    """Create a test document."""
    document = Document(
        id="test-doc-id",
        title="Test Document",
        file_name="test.pdf",
        file_path="./uploads/test/test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        checksum="abc123",
        document_type_id=test_document_type.id,
        tenant_id=test_tenant.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        lifecycle_status=LifecycleStatus.DRAFT,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


class TestDocumentTypes:
    """Test document type endpoints."""

    def test_list_document_types(self, client: TestClient, test_document_type, auth_headers):
        """Test listing document types."""
        response = client.get("/api/v1/documents/types", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_create_document_type(self, client: TestClient, auth_headers):
        """Test creating a document type."""
        response = client.post(
            "/api/v1/documents/types",
            json={"name": "Invoice", "description": "Invoice documents"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Invoice"


class TestDocuments:
    """Test document endpoints."""

    def test_list_documents(self, client: TestClient, test_document, auth_headers):
        """Test listing documents."""
        response = client.get("/api/v1/documents/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_document(self, client: TestClient, test_document, auth_headers):
        """Test getting a specific document."""
        response = client.get(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id
        assert data["title"] == "Test Document"

    def test_get_document_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent document."""
        response = client.get(
            "/api/v1/documents/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_document(self, client: TestClient, test_document, auth_headers):
        """Test updating a document."""
        response = client.put(
            f"/api/v1/documents/{test_document.id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_delete_document(self, client: TestClient, test_document, auth_headers):
        """Test deleting a document."""
        response = client.delete(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_delete_worm_locked_document(self, client: TestClient, test_document, db, auth_headers):
        """Test that WORM locked documents cannot be deleted."""
        # Lock the document
        test_document.is_worm_locked = True
        db.commit()

        response = client.delete(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "WORM" in response.json()["detail"]

    def test_delete_legal_hold_document(self, client: TestClient, test_document, db, auth_headers):
        """Test that documents under legal hold cannot be deleted."""
        # Put document on legal hold
        test_document.legal_hold = True
        db.commit()

        response = client.delete(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "legal hold" in response.json()["detail"].lower()


class TestDocumentLifecycle:
    """Test document lifecycle transitions."""

    def test_lifecycle_transition(self, client: TestClient, test_document, auth_headers):
        """Test transitioning document lifecycle."""
        response = client.post(
            f"/api/v1/documents/{test_document.id}/lifecycle",
            json={"new_status": "REVIEW", "comment": "Ready for review"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lifecycle_status"] == "REVIEW"
