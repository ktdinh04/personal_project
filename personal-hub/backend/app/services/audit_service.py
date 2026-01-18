"""Audit logging service."""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.audit_log import AuditAction, AuditLog


class AuditService:
    """Service for audit logging operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: AuditAction | str,
        user_id: int | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        action_str = action.value if isinstance(action, AuditAction) else action

        log_entry = AuditLog(
            action=action_str,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            description=description,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(log_entry)
        await self.db.flush()

        return log_entry

    async def get_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        user_id: int | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Get audit logs with filtering and pagination."""
        query = select(AuditLog).options(selectinload(AuditLog.user))

        # Apply filters
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)

        if action:
            query = query.where(AuditLog.action == action)

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def log_login(
        self,
        user_id: int,
        success: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Log login attempt."""
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        return await self.log(
            action=action,
            user_id=user_id if success else None,
            resource_type="user",
            resource_id=user_id,
            description=f"Login {'successful' if success else 'failed'}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_user_create(
        self,
        admin_id: int,
        created_user_id: int,
        created_email: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log user creation."""
        return await self.log(
            action=AuditAction.USER_CREATE,
            user_id=admin_id,
            resource_type="user",
            resource_id=created_user_id,
            description=f"Created user: {created_email}",
            ip_address=ip_address,
        )

    async def log_role_change(
        self,
        admin_id: int,
        target_user_id: int,
        old_roles: list[str],
        new_roles: list[str],
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log role change."""
        added = set(new_roles) - set(old_roles)
        removed = set(old_roles) - set(new_roles)

        action = AuditAction.ROLE_ASSIGN if added else AuditAction.ROLE_REVOKE

        return await self.log(
            action=action,
            user_id=admin_id,
            resource_type="user",
            resource_id=target_user_id,
            description=f"Roles changed: added={list(added)}, removed={list(removed)}",
            details={"old_roles": old_roles, "new_roles": new_roles},
            ip_address=ip_address,
        )

    async def log_module_change(
        self,
        user_id: int,
        module_id: str,
        action_type: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log module enable/disable/config change."""
        action_map = {
            "enable": AuditAction.MODULE_ENABLE,
            "disable": AuditAction.MODULE_DISABLE,
            "config": AuditAction.MODULE_CONFIG_UPDATE,
        }
        action = action_map.get(action_type, AuditAction.MODULE_CONFIG_UPDATE)

        return await self.log(
            action=action,
            user_id=user_id,
            resource_type="module",
            resource_id=module_id,
            description=f"Module {action_type}: {module_id}",
            details=details,
            ip_address=ip_address,
        )
