# Alphha DMS

Enterprise-grade Government Document Management System

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18+, TypeScript, Ant Design Pro, TailwindCSS, Zustand |
| Backend | Python FastAPI, SQLAlchemy 2.0, SQLite (PostgreSQL-ready) |
| Background Jobs | Celery + Redis |
| Authentication | JWT + MFA |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api/v1
# API Docs: http://localhost:8000/api/v1/docs
```

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations and seed data
python -m app.scripts.seed_data

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Default Credentials

After running the seed script:

- **Email**: admin@alphha.local
- **Password**: admin123

⚠️ **Change the admin password in production!**

## Modules Implemented

### Phase 1: Core Foundation
- ✅ M01: Authentication & Authorization (JWT, MFA, RBAC)
- ✅ M02: Document Management Core
- ✅ M03: Document Versioning
- ✅ M04: Document Lifecycle
- ✅ M12: Immutable Audit Ledger
- ✅ M18: Multi-Tenancy (partial)

### Phase 2: Compliance & Security
- ✅ M05: Approval Workflow
- ✅ M06: WORM Records
- ✅ M07: Retention & Policy Engine
- ✅ M08: Legal Hold & E-Discovery
- ✅ M09: DLP & PII Detection

### Phase 3: Search & Intelligence
- ✅ M10: Document Sharing & Permissions
- ✅ M11: Taxonomy & Auto-Tagging
- ✅ M13: Search & Semantic Retrieval
- ✅ M14: AI-Augmented Q&A Chatbot

### Phase 4: Advanced Features
- ✅ M15: Governance & Analytics Dashboard
- ✅ M16: Bank Statement Intelligence
- ✅ M17: Offline/Edge Capture (PWA)
- ✅ M19: Notifications & Alerts

## API Documentation

The API documentation is available at:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Project Structure

```
/backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── core/                   # Core configuration
│   │   ├── config.py           # Settings
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── security.py         # JWT, password hashing
│   │   └── events.py           # Startup/shutdown events
│   ├── api/v1/                 # API endpoints
│   │   ├── endpoints/          # Route handlers
│   │   └── dependencies.py     # Auth dependencies
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   ├── tasks/                  # Celery tasks
│   └── utils/                  # Utilities
├── alembic/                    # Database migrations
├── requirements.txt
└── Dockerfile

/frontend/
├── src/
│   ├── components/             # Reusable components
│   ├── pages/                  # Page components
│   ├── layouts/                # Layout components
│   ├── hooks/                  # Custom hooks
│   ├── services/               # API services
│   ├── store/                  # Zustand stores
│   ├── types/                  # TypeScript types
│   └── styles/                 # Global styles
├── package.json
├── vite.config.ts
└── Dockerfile
```

## Design Theme

- **Primary**: #1E3A5F (Navy Blue)
- **Secondary**: #2E7D32 (Government Green)
- **Accent**: #B8860B (Gold)

## License

Proprietary - All rights reserved
