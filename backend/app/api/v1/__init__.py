from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, documents, tenants, workflows, pii,
    compliance, search, chat, analytics, notifications, bsi, offline,
    entities, versions, sharing, license, config
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(workflows.router)  # Has its own prefix
api_router.include_router(pii.router)  # Has its own prefix
api_router.include_router(compliance.router, prefix="/compliance")
api_router.include_router(search.router)  # Has its own prefix
api_router.include_router(chat.router)  # Has its own prefix

# Phase 4 endpoints
api_router.include_router(analytics.router)  # Has its own prefix
api_router.include_router(notifications.router)  # Has its own prefix
api_router.include_router(bsi.router)  # Has its own prefix
api_router.include_router(offline.router)  # Has its own prefix

# Entity management
api_router.include_router(entities.router, prefix="/entities", tags=["Entities"])
api_router.include_router(versions.router, tags=["Versions"])
api_router.include_router(sharing.router, tags=["Sharing"])
api_router.include_router(license.router)  # Has its own prefix
api_router.include_router(config.router)  # Config options
