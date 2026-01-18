"""Pydantic schemas for request/response validation."""

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenPayload,
    TokenResponse,
)
from app.schemas.module import (
    ModuleConfigCreate,
    ModuleConfigResponse,
    ModuleConfigUpdate,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
)
from app.schemas.user import (
    RoleCreate,
    RoleResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "TokenPayload",
    "TokenResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "RoleCreate",
    "RoleResponse",
    # Module
    "ModuleCreate",
    "ModuleUpdate",
    "ModuleResponse",
    "ModuleConfigCreate",
    "ModuleConfigUpdate",
    "ModuleConfigResponse",
]
