# Alphha DMS

Enterprise-grade Document Management System with AI-powered capabilities, compliance features, and multi-tenant architecture.

## Features

### Core Document Management
- Document upload with source type classification (Customer/Vendor/Internal)
- Version control with diff viewer and restore capability
- Document lifecycle management (Draft → Review → Approved → Archived)
- Check-in/Check-out model for document locking
- Custom metadata fields (Text, Number, Date, Select, Multi-Select, Boolean)

### Compliance & Security
- WORM (Write-Once-Read-Many) records management
- Legal hold & e-discovery with evidence export
- Retention policies with auto-archive
- Immutable audit ledger with hash chaining
- DLP & PII detection with masking
- Role-based access control (RBAC)

### AI & Intelligence
- OCR with Mistral AI integration
- Semantic search with vector embeddings
- AI-powered Q&A chatbot
- Bank Statement Intelligence (BSI) with transaction analysis
- Auto-tagging and taxonomy

### Sharing & Permissions
9 permission levels: Owner, Co-Owner, Editor, Commenter, Viewer (Download), Viewer (No Download), Link-Only, Restricted (Masked), No Access

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Ant Design, TailwindCSS, Zustand |
| Backend | Python FastAPI, SQLAlchemy 2.0, SQLite |
| Background Jobs | Celery + Redis |
| Authentication | JWT + MFA |

## Quick Start

```bash
# Start all services
docker-compose up -d --build

# Seed the database
docker-compose exec backend python -m app.scripts.seed_realistic

# Access the application
# Frontend: http://localhost:7000
# Backend API: http://localhost:7001/api/v1
# API Docs: http://localhost:7001/api/v1/docs
```

## Default Users

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@alphha.local | admin123 |
| Manager | manager@alphha.local | password123 |
| Legal | legal@alphha.local | password123 |
| Compliance | compliance@alphha.local | password123 |
| User | user@alphha.local | password123 |
| Viewer | viewer@alphha.local | password123 |

## Role Permissions

| Role | Access |
|------|--------|
| Admin | Full system access |
| Manager | Documents, Entities, Analytics, Approvals |
| Legal | Documents (read), Legal Hold, Audit, Compliance |
| Compliance | Documents (read), Audit, PII, Compliance |
| User | Documents (create, read, update) |
| Viewer | Documents (read only) |

## API Endpoints

### Documents
- `GET /api/v1/documents` - List documents
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents/{id}` - Get document
- `GET /api/v1/documents/{id}/versions` - Version history
- `POST /api/v1/documents/{id}/versions/{v1}/diff/{v2}` - Compare versions
- `POST /api/v1/documents/{id}/checkout` - Lock document
- `POST /api/v1/documents/{id}/checkin` - Release lock

### Entities
- `GET /api/v1/entities/customers` - List customers
- `GET /api/v1/entities/vendors` - List vendors
- `GET /api/v1/documents/departments` - List departments

### Config
- `GET /api/v1/config/options` - List config options
- `POST /api/v1/config/options` - Create option
- `POST /api/v1/config/options/seed-defaults` - Seed defaults

### Sharing
- `GET /api/v1/documents/{id}/shares` - List shares
- `POST /api/v1/documents/{id}/share` - Share document

## Project Structure

```
/backend/
├── app/
│   ├── api/v1/endpoints/    # API routes
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── scripts/             # Seed scripts
/frontend/
├── src/
│   ├── components/          # Reusable components
│   ├── pages/               # Page components
│   ├── layouts/             # Layout components
│   └── services/            # API services
```

## License

Proprietary - All rights reserved
