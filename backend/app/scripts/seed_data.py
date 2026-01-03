"""Comprehensive seed data script for Alphha DMS"""
import uuid
import os
import hashlib
import random
from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models import (
    Tenant,
    User,
    Role,
    DocumentType,
    Department,
    Folder,
)
from app.models.document import Document, SourceType, Classification, LifecycleStatus, OCRStatus
from app.models.version import DocumentVersion
from app.models.workflow import (
    ApprovalWorkflow, ApprovalStep, ApprovalRequest, ApprovalAction,
    WorkflowType, ApprovalStatus, StepStatus
)
from app.models.compliance import (
    RetentionPolicy, LegalHold, LegalHoldDocument, WORMRecord,
    RetentionUnit, RetentionAction, LegalHoldStatus
)
from app.models.analytics import (
    AnalyticsMetric, ComplianceAlert, DashboardWidget,
    MetricType, TimeGranularity
)
from app.models.notifications import Notification, NotificationType, NotificationPriority
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.search import SavedSearch
from app.models.bsi import (
    BankStatement, BankTransaction, TransactionRule,
    StatementStatus, TransactionCategory, TransactionType
)
from app.models.pii import PIIPolicy
from app.models.audit import AuditEvent
from app.core.security import get_password_hash
from app.services.pii_service import PIIService


def create_default_tenant(db: Session) -> Tenant:
    """Create default tenant"""
    tenant = db.query(Tenant).filter(Tenant.subdomain == "default").first()
    if not tenant:
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Alphha Default",
            subdomain="default",
            is_active=True,
            license_key="ALPHHA-DEFAULT-2026-ENTERPRISE",
            license_expires=date.today() + timedelta(days=365),
            primary_color="#1E3A5F",
            config={
                "theme": {"primary_color": "#1E3A5F", "secondary_color": "#2E7D32"},
                "features": {"ocr_enabled": True, "pii_detection": True, "ai_chat": True}
            },
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print("Created default tenant")
    return tenant


def create_default_roles(db: Session, tenant_id: str) -> dict:
    """Create default roles"""
    roles = {
        "super_admin": {"name": "super_admin", "description": "Full system access", "permissions": ["*"], "is_system_role": True},
        "admin": {"name": "admin", "description": "Administrative access", "permissions": ["documents:*", "users:*", "workflows:*"], "is_system_role": True},
        "legal": {"name": "legal", "description": "Legal team access", "permissions": ["documents:read", "documents:legal_hold", "audit:*"], "is_system_role": True},
        "compliance": {"name": "compliance", "description": "Compliance access", "permissions": ["documents:read", "audit:*", "pii:view"], "is_system_role": True},
        "manager": {"name": "manager", "description": "Manager access", "permissions": ["documents:*", "documents:approve", "workflows:read"], "is_system_role": True},
        "user": {"name": "user", "description": "Standard user", "permissions": ["documents:create", "documents:read", "documents:update"], "is_system_role": True},
        "viewer": {"name": "viewer", "description": "Read-only access", "permissions": ["documents:read"], "is_system_role": True},
    }

    created_roles = {}
    for role_key, role_data in roles.items():
        existing = db.query(Role).filter(Role.tenant_id == tenant_id, Role.name == role_data["name"]).first()
        if not existing:
            role = Role(id=str(uuid.uuid4()), tenant_id=tenant_id, **role_data)
            db.add(role)
            db.commit()
            db.refresh(role)
            created_roles[role_key] = role
            print(f"Created role: {role_data['name']}")
        else:
            created_roles[role_key] = existing
    return created_roles


def create_admin_user(db: Session, tenant_id: str, admin_role: Role) -> User:
    """Create default admin user"""
    existing = db.query(User).filter(User.email == "admin@alphha.local").first()
    if not existing:
        user = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email="admin@alphha.local",
            full_name="System Administrator",
            password_hash=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True,
            clearance_level="RESTRICTED",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user.roles.append(admin_role)
        db.commit()
        print("Created admin user: admin@alphha.local / admin123")
        return user
    return existing


def create_document_types(db: Session, tenant_id: str) -> dict:
    """Create default document types and return mapping"""
    types = [
        {"name": "Contract", "retention_days": 2555, "description": "Legal contracts and agreements"},
        {"name": "Invoice", "retention_days": 1825, "description": "Financial invoices"},
        {"name": "Report", "retention_days": 365, "description": "Business reports"},
        {"name": "Memo", "retention_days": 365, "description": "Internal memos"},
        {"name": "Policy", "retention_days": 3650, "description": "Company policies"},
        {"name": "Legal Document", "retention_days": 2555, "description": "Legal documents"},
        {"name": "Financial Statement", "retention_days": 2555, "description": "Financial statements"},
        {"name": "HR Document", "retention_days": 2555, "description": "HR documents"},
        {"name": "Technical Specification", "retention_days": 1825, "description": "Technical specs"},
        {"name": "General", "retention_days": 365, "description": "General documents"},
    ]

    type_map = {}
    for type_data in types:
        existing = db.query(DocumentType).filter(DocumentType.tenant_id == tenant_id, DocumentType.name == type_data["name"]).first()
        if not existing:
            doc_type = DocumentType(id=str(uuid.uuid4()), tenant_id=tenant_id, **type_data)
            db.add(doc_type)
            db.commit()
            db.refresh(doc_type)
            type_map[type_data["name"]] = doc_type
            print(f"Created document type: {type_data['name']}")
        else:
            type_map[type_data["name"]] = existing
    return type_map


def create_departments(db: Session, tenant_id: str) -> dict:
    """Create default departments and return mapping"""
    departments = [
        {"name": "Legal", "code": "LEGAL"},
        {"name": "Finance", "code": "FINANCE"},
        {"name": "Human Resources", "code": "HR"},
        {"name": "Operations", "code": "OPS"},
        {"name": "Technology", "code": "TECH"},
        {"name": "Compliance", "code": "COMPLIANCE"},
        {"name": "Administration", "code": "ADMIN"},
    ]

    dept_map = {}
    for dept_data in departments:
        existing = db.query(Department).filter(Department.tenant_id == tenant_id, Department.code == dept_data["code"]).first()
        if not existing:
            dept = Department(id=str(uuid.uuid4()), tenant_id=tenant_id, **dept_data)
            db.add(dept)
            db.commit()
            db.refresh(dept)
            dept_map[dept_data["name"]] = dept
            print(f"Created department: {dept_data['name']}")
        else:
            dept_map[dept_data["name"]] = existing
    return dept_map


def create_default_folders(db: Session, tenant_id: str) -> dict:
    """Create default folder structure"""
    folders = [
        {"name": "Contracts", "path": "/Contracts"},
        {"name": "Invoices", "path": "/Invoices"},
        {"name": "Reports", "path": "/Reports"},
        {"name": "Policies", "path": "/Policies"},
        {"name": "HR Documents", "path": "/HR Documents"},
        {"name": "Financial", "path": "/Financial"},
        {"name": "Archive", "path": "/Archive"},
    ]

    folder_map = {}
    for folder_data in folders:
        existing = db.query(Folder).filter(Folder.tenant_id == tenant_id, Folder.path == folder_data["path"]).first()
        if not existing:
            folder = Folder(id=str(uuid.uuid4()), tenant_id=tenant_id, **folder_data)
            db.add(folder)
            db.commit()
            db.refresh(folder)
            folder_map[folder_data["name"]] = folder
            print(f"Created folder: {folder_data['path']}")
        else:
            folder_map[folder_data["name"]] = existing
    return folder_map


def initialize_pii_patterns(db: Session, tenant_id: str) -> None:
    """Initialize system PII patterns"""
    pii_service = PIIService(db)
    pii_service.initialize_system_patterns(tenant_id)
    print("Initialized PII detection patterns")


def create_test_users(db: Session, tenant_id: str, roles: dict) -> dict:
    """Create test users for different roles"""
    test_users = [
        {"email": "manager@alphha.local", "full_name": "John Manager", "role": "manager", "clearance_level": "CONFIDENTIAL"},
        {"email": "legal@alphha.local", "full_name": "Sarah Legal", "role": "legal", "clearance_level": "RESTRICTED"},
        {"email": "compliance@alphha.local", "full_name": "Mike Compliance", "role": "compliance", "clearance_level": "CONFIDENTIAL"},
        {"email": "user@alphha.local", "full_name": "Jane User", "role": "user", "clearance_level": "INTERNAL"},
        {"email": "viewer@alphha.local", "full_name": "Bob Viewer", "role": "viewer", "clearance_level": "PUBLIC"},
    ]

    user_map = {}
    for user_data in test_users:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                email=user_data["email"],
                full_name=user_data["full_name"],
                password_hash=get_password_hash("password123"),
                is_active=True,
                clearance_level=user_data["clearance_level"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user.roles.append(roles[user_data["role"]])
            db.commit()
            user_map[user_data["role"]] = user
            print(f"Created test user: {user_data['email']}")
        else:
            user_map[user_data["role"]] = existing
    return user_map


def create_placeholder_files(tenant_id: str) -> str:
    """Create placeholder PDF files and return base path"""
    upload_dir = os.path.join(os.getcwd(), "uploads", tenant_id)
    os.makedirs(upload_dir, exist_ok=True)

    # Create a simple placeholder PDF content
    placeholder_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"

    return upload_dir, placeholder_content


def create_sample_documents(db: Session, tenant_id: str, doc_types: dict, departments: dict, folders: dict, admin_id: str) -> list:
    """Create sample documents with varied statuses"""

    # Check if documents already exist
    existing_count = db.query(Document).filter(Document.tenant_id == tenant_id).count()
    if existing_count > 5:
        print(f"Documents already exist ({existing_count}), skipping...")
        return db.query(Document).filter(Document.tenant_id == tenant_id).all()

    upload_dir, placeholder_content = create_placeholder_files(tenant_id)

    documents_data = [
        # Contracts
        {"title": "Software License Agreement - Microsoft 365", "type": "Contract", "dept": "Technology", "classification": Classification.CONFIDENTIAL, "status": LifecycleStatus.APPROVED, "source": SourceType.VENDOR},
        {"title": "Office Lease Agreement 2024-2027", "type": "Contract", "dept": "Administration", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.VENDOR},
        {"title": "Vendor Service Agreement - AWS", "type": "Contract", "dept": "Technology", "classification": Classification.CONFIDENTIAL, "status": LifecycleStatus.REVIEW, "source": SourceType.VENDOR},
        {"title": "Partnership Agreement - TechCorp", "type": "Contract", "dept": "Legal", "classification": Classification.RESTRICTED, "status": LifecycleStatus.DRAFT, "source": SourceType.CUSTOMER},

        # Invoices
        {"title": "Invoice #INV-2024-001 - Q1 Cloud Services", "type": "Invoice", "dept": "Finance", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.VENDOR},
        {"title": "Invoice #INV-2024-002 - Office Supplies", "type": "Invoice", "dept": "Administration", "classification": Classification.PUBLIC, "status": LifecycleStatus.APPROVED, "source": SourceType.VENDOR},
        {"title": "Invoice #INV-2024-003 - Consulting Services", "type": "Invoice", "dept": "Finance", "classification": Classification.INTERNAL, "status": LifecycleStatus.REVIEW, "source": SourceType.VENDOR},

        # Reports
        {"title": "Q4 2023 Financial Report", "type": "Financial Statement", "dept": "Finance", "classification": Classification.RESTRICTED, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Annual Compliance Audit Report 2023", "type": "Report", "dept": "Compliance", "classification": Classification.CONFIDENTIAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Employee Satisfaction Survey Results", "type": "Report", "dept": "Human Resources", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Q1 2024 Sales Performance Report", "type": "Report", "dept": "Operations", "classification": Classification.INTERNAL, "status": LifecycleStatus.DRAFT, "source": SourceType.INTERNAL},

        # Policies
        {"title": "Information Security Policy v2.1", "type": "Policy", "dept": "Technology", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Data Retention Policy", "type": "Policy", "dept": "Compliance", "classification": Classification.PUBLIC, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Remote Work Policy 2024", "type": "Policy", "dept": "Human Resources", "classification": Classification.PUBLIC, "status": LifecycleStatus.REVIEW, "source": SourceType.INTERNAL},
        {"title": "Acceptable Use Policy", "type": "Policy", "dept": "Technology", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},

        # Legal Documents
        {"title": "NDA - Partner Company Alpha", "type": "Legal Document", "dept": "Legal", "classification": Classification.CONFIDENTIAL, "status": LifecycleStatus.APPROVED, "source": SourceType.CUSTOMER},
        {"title": "Terms of Service v3.0", "type": "Legal Document", "dept": "Legal", "classification": Classification.PUBLIC, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Privacy Policy Update", "type": "Legal Document", "dept": "Legal", "classification": Classification.PUBLIC, "status": LifecycleStatus.REVIEW, "source": SourceType.INTERNAL},

        # HR Documents
        {"title": "Employee Handbook 2024", "type": "HR Document", "dept": "Human Resources", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Benefits Enrollment Guide", "type": "HR Document", "dept": "Human Resources", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Performance Review Template", "type": "HR Document", "dept": "Human Resources", "classification": Classification.INTERNAL, "status": LifecycleStatus.DRAFT, "source": SourceType.INTERNAL},

        # Technical Specs
        {"title": "API Integration Specification", "type": "Technical Specification", "dept": "Technology", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Database Architecture Document", "type": "Technical Specification", "dept": "Technology", "classification": Classification.CONFIDENTIAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "System Requirements Document", "type": "Technical Specification", "dept": "Technology", "classification": Classification.INTERNAL, "status": LifecycleStatus.REVIEW, "source": SourceType.INTERNAL},

        # Memos
        {"title": "Q1 2024 All-Hands Meeting Notes", "type": "Memo", "dept": "Administration", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Budget Approval - Marketing Campaign", "type": "Memo", "dept": "Finance", "classification": Classification.INTERNAL, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Office Renovation Announcement", "type": "Memo", "dept": "Administration", "classification": Classification.PUBLIC, "status": LifecycleStatus.ARCHIVED, "source": SourceType.INTERNAL},

        # General
        {"title": "Meeting Minutes - Board Meeting Jan 2024", "type": "General", "dept": "Administration", "classification": Classification.RESTRICTED, "status": LifecycleStatus.APPROVED, "source": SourceType.INTERNAL},
        {"title": "Project Proposal - Digital Transformation", "type": "General", "dept": "Technology", "classification": Classification.INTERNAL, "status": LifecycleStatus.DRAFT, "source": SourceType.INTERNAL},
        {"title": "Vendor Evaluation Report", "type": "General", "dept": "Operations", "classification": Classification.INTERNAL, "status": LifecycleStatus.REVIEW, "source": SourceType.INTERNAL},
    ]

    created_documents = []
    for idx, doc_data in enumerate(documents_data):
        file_name = f"{doc_data['title'].replace(' ', '_').replace('/', '_')}.pdf"
        file_path = os.path.join(upload_dir, file_name)

        # Create placeholder file
        with open(file_path, 'wb') as f:
            f.write(placeholder_content)

        checksum = hashlib.sha256(placeholder_content).hexdigest()

        doc = Document(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=doc_data["title"],
            file_name=file_name,
            file_path=file_path,
            file_size=len(placeholder_content),
            mime_type="application/pdf",
            page_count=random.randint(1, 20),
            checksum_sha256=checksum,
            source_type=doc_data["source"],
            department_id=departments.get(doc_data["dept"], list(departments.values())[0]).id if doc_data["dept"] in departments else None,
            document_type_id=doc_types[doc_data["type"]].id,
            folder_id=list(folders.values())[idx % len(folders)].id,
            classification=doc_data["classification"],
            lifecycle_status=doc_data["status"],
            ocr_status=OCRStatus.COMPLETED,
            ocr_confidence=random.randint(85, 99),
            ocr_text=f"Sample OCR text for {doc_data['title']}. This document contains important information.",
            created_by=admin_id,
            updated_by=admin_id,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
        )
        db.add(doc)
        created_documents.append(doc)

    db.commit()
    print(f"Created {len(created_documents)} sample documents")
    return created_documents


def create_document_versions(db: Session, documents: list, admin_id: str) -> None:
    """Create version history for documents"""
    existing_count = db.query(DocumentVersion).count()
    if existing_count > 10:
        print("Document versions already exist, skipping...")
        return

    for doc in documents[:15]:  # Create versions for first 15 docs
        for version_num in range(1, random.randint(2, 4)):
            version = DocumentVersion(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                version_number=version_num,
                file_path=doc.file_path,
                file_size=doc.file_size,
                checksum_sha256=doc.checksum_sha256,
                change_reason=["Initial upload", "Minor corrections", "Major revision", "Final version"][min(version_num - 1, 3)],
                created_by=admin_id,
                is_current=(version_num == 1),
                created_at=doc.created_at + timedelta(days=version_num * 5),
            )
            db.add(version)

    db.commit()
    print("Created document versions")


def create_sample_workflows(db: Session, tenant_id: str, roles: dict) -> list:
    """Create sample approval workflows"""
    existing = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.tenant_id == tenant_id).first()
    if existing:
        return db.query(ApprovalWorkflow).filter(ApprovalWorkflow.tenant_id == tenant_id).all()

    workflows_data = [
        {
            "name": "Document Review",
            "description": "Standard document review workflow",
            "workflow_type": WorkflowType.SEQUENTIAL,
            "steps": [
                {"name": "Manager Review", "order": 1, "role": "manager"},
                {"name": "Compliance Check", "order": 2, "role": "compliance"},
            ]
        },
        {
            "name": "Contract Approval",
            "description": "Multi-level contract approval",
            "workflow_type": WorkflowType.SEQUENTIAL,
            "steps": [
                {"name": "Legal Review", "order": 1, "role": "legal"},
                {"name": "Finance Approval", "order": 2, "role": "manager"},
                {"name": "Executive Sign-off", "order": 3, "role": "admin"},
            ]
        },
        {
            "name": "Policy Review",
            "description": "Policy document review process",
            "workflow_type": WorkflowType.SEQUENTIAL,
            "steps": [
                {"name": "Department Review", "order": 1, "role": "manager"},
                {"name": "Legal Review", "order": 2, "role": "legal"},
                {"name": "Final Approval", "order": 3, "role": "compliance"},
            ]
        },
    ]

    created_workflows = []
    for wf_data in workflows_data:
        workflow = ApprovalWorkflow(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=wf_data["name"],
            description=wf_data["description"],
            workflow_type=wf_data["workflow_type"],
            is_active=True,
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        for step_data in wf_data["steps"]:
            step = ApprovalStep(
                id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                name=step_data["name"],
                step_order=step_data["order"],
                approver_role_id=roles.get(step_data["role"]).id if step_data["role"] in roles else None,
                required_approvals=1,
            )
            db.add(step)

        db.commit()
        created_workflows.append(workflow)
        print(f"Created workflow: {wf_data['name']}")

    return created_workflows


def create_approval_requests(db: Session, tenant_id: str, documents: list, workflows: list, users: dict, admin_id: str) -> None:
    """Create sample approval requests"""
    existing_count = db.query(ApprovalRequest).filter(ApprovalRequest.tenant_id == tenant_id).count()
    if existing_count > 5:
        print("Approval requests already exist, skipping...")
        return

    if not workflows or not documents:
        print("No workflows or documents available for approval requests")
        return

    statuses = [
        (ApprovalStatus.PENDING, 5),
        (ApprovalStatus.APPROVED, 5),
        (ApprovalStatus.REJECTED, 3),
        (ApprovalStatus.CANCELLED, 2),
    ]

    doc_idx = 0
    for status, count in statuses:
        for i in range(count):
            if doc_idx >= len(documents):
                break

            doc = documents[doc_idx]
            workflow = workflows[doc_idx % len(workflows)]

            request = ApprovalRequest(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                workflow_id=workflow.id,
                document_id=doc.id,
                status=status,
                current_step=1 if status == ApprovalStatus.PENDING else 2,
                requested_by=admin_id,
                requested_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                priority=random.choice(["LOW", "NORMAL", "HIGH", "URGENT"]),
                deadline=datetime.utcnow() + timedelta(days=random.randint(1, 14)) if status == ApprovalStatus.PENDING else None,
                completed_at=datetime.utcnow() - timedelta(days=random.randint(1, 5)) if status != ApprovalStatus.PENDING else None,
            )
            db.add(request)
            db.commit()
            db.refresh(request)

            # Create approval actions for completed requests
            if status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
                steps = db.query(ApprovalStep).filter(ApprovalStep.workflow_id == workflow.id).all()
                for step in steps[:2]:
                    action = ApprovalAction(
                        id=str(uuid.uuid4()),
                        request_id=request.id,
                        step_id=step.id,
                        action=StepStatus.APPROVED if status == ApprovalStatus.APPROVED else StepStatus.REJECTED,
                        comments="Reviewed and " + ("approved" if status == ApprovalStatus.APPROVED else "rejected"),
                        acted_by=list(users.values())[0].id if users else admin_id,
                        acted_at=datetime.utcnow() - timedelta(days=random.randint(1, 10)),
                    )
                    db.add(action)

            doc_idx += 1

    db.commit()
    print(f"Created {doc_idx} approval requests with actions")


def create_retention_policies(db: Session, tenant_id: str, doc_types: dict, admin_id: str) -> list:
    """Create retention policies"""
    existing = db.query(RetentionPolicy).filter(RetentionPolicy.tenant_id == tenant_id).first()
    if existing:
        return db.query(RetentionPolicy).filter(RetentionPolicy.tenant_id == tenant_id).all()

    policies_data = [
        {"name": "Financial Records - 7 Years", "period": 7, "unit": RetentionUnit.YEARS, "action": RetentionAction.ARCHIVE, "type": "Invoice"},
        {"name": "Contracts - 10 Years", "period": 10, "unit": RetentionUnit.YEARS, "action": RetentionAction.ARCHIVE, "type": "Contract"},
        {"name": "HR Records - 5 Years", "period": 5, "unit": RetentionUnit.YEARS, "action": RetentionAction.ARCHIVE, "type": "HR Document"},
        {"name": "General Documents - 3 Years", "period": 3, "unit": RetentionUnit.YEARS, "action": RetentionAction.DELETE, "type": "Memo"},
        {"name": "Legal Documents - Permanent", "period": 100, "unit": RetentionUnit.YEARS, "action": RetentionAction.REVIEW, "type": "Legal Document"},
    ]

    created_policies = []
    for policy_data in policies_data:
        policy = RetentionPolicy(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=policy_data["name"],
            description=f"Retention policy for {policy_data['type']} documents",
            document_type_id=doc_types.get(policy_data["type"]).id if policy_data["type"] in doc_types else None,
            retention_period=policy_data["period"],
            retention_unit=policy_data["unit"],
            expiry_action=policy_data["action"],
            notify_days_before=30,
            auto_apply=True,
            is_active=True,
            created_by=admin_id,
        )
        db.add(policy)
        created_policies.append(policy)
        print(f"Created retention policy: {policy_data['name']}")

    db.commit()
    return created_policies


def create_legal_holds(db: Session, tenant_id: str, documents: list, admin_id: str) -> list:
    """Create legal holds"""
    existing = db.query(LegalHold).filter(LegalHold.tenant_id == tenant_id).first()
    if existing:
        return db.query(LegalHold).filter(LegalHold.tenant_id == tenant_id).all()

    holds_data = [
        {"name": "Smith vs. Company - Litigation Hold", "case": "2024-CV-1234", "status": LegalHoldStatus.ACTIVE, "counsel": "John Smith, Esq."},
        {"name": "Regulatory Audit 2024", "case": "REG-2024-001", "status": LegalHoldStatus.ACTIVE, "counsel": "Compliance Team"},
        {"name": "Insurance Claim Investigation", "case": "INS-2023-789", "status": LegalHoldStatus.RELEASED, "counsel": "Insurance Counsel"},
    ]

    created_holds = []
    doc_idx = 0
    for hold_data in holds_data:
        hold = LegalHold(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            hold_name=hold_data["name"],
            case_number=hold_data["case"],
            matter_name=hold_data["name"],
            description=f"Legal hold for {hold_data['name']}",
            legal_counsel=hold_data["counsel"],
            status=hold_data["status"],
            hold_start_date=datetime.utcnow() - timedelta(days=random.randint(30, 180)),
            hold_end_date=datetime.utcnow() + timedelta(days=365) if hold_data["status"] == LegalHoldStatus.ACTIVE else None,
            documents_held=random.randint(3, 10),
            total_size_bytes=random.randint(1000000, 50000000),
            created_by=admin_id,
            released_at=datetime.utcnow() - timedelta(days=10) if hold_data["status"] == LegalHoldStatus.RELEASED else None,
            release_reason="Matter resolved" if hold_data["status"] == LegalHoldStatus.RELEASED else None,
        )
        db.add(hold)
        db.commit()
        db.refresh(hold)

        # Add documents to hold
        for i in range(min(5, len(documents) - doc_idx)):
            if doc_idx < len(documents):
                hold_doc = LegalHoldDocument(
                    id=str(uuid.uuid4()),
                    legal_hold_id=hold.id,
                    document_id=documents[doc_idx].id,
                    added_by=admin_id,
                    snapshot_metadata={"title": documents[doc_idx].title, "status": documents[doc_idx].lifecycle_status.value},
                )
                db.add(hold_doc)

                # Update document's legal hold flag
                documents[doc_idx].legal_hold = True
                documents[doc_idx].legal_hold_by = admin_id
                documents[doc_idx].legal_hold_at = datetime.utcnow()
                doc_idx += 1

        created_holds.append(hold)
        print(f"Created legal hold: {hold_data['name']}")

    db.commit()
    return created_holds


def create_worm_records(db: Session, tenant_id: str, documents: list, admin_id: str) -> None:
    """Create WORM locked records"""
    existing = db.query(WORMRecord).filter(WORMRecord.tenant_id == tenant_id).first()
    if existing:
        print("WORM records already exist, skipping...")
        return

    # Lock 5 approved documents
    approved_docs = [d for d in documents if d.lifecycle_status == LifecycleStatus.APPROVED][:5]

    for doc in approved_docs:
        worm = WORMRecord(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            tenant_id=tenant_id,
            locked_by=admin_id,
            lock_reason="Compliance requirement - regulatory retention",
            retention_until=datetime.utcnow() + timedelta(days=365 * 7),
            content_hash=doc.checksum_sha256,
            last_verified_at=datetime.utcnow(),
            last_verified_hash=doc.checksum_sha256,
            verification_count=1,
        )
        db.add(worm)

        # Update document
        doc.is_worm_locked = True
        doc.retention_expiry = datetime.utcnow() + timedelta(days=365 * 7)

    db.commit()
    print(f"Created {len(approved_docs)} WORM records")


def create_compliance_alerts(db: Session, tenant_id: str) -> None:
    """Create compliance alerts"""
    existing = db.query(ComplianceAlert).filter(ComplianceAlert.tenant_id == tenant_id).first()
    if existing:
        print("Compliance alerts already exist, skipping...")
        return

    alerts_data = [
        {"type": "retention_expiry", "severity": "high", "title": "5 Documents Expiring Soon", "desc": "5 documents will reach retention expiry in the next 30 days"},
        {"type": "pii_detected", "severity": "critical", "title": "PII Detected in Upload", "desc": "Sensitive PII data detected in recently uploaded document"},
        {"type": "workflow_overdue", "severity": "medium", "title": "3 Approvals Overdue", "desc": "3 approval requests have exceeded their deadline"},
        {"type": "storage_warning", "severity": "low", "title": "Storage Usage at 75%", "desc": "Storage usage has reached 75% of allocated capacity"},
        {"type": "compliance_violation", "severity": "high", "title": "Unauthorized Access Attempt", "desc": "Multiple failed access attempts detected for restricted document"},
        {"type": "audit_required", "severity": "medium", "title": "Quarterly Audit Due", "desc": "Quarterly compliance audit is due in 15 days"},
        {"type": "retention_expiry", "severity": "medium", "title": "Retention Policy Update Needed", "desc": "3 retention policies need review and update"},
        {"type": "pii_detected", "severity": "high", "title": "Unmasked PII in Report", "desc": "Financial report contains unmasked SSN numbers"},
        {"type": "workflow_overdue", "severity": "low", "title": "Pending Approval Reminder", "desc": "Document approval pending for more than 7 days"},
        {"type": "compliance_violation", "severity": "critical", "title": "Legal Hold Violation", "desc": "Attempted deletion of document under legal hold"},
    ]

    for alert_data in alerts_data:
        alert = ComplianceAlert(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            alert_type=alert_data["type"],
            severity=alert_data["severity"],
            title=alert_data["title"],
            description=alert_data["desc"],
            status=random.choice(["active", "active", "acknowledged"]),
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
        )
        db.add(alert)

    db.commit()
    print(f"Created {len(alerts_data)} compliance alerts")


def create_analytics_metrics(db: Session, tenant_id: str) -> None:
    """Create analytics metrics"""
    existing = db.query(AnalyticsMetric).filter(AnalyticsMetric.tenant_id == tenant_id).first()
    if existing:
        print("Analytics metrics already exist, skipping...")
        return

    # Create daily metrics for the past 30 days
    for days_ago in range(30):
        metric_date = datetime.utcnow() - timedelta(days=days_ago)

        metrics = [
            (MetricType.DOCUMENT_COUNT, random.randint(25, 35)),
            (MetricType.DOCUMENT_UPLOADS, random.randint(2, 10)),
            (MetricType.DOCUMENT_DOWNLOADS, random.randint(5, 25)),
            (MetricType.ACTIVE_USERS, random.randint(3, 8)),
            (MetricType.WORKFLOW_PENDING, random.randint(3, 8)),
            (MetricType.WORKFLOW_COMPLETED, random.randint(1, 5)),
            (MetricType.COMPLIANCE_SCORE, random.randint(92, 99)),
            (MetricType.SEARCH_QUERIES, random.randint(10, 50)),
        ]

        for metric_type, value in metrics:
            metric = AnalyticsMetric(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                metric_type=metric_type,
                granularity=TimeGranularity.DAILY,
                period_start=metric_date.replace(hour=0, minute=0, second=0),
                period_end=metric_date.replace(hour=23, minute=59, second=59),
                value=float(value),
                count=value,
                computed_at=metric_date,
            )
            db.add(metric)

    db.commit()
    print("Created analytics metrics for 30 days")


def create_notifications(db: Session, tenant_id: str, users: dict, admin_id: str) -> None:
    """Create notifications for all users"""
    existing_count = db.query(Notification).filter(Notification.tenant_id == tenant_id).count()
    if existing_count > 10:
        print("Notifications already exist, skipping...")
        return

    notifications_data = [
        {"type": NotificationType.DOCUMENT_SHARED, "title": "Document Shared With You", "msg": "John Manager shared 'Q4 Financial Report' with you.", "priority": NotificationPriority.NORMAL},
        {"type": NotificationType.APPROVAL_REQUESTED, "title": "Approval Required", "msg": "A new contract requires your approval.", "priority": NotificationPriority.HIGH},
        {"type": NotificationType.DOCUMENT_APPROVED, "title": "Document Approved", "msg": "Your document 'Policy Update' has been approved.", "priority": NotificationPriority.NORMAL},
        {"type": NotificationType.DOCUMENT_REJECTED, "title": "Document Rejected", "msg": "Your document 'Draft Memo' was rejected. Please review comments.", "priority": NotificationPriority.HIGH},
        {"type": NotificationType.DOCUMENT_EXPIRING, "title": "Document Expiring Soon", "msg": "3 documents in your folder are expiring in 30 days.", "priority": NotificationPriority.NORMAL},
        {"type": NotificationType.LEGAL_HOLD_APPLIED, "title": "Legal Hold Applied", "msg": "A legal hold has been applied to 'Contract ABC'.", "priority": NotificationPriority.HIGH},
        {"type": NotificationType.SYSTEM_ANNOUNCEMENT, "title": "System Maintenance", "msg": "Scheduled maintenance on Sunday 2 AM - 4 AM.", "priority": NotificationPriority.LOW},
        {"type": NotificationType.APPROVAL_REMINDER, "title": "Approval Reminder", "msg": "You have 3 pending approvals awaiting your review.", "priority": NotificationPriority.NORMAL},
    ]

    all_user_ids = [admin_id] + [u.id for u in users.values()]

    for user_id in all_user_ids:
        for notif_data in notifications_data[:random.randint(3, len(notifications_data))]:
            notification = Notification(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                notification_type=notif_data["type"],
                title=notif_data["title"],
                message=notif_data["msg"],
                priority=notif_data["priority"],
                is_read=random.choice([True, False, False]),
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 168)),
            )
            db.add(notification)

    db.commit()
    print(f"Created notifications for {len(all_user_ids)} users")


def create_chat_sessions(db: Session, tenant_id: str, documents: list, admin_id: str) -> None:
    """Create chat sessions with messages"""
    existing = db.query(ChatSession).filter(ChatSession.tenant_id == tenant_id).first()
    if existing:
        print("Chat sessions already exist, skipping...")
        return

    sessions_data = [
        {
            "title": "Contract Review Questions",
            "messages": [
                {"role": MessageRole.USER, "content": "What are the key terms in the Microsoft license agreement?"},
                {"role": MessageRole.ASSISTANT, "content": "Based on the Software License Agreement, the key terms include:\n\n1. **License Duration**: 3-year term with auto-renewal\n2. **User Limits**: Up to 500 licensed users\n3. **Payment Terms**: Annual billing, Net 30\n4. **Support Level**: Premium 24/7 support included\n5. **Data Handling**: Data remains customer property\n\nWould you like me to elaborate on any of these terms?"},
                {"role": MessageRole.USER, "content": "What about the termination clause?"},
                {"role": MessageRole.ASSISTANT, "content": "The termination clause specifies:\n\n- **For Convenience**: Either party may terminate with 90 days written notice\n- **For Cause**: Immediate termination for material breach if not cured within 30 days\n- **Effect of Termination**: All licenses cease, customer data export within 60 days\n- **Refund Policy**: Pro-rata refund for unused prepaid fees"},
            ]
        },
        {
            "title": "Compliance Policy Inquiry",
            "messages": [
                {"role": MessageRole.USER, "content": "What is our data retention policy for financial documents?"},
                {"role": MessageRole.ASSISTANT, "content": "According to the Data Retention Policy, financial documents must be retained for 7 years from the date of creation. This includes:\n\n- Invoices and receipts\n- Financial statements\n- Tax records\n- Audit documentation\n\nAfter the retention period, documents are automatically archived or deleted based on the configured action."},
            ]
        },
        {
            "title": "HR Document Search",
            "messages": [
                {"role": MessageRole.USER, "content": "Where can I find the remote work policy?"},
                {"role": MessageRole.ASSISTANT, "content": "The Remote Work Policy 2024 is located in the Policies folder. Key highlights:\n\n- Eligible employees may work remotely up to 3 days per week\n- Core hours: 10 AM - 3 PM in local timezone\n- Equipment stipend: $500 for home office setup\n- Security requirements: VPN mandatory, encrypted devices\n\nI can provide more details on any section."},
            ]
        },
        {
            "title": "Technical Documentation",
            "messages": [
                {"role": MessageRole.USER, "content": "What are the API rate limits in our integration spec?"},
                {"role": MessageRole.ASSISTANT, "content": "Based on the API Integration Specification, the rate limits are:\n\n| Endpoint Type | Limit | Window |\n|--------------|-------|--------|\n| Standard | 1000 requests | per minute |\n| Bulk Operations | 100 requests | per minute |\n| File Upload | 50 requests | per minute |\n\nExceeding these limits returns HTTP 429 with retry-after header."},
            ]
        },
        {
            "title": "Legal NDA Questions",
            "messages": [
                {"role": MessageRole.USER, "content": "What is the confidentiality period in the Partner Alpha NDA?"},
                {"role": MessageRole.ASSISTANT, "content": "The NDA with Partner Company Alpha specifies a confidentiality period of 5 years from disclosure date. Key provisions:\n\n- Covers all business and technical information\n- Excludes publicly available information\n- Allows disclosure to employees on need-to-know basis\n- Requires return/destruction of materials upon termination"},
            ]
        },
    ]

    for session_data in sessions_data:
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=admin_id,
            tenant_id=tenant_id,
            title=session_data["title"],
            is_active=True,
            message_count=len(session_data["messages"]),
            last_message_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
            context_document_ids=[documents[random.randint(0, len(documents)-1)].id] if documents else [],
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        for idx, msg_data in enumerate(session_data["messages"]):
            message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                role=msg_data["role"],
                content=msg_data["content"],
                citations=[{"document_id": documents[0].id, "relevance": 0.95}] if msg_data["role"] == MessageRole.ASSISTANT and documents else None,
                model_used="gpt-4" if msg_data["role"] == MessageRole.ASSISTANT else None,
                tokens_used=random.randint(100, 500) if msg_data["role"] == MessageRole.ASSISTANT else None,
                created_at=datetime.utcnow() - timedelta(hours=72-idx),
            )
            db.add(message)

        print(f"Created chat session: {session_data['title']}")

    db.commit()


def create_saved_searches(db: Session, tenant_id: str, admin_id: str) -> None:
    """Create saved searches"""
    existing = db.query(SavedSearch).filter(SavedSearch.tenant_id == tenant_id).first()
    if existing:
        print("Saved searches already exist, skipping...")
        return

    searches_data = [
        {"name": "All Contracts", "query": "contract", "filters": {"document_type": "Contract"}},
        {"name": "Pending Approvals", "query": "", "filters": {"lifecycle_status": "REVIEW"}},
        {"name": "Confidential Documents", "query": "", "filters": {"classification": "CONFIDENTIAL"}},
        {"name": "Recent Uploads", "query": "", "filters": {"date_range": "last_7_days"}},
        {"name": "Legal Department Files", "query": "", "filters": {"department": "Legal"}},
    ]

    for search_data in searches_data:
        search = SavedSearch(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=admin_id,
            name=search_data["name"],
            query=search_data["query"],
            filters=search_data["filters"],
            search_type="keyword",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
        )
        db.add(search)
        print(f"Created saved search: {search_data['name']}")

    db.commit()


def create_bank_statements(db: Session, tenant_id: str, documents: list, admin_id: str) -> None:
    """Create bank statements with transactions"""
    existing = db.query(BankStatement).filter(BankStatement.tenant_id == tenant_id).first()
    if existing:
        print("Bank statements already exist, skipping...")
        return

    if not documents:
        print("No documents available for bank statements")
        return

    statements_data = [
        {
            "bank": "First National Bank",
            "account": "****4521",
            "holder": "Alphha Corporation",
            "opening": 150000.00,
            "transactions": [
                {"date": date(2024, 1, 5), "desc": "Payroll - January", "amount": -45000, "type": TransactionType.DEBIT, "cat": TransactionCategory.SALARY},
                {"date": date(2024, 1, 10), "desc": "Client Payment - ABC Corp", "amount": 75000, "type": TransactionType.CREDIT, "cat": TransactionCategory.TRANSFER},
                {"date": date(2024, 1, 15), "desc": "AWS Services", "amount": -2500, "type": TransactionType.DEBIT, "cat": TransactionCategory.UTILITIES},
                {"date": date(2024, 1, 18), "desc": "Office Rent", "amount": -15000, "type": TransactionType.DEBIT, "cat": TransactionCategory.RENT},
                {"date": date(2024, 1, 20), "desc": "Client Payment - XYZ Ltd", "amount": 50000, "type": TransactionType.CREDIT, "cat": TransactionCategory.TRANSFER},
                {"date": date(2024, 1, 22), "desc": "Insurance Premium", "amount": -3500, "type": TransactionType.DEBIT, "cat": TransactionCategory.INSURANCE},
                {"date": date(2024, 1, 25), "desc": "Vendor Payment - SupplyCo", "amount": -8000, "type": TransactionType.DEBIT, "cat": TransactionCategory.OTHER},
                {"date": date(2024, 1, 28), "desc": "Interest Credit", "amount": 125, "type": TransactionType.CREDIT, "cat": TransactionCategory.OTHER},
            ]
        },
        {
            "bank": "Corporate Bank",
            "account": "****7892",
            "holder": "Alphha Corporation",
            "opening": 250000.00,
            "transactions": [
                {"date": date(2024, 1, 3), "desc": "Investment Return", "amount": 12000, "type": TransactionType.CREDIT, "cat": TransactionCategory.INVESTMENT},
                {"date": date(2024, 1, 8), "desc": "Equipment Purchase", "amount": -35000, "type": TransactionType.DEBIT, "cat": TransactionCategory.OTHER},
                {"date": date(2024, 1, 12), "desc": "Consulting Fee - TechAdvisors", "amount": -8500, "type": TransactionType.DEBIT, "cat": TransactionCategory.OTHER},
                {"date": date(2024, 1, 15), "desc": "Tax Payment", "amount": -25000, "type": TransactionType.DEBIT, "cat": TransactionCategory.OTHER},
                {"date": date(2024, 1, 20), "desc": "Grant Received", "amount": 100000, "type": TransactionType.CREDIT, "cat": TransactionCategory.TRANSFER},
                {"date": date(2024, 1, 25), "desc": "Marketing Campaign", "amount": -15000, "type": TransactionType.DEBIT, "cat": TransactionCategory.OTHER},
            ]
        },
        {
            "bank": "City Credit Union",
            "account": "****3456",
            "holder": "Alphha Operations",
            "opening": 75000.00,
            "transactions": [
                {"date": date(2024, 1, 2), "desc": "ATM Withdrawal", "amount": -500, "type": TransactionType.DEBIT, "cat": TransactionCategory.ATM},
                {"date": date(2024, 1, 5), "desc": "Online Transfer In", "amount": 10000, "type": TransactionType.CREDIT, "cat": TransactionCategory.TRANSFER},
                {"date": date(2024, 1, 10), "desc": "Utility Bill - Electric", "amount": -850, "type": TransactionType.DEBIT, "cat": TransactionCategory.UTILITIES},
                {"date": date(2024, 1, 15), "desc": "POS - Office Supplies", "amount": -320, "type": TransactionType.DEBIT, "cat": TransactionCategory.POS},
                {"date": date(2024, 1, 20), "desc": "Loan Payment", "amount": -5000, "type": TransactionType.DEBIT, "cat": TransactionCategory.LOAN_PAYMENT},
            ]
        },
    ]

    doc_idx = 0
    for stmt_data in statements_data:
        if doc_idx >= len(documents):
            break

        # Calculate closing balance
        closing = Decimal(str(stmt_data["opening"]))
        for txn in stmt_data["transactions"]:
            closing += Decimal(str(txn["amount"]))

        statement = BankStatement(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            document_id=documents[doc_idx].id,
            uploaded_by=admin_id,
            bank_name=stmt_data["bank"],
            account_number=stmt_data["account"],
            account_holder=stmt_data["holder"],
            account_type="current",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            opening_balance=Decimal(str(stmt_data["opening"])),
            closing_balance=closing,
            total_credits=sum(Decimal(str(t["amount"])) for t in stmt_data["transactions"] if t["amount"] > 0),
            total_debits=abs(sum(Decimal(str(t["amount"])) for t in stmt_data["transactions"] if t["amount"] < 0)),
            transaction_count=len(stmt_data["transactions"]),
            currency="USD",
            status=StatementStatus.VERIFIED,
            parsing_confidence=Decimal("95.5"),
            is_verified=True,
            verified_by=admin_id,
            verified_at=datetime.utcnow(),
        )
        db.add(statement)
        db.commit()
        db.refresh(statement)

        # Add transactions
        balance = Decimal(str(stmt_data["opening"]))
        for txn_data in stmt_data["transactions"]:
            balance += Decimal(str(txn_data["amount"]))
            txn = BankTransaction(
                id=str(uuid.uuid4()),
                statement_id=statement.id,
                tenant_id=tenant_id,
                transaction_date=txn_data["date"],
                description=txn_data["desc"],
                transaction_type=txn_data["type"],
                amount=abs(Decimal(str(txn_data["amount"]))),
                balance=balance,
                category=txn_data["cat"],
                category_confidence=Decimal("0.92"),
                is_category_verified=True,
                is_recurring=txn_data["cat"] in [TransactionCategory.SALARY, TransactionCategory.RENT],
            )
            db.add(txn)

        print(f"Created bank statement: {stmt_data['bank']} with {len(stmt_data['transactions'])} transactions")
        doc_idx += 1

    db.commit()


def create_pii_policies(db: Session, tenant_id: str, admin_id: str) -> None:
    """Create PII handling policies"""
    existing = db.query(PIIPolicy).filter(PIIPolicy.tenant_id == tenant_id).first()
    if existing:
        print("PII policies already exist, skipping...")
        return

    policies_data = [
        {"name": "Mask Social Security Numbers", "types": ["SSN"], "action": "MASK"},
        {"name": "Alert on Credit Card Detection", "types": ["CREDIT_CARD"], "action": "ALERT"},
        {"name": "Redact Phone Numbers", "types": ["PHONE"], "action": "REDACT"},
        {"name": "Encrypt Email Addresses", "types": ["EMAIL"], "action": "ENCRYPT"},
    ]

    for policy_data in policies_data:
        policy = PIIPolicy(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=policy_data["name"],
            description=f"Automatically {policy_data['action'].lower()} detected {policy_data['types'][0]}",
            pii_types=policy_data["types"],
            action=policy_data["action"],
            is_active=True,
        )
        db.add(policy)
        print(f"Created PII policy: {policy_data['name']}")

    db.commit()


def create_audit_events(db: Session, tenant_id: str, documents: list, users: dict, admin_id: str) -> None:
    """Create audit events"""
    existing_count = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id).count()
    if existing_count > 50:
        print("Audit events already exist, skipping...")
        return

    all_user_ids = [admin_id] + [u.id for u in users.values()]

    event_types = [
        ("auth.login", "user", "User logged in successfully"),
        ("auth.logout", "user", "User logged out"),
        ("document.create", "document", "Document uploaded"),
        ("document.view", "document", "Document viewed"),
        ("document.download", "document", "Document downloaded"),
        ("document.update", "document", "Document metadata updated"),
        ("workflow.submit", "workflow", "Document submitted for approval"),
        ("workflow.approve", "workflow", "Document approved"),
        ("workflow.reject", "workflow", "Document rejected"),
        ("compliance.legal_hold", "document", "Legal hold applied"),
        ("pii.detected", "document", "PII detected in document"),
        ("search.query", "search", "Search performed"),
    ]

    # Get the max sequence number and last hash to continue chain
    last_event = db.query(AuditEvent).order_by(AuditEvent.sequence_number.desc()).first()
    start_seq = (last_event.sequence_number + 1) if last_event else 1
    # Genesis hash for first event or continue from last event's hash
    prev_hash = last_event.event_hash if last_event else hashlib.sha256(b"GENESIS:alphha-dms").hexdigest()
    for i in range(100):
        event_type, entity_type, description = random.choice(event_types)
        user_id = random.choice(all_user_ids)
        entity_id = documents[random.randint(0, len(documents)-1)].id if documents else str(uuid.uuid4())

        # Create hash chain
        event_data = f"{event_type}:{entity_id}:{user_id}:{datetime.utcnow().isoformat()}"
        current_hash = hashlib.sha256((event_data + (prev_hash or "")).encode()).hexdigest()

        event = AuditEvent(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            sequence_number=start_seq + i,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            ip_address=f"192.168.1.{random.randint(1, 254)}",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            event_metadata={"description": description},
            event_hash=current_hash,
            previous_hash=prev_hash,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 720)),
        )
        db.add(event)
        prev_hash = current_hash

    db.commit()
    print("Created 100 audit events with hash chain")


def seed_all():
    """Run all seed functions"""
    print("=" * 60)
    print("Alphha DMS - Comprehensive Database Seeding")
    print("=" * 60)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")

    db = SessionLocal()
    try:
        # Core setup
        tenant = create_default_tenant(db)
        roles = create_default_roles(db, tenant.id)
        admin = create_admin_user(db, tenant.id, roles["super_admin"])
        users = create_test_users(db, tenant.id, roles)
        doc_types = create_document_types(db, tenant.id)
        departments = create_departments(db, tenant.id)
        folders = create_default_folders(db, tenant.id)

        # PII patterns
        try:
            initialize_pii_patterns(db, tenant.id)
        except Exception as e:
            print(f"Skipping PII patterns: {e}")

        # Documents
        documents = create_sample_documents(db, tenant.id, doc_types, departments, folders, admin.id)
        create_document_versions(db, documents, admin.id)

        # Workflows
        workflows = create_sample_workflows(db, tenant.id, roles)
        create_approval_requests(db, tenant.id, documents, workflows, users, admin.id)

        # Compliance
        create_retention_policies(db, tenant.id, doc_types, admin.id)
        create_legal_holds(db, tenant.id, documents, admin.id)
        create_worm_records(db, tenant.id, documents, admin.id)

        # Analytics
        create_compliance_alerts(db, tenant.id)
        create_analytics_metrics(db, tenant.id)

        # Notifications
        create_notifications(db, tenant.id, users, admin.id)

        # Chat
        create_chat_sessions(db, tenant.id, documents, admin.id)

        # Search
        create_saved_searches(db, tenant.id, admin.id)

        # BSI
        create_bank_statements(db, tenant.id, documents, admin.id)

        # PII Policies
        try:
            create_pii_policies(db, tenant.id, admin.id)
        except Exception as e:
            print(f"Skipping PII policies: {e}")

        # Audit
        create_audit_events(db, tenant.id, documents, users, admin.id)

        print("\n" + "=" * 60)
        print("Database seeding completed successfully!")
        print("=" * 60)
        print("\nTest User Credentials:")
        print("-" * 40)
        print("  Admin:      admin@alphha.local / admin123")
        print("  Manager:    manager@alphha.local / password123")
        print("  Legal:      legal@alphha.local / password123")
        print("  Compliance: compliance@alphha.local / password123")
        print("  User:       user@alphha.local / password123")
        print("  Viewer:     viewer@alphha.local / password123")
        print("\n  Change passwords in production!")

        print("\nData Created:")
        print("-" * 40)
        print(f"  Documents: {len(documents)}")
        print(f"  Workflows: {len(workflows)}")
        print(f"  Approval Requests: 15+")
        print(f"  Legal Holds: 3")
        print(f"  Compliance Alerts: 10")
        print(f"  Notifications: 40+")
        print(f"  Chat Sessions: 5")
        print(f"  Bank Statements: 3")
        print(f"  Audit Events: 100")

    except Exception as e:
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
