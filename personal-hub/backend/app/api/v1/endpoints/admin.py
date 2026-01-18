"""Admin endpoints for system management."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps.auth import AdminUser
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log response."""

    id: int
    action: str
    user_id: int | None
    user_email: str | None
    resource_type: str | None
    resource_id: str | None
    description: str | None
    details: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: str


class AuditLogListResponse(BaseModel):
    """Audit log list response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RoleResponse(BaseModel):
    """Role response."""

    id: int
    name: str
    description: str | None
    created_at: str


class StatsResponse(BaseModel):
    """Admin dashboard stats."""

    total_users: int
    active_users: int
    total_modules: int
    enabled_modules: int
    recent_logins: int


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> AuditLogListResponse:
    """
    List audit logs with filtering.

    **Admin only.**
    """
    audit_service = AuditService(db)
    logs, total = await audit_service.get_logs(
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )

    total_pages = (total + page_size - 1) // page_size

    items = [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            user_id=log.user_id,
            user_email=log.user.email if log.user else None,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            description=log.description,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoleResponse]:
    """
    List all roles.

    **Admin only.**
    """
    user_service = UserService(db)
    roles = await user_service.get_all_roles()

    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            created_at=role.created_at.isoformat(),
        )
        for role in roles
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_admin_stats(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatsResponse:
    """
    Get admin dashboard statistics.

    **Admin only.**
    """
    from datetime import timedelta, timezone

    from sqlalchemy import func, select

    from app.db.models.audit_log import AuditAction, AuditLog
    from app.db.models.module import Module
    from app.db.models.user import User

    # User stats
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar() or 0

    # Module stats
    total_modules_result = await db.execute(select(func.count(Module.id)))
    total_modules = total_modules_result.scalar() or 0

    enabled_modules_result = await db.execute(
        select(func.count(Module.id)).where(Module.is_enabled == True)
    )
    enabled_modules = enabled_modules_result.scalar() or 0

    # Recent logins (last 24 hours)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    recent_logins_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == AuditAction.LOGIN.value, AuditLog.created_at >= yesterday
        )
    )
    recent_logins = recent_logins_result.scalar() or 0

    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_modules=total_modules,
        enabled_modules=enabled_modules,
        recent_logins=recent_logins,
    )
