"""Realistic seed data for Alphha DMS."""
import uuid
import os
import hashlib
import random
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models import *
from app.models.entities import Customer, Vendor, License
from app.core.security import get_password_hash


# Realistic data
CUSTOMERS = [
    {"external_id": "CUST-2024-001", "name": "Mohammed Al-Rashid", "email": "m.alrashid@email.com", "phone": "+971501234567", "id_number": "784-1990-1234567-1"},
    {"external_id": "CUST-2024-002", "name": "Sarah Johnson", "email": "sarah.j@company.com", "phone": "+971502345678", "id_number": "784-1985-2345678-2"},
    {"external_id": "CUST-2024-003", "name": "Ahmed Hassan", "email": "ahmed.h@business.ae", "phone": "+971503456789", "id_number": "784-1992-3456789-3"},
    {"external_id": "CUST-2024-004", "name": "Fatima Al-Maktoum", "email": "fatima.m@corp.ae", "phone": "+971504567890", "id_number": "784-1988-4567890-4"},
    {"external_id": "CUST-2024-005", "name": "John Smith", "email": "john.smith@intl.com", "phone": "+971505678901", "id_number": "GBR-12345678"},
]

VENDORS = [
    {"external_id": "VND-001", "name": "Emirates Office Supplies LLC", "tax_id": "TRN-100234567890123", "email": "sales@emiratesoffice.ae", "phone": "+97142345678"},
    {"external_id": "VND-002", "name": "Gulf IT Solutions", "tax_id": "TRN-100345678901234", "email": "info@gulfitsolutions.com", "phone": "+97143456789"},
    {"external_id": "VND-003", "name": "Al Futtaim Services", "tax_id": "TRN-100456789012345", "email": "corporate@alfuttaim.ae", "phone": "+97144567890"},
    {"external_id": "VND-004", "name": "Dubai Cleaning Services", "tax_id": "TRN-100567890123456", "email": "contracts@dubaicleaning.ae", "phone": "+97145678901"},
    {"external_id": "VND-005", "name": "National Security Systems", "tax_id": "TRN-100678901234567", "email": "sales@nss.ae", "phone": "+97146789012"},
]

DEPARTMENTS = [
    {"name": "Human Resources", "code": "HR"},
    {"name": "Finance & Accounting", "code": "FIN"},
    {"name": "Legal & Compliance", "code": "LEGAL"},
    {"name": "Information Technology", "code": "IT"},
    {"name": "Operations", "code": "OPS"},
    {"name": "Marketing", "code": "MKT"},
    {"name": "Procurement", "code": "PROC"},
]

DOCUMENT_TYPES = [
    {"name": "Invoice", "icon": "file-invoice", "retention_days": 2555, "approval_flow_type": "AUTO"},
    {"name": "Contract", "icon": "file-contract", "retention_days": 3650, "approval_flow_type": "MANUAL"},
    {"name": "KYC Document", "icon": "id-card", "retention_days": 1825, "approval_flow_type": "MANUAL"},
    {"name": "Bank Statement", "icon": "bank", "retention_days": 2555, "approval_flow_type": "AUTO"},
    {"name": "Purchase Order", "icon": "shopping-cart", "retention_days": 2555, "approval_flow_type": "MANUAL"},
    {"name": "Employee Document", "icon": "user", "retention_days": 3650, "approval_flow_type": "MANUAL"},
    {"name": "Policy Document", "icon": "book", "retention_days": None, "approval_flow_type": "MANUAL"},
    {"name": "Meeting Minutes", "icon": "clipboard", "retention_days": 1095, "approval_flow_type": "NONE"},
    {"name": "Passport Copy", "icon": "passport", "retention_days": 1825, "approval_flow_type": "AUTO"},
    {"name": "Trade License", "icon": "certificate", "retention_days": 3650, "approval_flow_type": "MANUAL"},
]

USERS = [
    {"email": "admin@alphha.local", "full_name": "System Administrator", "role": "super_admin", "department": "IT"},
    {"email": "manager@alphha.local", "full_name": "Ahmed Al-Farsi", "role": "manager", "department": "FIN"},
    {"email": "legal@alphha.local", "full_name": "Sarah Thompson", "role": "legal", "department": "LEGAL"},
    {"email": "compliance@alphha.local", "full_name": "Omar Khalid", "role": "compliance", "department": "LEGAL"},
    {"email": "user@alphha.local", "full_name": "Fatima Al-Zahra", "role": "user", "department": "OPS"},
    {"email": "viewer@alphha.local", "full_name": "Layla Hassan", "role": "viewer", "department": "PROC"},
    {"email": "john.it@alphha.local", "full_name": "John Anderson", "role": "admin", "department": "IT"},
    {"email": "mohammed.hr@alphha.local", "full_name": "Mohammed Ibrahim", "role": "manager", "department": "HR"},
]

REALISTIC_DOCUMENTS = [
    # Customer documents
    {"title": "Emirates ID - Mohammed Al-Rashid", "source": "CUSTOMER", "customer": "CUST-2024-001", "type": "KYC Document", "status": "APPROVED"},
    {"title": "Passport Copy - Mohammed Al-Rashid", "source": "CUSTOMER", "customer": "CUST-2024-001", "type": "Passport Copy", "status": "APPROVED"},
    {"title": "Bank Statement Jan 2026 - Sarah Johnson", "source": "CUSTOMER", "customer": "CUST-2024-002", "type": "Bank Statement", "status": "REVIEW"},
    {"title": "Employment Contract - Ahmed Hassan", "source": "CUSTOMER", "customer": "CUST-2024-003", "type": "Contract", "status": "APPROVED"},
    {"title": "Salary Certificate - Fatima Al-Maktoum", "source": "CUSTOMER", "customer": "CUST-2024-004", "type": "Employee Document", "status": "APPROVED"},
    
    # Vendor documents
    {"title": "Invoice INV-2026-0001 - Emirates Office Supplies", "source": "VENDOR", "vendor": "VND-001", "type": "Invoice", "status": "APPROVED"},
    {"title": "Service Agreement - Gulf IT Solutions", "source": "VENDOR", "vendor": "VND-002", "type": "Contract", "status": "APPROVED"},
    {"title": "Invoice INV-2026-0045 - Al Futtaim Services", "source": "VENDOR", "vendor": "VND-003", "type": "Invoice", "status": "REVIEW"},
    {"title": "Annual Maintenance Contract - Dubai Cleaning", "source": "VENDOR", "vendor": "VND-004", "type": "Contract", "status": "DRAFT"},
    {"title": "Security System Proposal - NSS", "source": "VENDOR", "vendor": "VND-005", "type": "Purchase Order", "status": "REVIEW"},
    
    # Internal documents
    {"title": "Employee Handbook 2026", "source": "INTERNAL", "department": "HR", "type": "Policy Document", "status": "APPROVED"},
    {"title": "IT Security Policy v3.2", "source": "INTERNAL", "department": "IT", "type": "Policy Document", "status": "APPROVED"},
    {"title": "Q4 2025 Financial Report", "source": "INTERNAL", "department": "FIN", "type": "Meeting Minutes", "status": "APPROVED"},
    {"title": "Board Meeting Minutes - Dec 2025", "source": "INTERNAL", "department": "LEGAL", "type": "Meeting Minutes", "status": "APPROVED"},
    {"title": "Procurement Guidelines 2026", "source": "INTERNAL", "department": "PROC", "type": "Policy Document", "status": "REVIEW"},
    {"title": "Trade License Renewal 2026", "source": "INTERNAL", "department": "LEGAL", "type": "Trade License", "status": "APPROVED"},
    {"title": "Marketing Budget Proposal Q1", "source": "INTERNAL", "department": "MKT", "type": "Meeting Minutes", "status": "DRAFT"},
    {"title": "Data Protection Policy", "source": "INTERNAL", "department": "IT", "type": "Policy Document", "status": "APPROVED"},
]

CUSTOM_FIELDS = [
    {"name": "Invoice Number", "field_key": "invoice_number", "field_type": "TEXT", "doc_type": "Invoice"},
    {"name": "Invoice Amount", "field_key": "invoice_amount", "field_type": "NUMBER", "doc_type": "Invoice"},
    {"name": "Due Date", "field_key": "due_date", "field_type": "DATE", "doc_type": "Invoice"},
    {"name": "Contract Value", "field_key": "contract_value", "field_type": "NUMBER", "doc_type": "Contract"},
    {"name": "Contract Start Date", "field_key": "contract_start", "field_type": "DATE", "doc_type": "Contract"},
    {"name": "Contract End Date", "field_key": "contract_end", "field_type": "DATE", "doc_type": "Contract"},
    {"name": "ID Type", "field_key": "id_type", "field_type": "SELECT", "doc_type": "KYC Document", "options": ["Emirates ID", "Passport", "Driving License", "Visa"]},
    {"name": "Expiry Date", "field_key": "expiry_date", "field_type": "DATE", "doc_type": "KYC Document"},
    {"name": "Statement Period", "field_key": "statement_period", "field_type": "TEXT", "doc_type": "Bank Statement"},
    {"name": "Account Number", "field_key": "account_number", "field_type": "TEXT", "doc_type": "Bank Statement"},
]


def seed_all():
    """Seed all realistic data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Create Tenant
        tenant = db.query(Tenant).filter(Tenant.subdomain == "default").first()
        if not tenant:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Alphha Government Services",
                subdomain="default",
                is_active=True,
                license_key="ADMS-GOVT-2026-ENT",
                license_expires=date.today() + timedelta(days=365),
                primary_color="#1E3A5F",
                config={"features": {"ocr_enabled": True, "pii_detection": True, "ai_chat": True}}
            )
            db.add(tenant)
            db.commit()
            print("✓ Created tenant")
        
        # 2. Create Roles
        roles = {}
        role_defs = {
            "super_admin": {"permissions": ["*"], "is_system_role": True},
            "admin": {"permissions": ["documents:*", "users:*", "workflows:*", "admin:*"], "is_system_role": True},
            "legal": {"permissions": ["documents:read", "documents:legal_hold", "audit:*", "compliance:*"], "is_system_role": True},
            "compliance": {"permissions": ["documents:read", "audit:*", "pii:view", "compliance:*"], "is_system_role": True},
            "manager": {"permissions": ["documents:*", "workflows:approve", "analytics:view"], "is_system_role": True},
            "user": {"permissions": ["documents:create", "documents:read", "documents:update"], "is_system_role": True},
            "viewer": {"permissions": ["documents:read"], "is_system_role": True},
        }
        
        for role_name, role_data in role_defs.items():
            role = db.query(Role).filter(Role.tenant_id == tenant.id, Role.name == role_name).first()
            if not role:
                role = Role(id=str(uuid.uuid4()), tenant_id=tenant.id, name=role_name, description=f"{role_name} role", **role_data)
                db.add(role)
            roles[role_name] = role
        db.commit()
        print("✓ Created roles")
        
        # 3. Create Departments
        depts = {}
        for d in DEPARTMENTS:
            dept = db.query(Department).filter(Department.tenant_id == tenant.id, Department.code == d["code"]).first()
            if not dept:
                dept = Department(id=str(uuid.uuid4()), tenant_id=tenant.id, **d)
                db.add(dept)
            depts[d["code"]] = dept
        db.commit()
        print("✓ Created departments")
        
        # 4. Create Document Types
        doc_types = {}
        for dt in DOCUMENT_TYPES:
            dtype = db.query(DocumentType).filter(DocumentType.tenant_id == tenant.id, DocumentType.name == dt["name"]).first()
            if not dtype:
                dtype = DocumentType(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant.id,
                    name=dt["name"],
                    icon=dt["icon"],
                    retention_days=dt["retention_days"],
                    approval_flow_type=ApprovalFlowType(dt["approval_flow_type"])
                )
                db.add(dtype)
            doc_types[dt["name"]] = dtype
        db.commit()
        print("✓ Created document types")
        
        # 5. Create Custom Fields
        for cf in CUSTOM_FIELDS:
            existing = db.query(CustomField).filter(
                CustomField.tenant_id == tenant.id,
                CustomField.field_key == cf["field_key"]
            ).first()
            if not existing:
                dtype = doc_types.get(cf.get("doc_type"))
                field = CustomField(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant.id,
                    name=cf["name"],
                    field_key=cf["field_key"],
                    field_type=FieldType(cf["field_type"]),
                    document_type_id=dtype.id if dtype else None,
                    options=cf.get("options"),
                    required=False
                )
                db.add(field)
        db.commit()
        print("✓ Created custom fields")
        
        # 6. Create Users
        users = {}
        for u in USERS:
            user = db.query(User).filter(User.email == u["email"]).first()
            if not user:
                pwd = "admin123" if u["email"] == "admin@alphha.local" else "password123"
                user = User(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant.id,
                    email=u["email"],
                    full_name=u["full_name"],
                    password_hash=get_password_hash(pwd),
                    is_active=True,
                    is_superuser=u["role"] in ["super_admin", "admin"],
                    department=u["department"]
                )
                db.add(user)
                db.commit()
                
                # Assign role using relationship
                role = roles.get(u["role"])
                if role:
                    user.roles.append(role)
                    db.commit()
            users[u["email"]] = user
        db.commit()
        print("✓ Created users")
        
        # 7. Create Customers
        customers = {}
        for c in CUSTOMERS:
            cust = db.query(Customer).filter(Customer.tenant_id == tenant.id, Customer.external_id == c["external_id"]).first()
            if not cust:
                cust = Customer(id=str(uuid.uuid4()), tenant_id=tenant.id, **c)
                db.add(cust)
            customers[c["external_id"]] = cust
        db.commit()
        print("✓ Created customers")
        
        # 8. Create Vendors
        vendors = {}
        for v in VENDORS:
            vnd = db.query(Vendor).filter(Vendor.tenant_id == tenant.id, Vendor.external_id == v["external_id"]).first()
            if not vnd:
                vnd = Vendor(id=str(uuid.uuid4()), tenant_id=tenant.id, **v)
                db.add(vnd)
            vendors[v["external_id"]] = vnd
        db.commit()
        print("✓ Created vendors")
        
        # 9. Create Documents
        admin_user = users.get("admin@alphha.local")
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        for doc_data in REALISTIC_DOCUMENTS:
            existing = db.query(Document).filter(Document.title == doc_data["title"], Document.tenant_id == tenant.id).first()
            if existing:
                continue
            
            # Create dummy file
            doc_id = str(uuid.uuid4())
            file_name = f"{doc_data['title'].replace(' ', '_').replace('-', '_')}.pdf"
            file_path = os.path.join(upload_dir, doc_id, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create minimal PDF content
            pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"
            with open(file_path, "wb") as f:
                f.write(pdf_content)
            
            checksum = hashlib.sha256(pdf_content).hexdigest()
            
            # Determine source type and IDs
            source_type = SourceType(doc_data["source"])
            customer_id = doc_data.get("customer")
            vendor_id = doc_data.get("vendor")
            dept_code = doc_data.get("department")
            dept = depts.get(dept_code) if dept_code else None
            
            # Custom metadata based on document type
            custom_meta = {}
            if doc_data["type"] == "Invoice":
                custom_meta = {
                    "invoice_number": f"INV-2026-{random.randint(1000, 9999)}",
                    "invoice_amount": round(random.uniform(1000, 50000), 2),
                    "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                }
            elif doc_data["type"] == "Contract":
                custom_meta = {
                    "contract_value": round(random.uniform(10000, 500000), 2),
                    "contract_start": datetime.now().strftime("%Y-%m-%d"),
                    "contract_end": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                }
            elif doc_data["type"] == "KYC Document":
                custom_meta = {
                    "id_type": random.choice(["Emirates ID", "Passport", "Visa"]),
                    "expiry_date": (datetime.now() + timedelta(days=random.randint(180, 1095))).strftime("%Y-%m-%d")
                }
            elif doc_data["type"] == "Bank Statement":
                custom_meta = {
                    "statement_period": "January 2026",
                    "account_number": f"****{random.randint(1000, 9999)}"
                }
            
            doc = Document(
                id=doc_id,
                tenant_id=tenant.id,
                title=doc_data["title"],
                file_name=file_name,
                file_path=file_path,
                file_size=len(pdf_content),
                mime_type="application/pdf",
                page_count=1,
                checksum_sha256=checksum,
                source_type=source_type,
                customer_id=customer_id,
                vendor_id=vendor_id,
                department_id=dept.id if dept else None,
                document_type_id=doc_types[doc_data["type"]].id,
                classification=Classification.INTERNAL,
                lifecycle_status=LifecycleStatus(doc_data["status"]),
                ocr_status=OCRStatus.COMPLETED,
                ocr_text=f"Sample OCR text for {doc_data['title']}",
                custom_metadata=custom_meta,
                created_by=admin_user.id,
                updated_by=admin_user.id
            )
            db.add(doc)
            
            # Create version
            version = DocumentVersion(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                version_number=1,
                file_path=file_path,
                file_size=len(pdf_content),
                checksum_sha256=checksum,
                is_current=True,
                created_by=admin_user.id,
                metadata_snapshot=custom_meta
            )
            db.add(version)
            doc.current_version_id = version.id
        
        db.commit()
        print("✓ Created documents")
        
        # 10. Create License
        existing_license = db.query(License).filter(License.tenant_id == tenant.id).first()
        if not existing_license:
            license_key = f"ADMS-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
            checksum_data = f"{license_key}:{tenant.id}:{(datetime.utcnow() + timedelta(days=365)).isoformat()}"
            lic = License(
                id=str(uuid.uuid4()),
                license_key=license_key,
                tenant_id=tenant.id,
                expires_at=datetime.utcnow() + timedelta(days=365),
                checksum=hashlib.sha256(checksum_data.encode()).hexdigest()
            )
            db.add(lic)
            db.commit()
            print("✓ Created license")
        
        # 11. Create sample notifications
        for i in range(5):
            notif = Notification(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                notification_type=random.choice([NotificationType.DOCUMENT_APPROVED, NotificationType.APPROVAL_REQUESTED, NotificationType.DOCUMENT_SHARED]),
                title=f"Sample Notification {i+1}",
                message=f"This is a sample notification message #{i+1}",
                priority=random.choice([NotificationPriority.LOW, NotificationPriority.NORMAL, NotificationPriority.HIGH]),
                is_read=random.choice([True, False])
            )
            db.add(notif)
        db.commit()
        print("✓ Created notifications")
        
        # 12. Create retention policies
        for dt_name, dtype in doc_types.items():
            if dtype.retention_days:
                existing = db.query(RetentionPolicy).filter(
                    RetentionPolicy.tenant_id == tenant.id,
                    RetentionPolicy.document_type_id == dtype.id
                ).first()
                if not existing:
                    policy = RetentionPolicy(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant.id,
                        name=f"{dt_name} Retention",
                        document_type_id=dtype.id,
                        retention_period=dtype.retention_days,
                        retention_unit=RetentionUnit.DAYS,
                        expiry_action=RetentionAction.ARCHIVE,
                        is_active=True
                    )
                    db.add(policy)
        db.commit()
        print("✓ Created retention policies")
        
        print("\n✅ Seed data completed successfully!")
        print(f"   - Tenant: {tenant.name}")
        print(f"   - Users: {len(USERS)}")
        print(f"   - Customers: {len(CUSTOMERS)}")
        print(f"   - Vendors: {len(VENDORS)}")
        print(f"   - Documents: {len(REALISTIC_DOCUMENTS)}")
        print("\n   Login: admin@alphha.local / admin123")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
