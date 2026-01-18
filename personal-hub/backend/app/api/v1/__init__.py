"""API v1 module."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, health, modules, profile, users

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(modules.router, prefix="/modules", tags=["Modules"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
