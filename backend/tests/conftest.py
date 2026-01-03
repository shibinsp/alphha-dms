import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-bytes!!"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.tenant import Tenant
from app.models.role import Role

# Test database
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_tenant(db):
    """Create a test tenant."""
    tenant = Tenant(
        id="test-tenant-id",
        name="Test Tenant",
        domain="test.local",
        license_key="TEST-LICENSE-KEY",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_role(db, test_tenant):
    """Create a test admin role."""
    role = Role(
        id="test-role-id",
        name="Admin",
        description="Test admin role",
        permissions=["*"],
        is_system_role=True,
        tenant_id=test_tenant.id,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def test_user(db, test_tenant, test_role):
    """Create a test user."""
    user = User(
        id="test-user-id",
        email="test@alphha.local",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        tenant_id=test_tenant.id,
        is_active=True,
        is_superuser=False,
    )
    user.roles.append(test_role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user."""
    response = client.post(
        "/api/v1/auth/login/json",
        json={"email": "test@alphha.local", "password": "testpassword123"}
    )
    assert response.status_code == 200
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
