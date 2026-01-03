"""Seed data script for initial setup"""
import uuid
from datetime import datetime
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
from app.core.security import get_password_hash
from app.services.pii_service import PIIService


def create_default_tenant(db: Session) -> Tenant:
    """Create default tenant"""
    tenant = db.query(Tenant).filter(Tenant.subdomain == "default").first()
    if not tenant:
        from datetime import date, timedelta
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Alphha Default",
            subdomain="default",
            is_active=True,
            license_key="ALPHHA-DEFAULT-2026-ENTERPRISE",
            license_expires=date.today() + timedelta(days=365),
            primary_color="#1E3A5F",
            config={
                "theme": {
                    "primary_color": "#1E3A5F",
                    "secondary_color": "#2E7D32",
                },
                "features": {
                    "ocr_enabled": True,
                    "pii_detection": True,
                    "ai_chat": True,
                }
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
        "super_admin": {
            "name": "super_admin",
            "description": "Full system access with all permissions",
            "permissions": ["*"],
            "is_system_role": True,
        },
        "admin": {
            "name": "admin",
            "description": "Administrative access to tenant",
            "permissions": [
                "documents:*",
                "users:*",
                "roles:read",
                "audit:read",
                "settings:*",
                "workflows:*",
                "pii:*",
                "analytics:read",
                "search:advanced",
                "chat:use",
            ],
            "is_system_role": True,
        },
        "legal": {
            "name": "legal",
            "description": "Legal team with document hold capabilities",
            "permissions": [
                "documents:read",
                "documents:download",
                "documents:legal_hold",
                "audit:read",
                "audit:export",
                "search:advanced",
            ],
            "is_system_role": True,
        },
        "compliance": {
            "name": "compliance",
            "description": "Compliance and audit access",
            "permissions": [
                "documents:read",
                "documents:approve",
                "audit:*",
                "pii:view",
                "analytics:read",
                "search:advanced",
            ],
            "is_system_role": True,
        },
        "manager": {
            "name": "manager",
            "description": "Team management and document approval",
            "permissions": [
                "documents:*",
                "documents:approve",
                "users:read",
                "workflows:read",
                "analytics:read",
                "search:advanced",
                "chat:use",
            ],
            "is_system_role": True,
        },
        "user": {
            "name": "user",
            "description": "Standard document user",
            "permissions": [
                "documents:create",
                "documents:read",
                "documents:update",
                "documents:download",
                "documents:share",
                "search:advanced",
                "chat:use",
            ],
            "is_system_role": True,
        },
        "viewer": {
            "name": "viewer",
            "description": "Read-only access",
            "permissions": [
                "documents:read",
                "documents:download",
            ],
            "is_system_role": True,
        },
    }

    created_roles = {}
    for role_key, role_data in roles.items():
        existing = db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == role_data["name"],
        ).first()

        if not existing:
            role = Role(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                **role_data,
            )
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
            password_hash=get_password_hash("admin123"),  # Change in production!
            is_active=True,
            is_superuser=True,
            clearance_level="RESTRICTED",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Assign admin role via relationship
        user.roles.append(admin_role)
        db.commit()

        print("Created admin user: admin@alphha.local / admin123")
        return user
    return existing


def create_document_types(db: Session, tenant_id: str) -> None:
    """Create default document types"""
    types = [
        {"name": "Contract", "retention_days": 2555, "description": "Legal contracts and agreements"},
        {"name": "Invoice", "retention_days": 1825, "description": "Financial invoices"},
        {"name": "Report", "retention_days": 365, "description": "Business reports"},
        {"name": "Memo", "retention_days": 365, "description": "Internal memos"},
        {"name": "Policy", "retention_days": 3650, "description": "Company policies"},
        {"name": "Legal Document", "retention_days": 2555, "description": "Legal documents"},
        {"name": "Financial Statement", "retention_days": 2555, "description": "Financial statements"},
        {"name": "HR Document", "retention_days": 2555, "description": "Human resources documents"},
        {"name": "Technical Specification", "retention_days": 1825, "description": "Technical specs"},
        {"name": "General", "retention_days": 365, "description": "General documents"},
    ]

    for type_data in types:
        existing = db.query(DocumentType).filter(
            DocumentType.tenant_id == tenant_id,
            DocumentType.name == type_data["name"],
        ).first()

        if not existing:
            doc_type = DocumentType(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                **type_data,
            )
            db.add(doc_type)
            print(f"Created document type: {type_data['name']}")

    db.commit()


def create_departments(db: Session, tenant_id: str) -> None:
    """Create default departments"""
    departments = [
        {"name": "Legal", "code": "LEGAL"},
        {"name": "Finance", "code": "FINANCE"},
        {"name": "Human Resources", "code": "HR"},
        {"name": "Operations", "code": "OPS"},
        {"name": "Technology", "code": "TECH"},
        {"name": "Compliance", "code": "COMPLIANCE"},
        {"name": "Administration", "code": "ADMIN"},
    ]

    for dept_data in departments:
        existing = db.query(Department).filter(
            Department.tenant_id == tenant_id,
            Department.code == dept_data["code"],
        ).first()

        if not existing:
            dept = Department(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                **dept_data,
            )
            db.add(dept)
            print(f"Created department: {dept_data['name']}")

    db.commit()


def create_default_folders(db: Session, tenant_id: str) -> None:
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

    for folder_data in folders:
        existing = db.query(Folder).filter(
            Folder.tenant_id == tenant_id,
            Folder.path == folder_data["path"],
        ).first()

        if not existing:
            folder = Folder(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                **folder_data,
            )
            db.add(folder)
            print(f"Created folder: {folder_data['path']}")

    db.commit()


def initialize_pii_patterns(db: Session, tenant_id: str) -> None:
    """Initialize system PII patterns"""
    pii_service = PIIService(db)
    pii_service.initialize_system_patterns(tenant_id)
    print("Initialized PII detection patterns")


def create_test_users(db: Session, tenant_id: str, roles: dict) -> list:
    """Create test users for different roles"""
    test_users = [
        {
            "email": "manager@alphha.local",
            "full_name": "John Manager",
            "role": "manager",
            "clearance_level": "CONFIDENTIAL",
        },
        {
            "email": "legal@alphha.local",
            "full_name": "Sarah Legal",
            "role": "legal",
            "clearance_level": "RESTRICTED",
        },
        {
            "email": "compliance@alphha.local",
            "full_name": "Mike Compliance",
            "role": "compliance",
            "clearance_level": "CONFIDENTIAL",
        },
        {
            "email": "user@alphha.local",
            "full_name": "Jane User",
            "role": "user",
            "clearance_level": "UNCLASSIFIED",
        },
        {
            "email": "viewer@alphha.local",
            "full_name": "Bob Viewer",
            "role": "viewer",
            "clearance_level": "UNCLASSIFIED",
        },
    ]

    created_users = []
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

            # Assign role via relationship
            user.roles.append(roles[user_data["role"]])
            db.commit()

            created_users.append(user)
            print(f"Created test user: {user_data['email']}")

    return created_users


def create_sample_workflows(db: Session, tenant_id: str) -> None:
    """Create sample approval workflows"""
    from app.models.workflow import ApprovalWorkflow, ApprovalStep, WorkflowType, ApprovalStrategy

    workflows = [
        {
            "name": "Document Review",
            "description": "Standard document review workflow",
            "workflow_type": WorkflowType.SEQUENTIAL,
            "steps": [
                {"name": "Manager Review", "order": 1, "strategy": ApprovalStrategy.ANY},
                {"name": "Compliance Check", "order": 2, "strategy": ApprovalStrategy.ANY},
            ]
        },
        {
            "name": "Contract Approval",
            "description": "Multi-level contract approval",
            "workflow_type": WorkflowType.SEQUENTIAL,
            "steps": [
                {"name": "Legal Review", "order": 1, "strategy": ApprovalStrategy.ALL},
                {"name": "Finance Approval", "order": 2, "strategy": ApprovalStrategy.ANY},
                {"name": "Executive Sign-off", "order": 3, "strategy": ApprovalStrategy.ANY},
            ]
        },
    ]

    for wf_data in workflows:
        existing = db.query(ApprovalWorkflow).filter(
            ApprovalWorkflow.tenant_id == tenant_id,
            ApprovalWorkflow.name == wf_data["name"],
        ).first()

        if not existing:
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
                    approval_strategy=step_data["strategy"],
                )
                db.add(step)

            db.commit()
            print(f"Created workflow: {wf_data['name']}")


def create_sample_tags(db: Session, tenant_id: str) -> None:
    """Create sample taxonomy tags"""
    from app.models.taxonomy import Tag

    tags = [
        {"name": "Urgent", "color": "#FF0000"},
        {"name": "Confidential", "color": "#8B0000"},
        {"name": "Draft", "color": "#FFA500"},
        {"name": "Final", "color": "#008000"},
        {"name": "Archived", "color": "#808080"},
        {"name": "Legal", "color": "#0000FF"},
        {"name": "Finance", "color": "#006400"},
        {"name": "HR", "color": "#800080"},
        {"name": "Technical", "color": "#4169E1"},
        {"name": "Policy", "color": "#DAA520"},
    ]

    for tag_data in tags:
        existing = db.query(Tag).filter(
            Tag.tenant_id == tenant_id,
            Tag.name == tag_data["name"],
        ).first()

        if not existing:
            tag = Tag(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=tag_data["name"],
                color=tag_data["color"],
                is_system=True,
            )
            db.add(tag)
            print(f"Created tag: {tag_data['name']}")

    db.commit()


def create_sample_notifications(db: Session, tenant_id: str, user_id: str) -> None:
    """Create sample notifications"""
    from app.models.notifications import Notification, NotificationType, NotificationPriority

    notifications = [
        {
            "notification_type": NotificationType.DOCUMENT_SHARED,
            "title": "Document Shared With You",
            "message": "John Manager shared 'Q4 Financial Report' with you.",
            "priority": NotificationPriority.NORMAL,
        },
        {
            "notification_type": NotificationType.APPROVAL_REQUESTED,
            "title": "Approval Required",
            "message": "A new contract requires your approval.",
            "priority": NotificationPriority.HIGH,
        },
        {
            "notification_type": NotificationType.SYSTEM_ANNOUNCEMENT,
            "title": "System Maintenance",
            "message": "Scheduled maintenance on Sunday 2 AM - 4 AM.",
            "priority": NotificationPriority.LOW,
        },
    ]

    for notif_data in notifications:
        notification = Notification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notif_data["notification_type"],
            title=notif_data["title"],
            message=notif_data["message"],
            priority=notif_data["priority"],
            is_read=False,
        )
        db.add(notification)
        print(f"Created notification: {notif_data['title']}")

    db.commit()


def seed_all():
    """Run all seed functions"""
    print("=" * 50)
    print("Alphha DMS - Database Seeding")
    print("=" * 50)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")

    db = SessionLocal()
    try:
        # Create tenant
        tenant = create_default_tenant(db)

        # Create roles
        roles = create_default_roles(db, tenant.id)

        # Create admin user
        admin = create_admin_user(db, tenant.id, roles["super_admin"])

        # Create test users
        create_test_users(db, tenant.id, roles)

        # Create document types
        create_document_types(db, tenant.id)

        # Create departments
        create_departments(db, tenant.id)

        # Create folders
        create_default_folders(db, tenant.id)

        # Initialize PII patterns
        initialize_pii_patterns(db, tenant.id)

        # Create sample tags (skip if Tag model not available)
        try:
            create_sample_tags(db, tenant.id)
        except Exception as e:
            print(f"Skipping tags: {e}")

        # Create sample notifications for admin
        try:
            create_sample_notifications(db, tenant.id, admin.id)
        except Exception as e:
            print(f"Skipping notifications: {e}")

        print("=" * 50)
        print("Database seeding completed successfully!")
        print("=" * 50)
        print("\nTest User Credentials:")
        print("-" * 40)
        print("  Admin:      admin@alphha.local / admin123")
        print("  Manager:    manager@alphha.local / password123")
        print("  Legal:      legal@alphha.local / password123")
        print("  Compliance: compliance@alphha.local / password123")
        print("  User:       user@alphha.local / password123")
        print("  Viewer:     viewer@alphha.local / password123")
        print("\n⚠️  Change passwords in production!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
