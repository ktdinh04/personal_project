"""Module management endpoints."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps.auth import ActiveUser, AdminUser
from app.db.models.module import ModuleStatus
from app.services.audit_service import AuditService
from app.services.module_service import ModuleService

router = APIRouter()


class ModuleResponse(BaseModel):
    """Module response for API."""

    id: int
    module_id: str
    name: str
    description: str | None
    version: str
    tags: list[str]
    icon: str | None
    nav_order: int
    ui_path: str | None
    api_base_path: str | None
    health_path: str | None
    permissions_required: list[str]
    services: dict[str, str]
    is_enabled: bool
    status: str
    health_message: str | None
    last_health_check: str | None


class ModuleListResponse(BaseModel):
    """Module list response."""

    items: list[ModuleResponse]
    total: int


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _serialize_module(module) -> ModuleResponse:
    """Serialize module to response format."""
    return ModuleResponse(
        id=module.id,
        module_id=module.module_id,
        name=module.name,
        description=module.description,
        version=module.version,
        tags=json.loads(module.tags) if module.tags else [],
        icon=module.icon,
        nav_order=module.nav_order,
        ui_path=module.ui_path,
        api_base_path=module.api_base_path,
        health_path=module.health_path,
        permissions_required=json.loads(module.permissions_required)
        if module.permissions_required
        else [],
        services=json.loads(module.services) if module.services else {},
        is_enabled=module.is_enabled,
        status=module.status,
        health_message=module.health_message,
        last_health_check=module.last_health_check.isoformat()
        if module.last_health_check
        else None,
    )


@router.get("", response_model=ModuleListResponse)
async def list_modules(
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_disabled: bool = Query(False),
) -> ModuleListResponse:
    """
    List all available modules.

    - **include_disabled**: Include disabled modules in the list
    """
    module_service = ModuleService(db)

    # Non-admins can only see enabled modules
    if not current_user.is_admin:
        include_disabled = False

    modules = await module_service.get_all(include_disabled=include_disabled)

    # Filter by user permissions
    filtered_modules = []
    for module in modules:
        permissions = json.loads(module.permissions_required) if module.permissions_required else []

        # Admin can see all, others need to have required permissions
        if current_user.is_admin or not permissions:
            filtered_modules.append(module)
        else:
            # Check if user has any required permission
            user_roles = set(current_user.role_names)
            if user_roles.intersection(set(permissions)):
                filtered_modules.append(module)

    return ModuleListResponse(
        items=[_serialize_module(m) for m in filtered_modules],
        total=len(filtered_modules),
    )


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(
    module_id: str,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModuleResponse:
    """Get module by ID."""
    module_service = ModuleService(db)
    module = await module_service.get_by_module_id(module_id)

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    # Check permissions
    if not current_user.is_admin:
        permissions = (
            json.loads(module.permissions_required) if module.permissions_required else []
        )
        if permissions:
            user_roles = set(current_user.role_names)
            if not user_roles.intersection(set(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this module",
                )

    return _serialize_module(module)


@router.post("/{module_id}/enable", response_model=ModuleResponse)
async def enable_module(
    request: Request,
    module_id: str,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModuleResponse:
    """
    Enable a module.

    **Admin only.**
    """
    module_service = ModuleService(db)
    audit_service = AuditService(db)

    module = await module_service.get_by_module_id(module_id)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    updated = await module_service.enable(module)

    # Audit log
    await audit_service.log_module_change(
        user_id=current_user.id,
        module_id=module_id,
        action_type="enable",
        ip_address=get_client_ip(request),
    )

    return _serialize_module(updated)


@router.post("/{module_id}/disable", response_model=ModuleResponse)
async def disable_module(
    request: Request,
    module_id: str,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModuleResponse:
    """
    Disable a module.

    **Admin only.**
    """
    module_service = ModuleService(db)
    audit_service = AuditService(db)

    module = await module_service.get_by_module_id(module_id)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    updated = await module_service.disable(module)

    # Audit log
    await audit_service.log_module_change(
        user_id=current_user.id,
        module_id=module_id,
        action_type="disable",
        ip_address=get_client_ip(request),
    )

    return _serialize_module(updated)


@router.get("/{module_id}/config")
async def get_module_config(
    module_id: str,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Get module configuration.

    **Admin only.**
    """
    module_service = ModuleService(db)
    module = await module_service.get_by_module_id(module_id)

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    return await module_service.get_config(module)


class ModuleConfigUpdate(BaseModel):
    """Module config update request."""

    configs: dict[str, str]


@router.put("/{module_id}/config")
async def update_module_config(
    request: Request,
    module_id: str,
    config_data: ModuleConfigUpdate,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Update module configuration.

    **Admin only.**
    """
    module_service = ModuleService(db)
    audit_service = AuditService(db)

    module = await module_service.get_by_module_id(module_id)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    # Update each config key
    for key, value in config_data.configs.items():
        await module_service.set_config(module, key, value)

    # Audit log
    await audit_service.log_module_change(
        user_id=current_user.id,
        module_id=module_id,
        action_type="config",
        details={"updated_keys": list(config_data.configs.keys())},
        ip_address=get_client_ip(request),
    )

    return await module_service.get_config(module)


@router.post("/{module_id}/health")
async def check_module_health(
    module_id: str,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Check module health status."""
    module_service = ModuleService(db)
    module = await module_service.get_by_module_id(module_id)

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    status_result, message = await module_service.check_health(module)
    await module_service.update_status(module, status_result, message)

    return {
        "module_id": module_id,
        "status": status_result.value,
        "message": message,
    }


@router.post("/reload", response_model=ModuleListResponse)
async def reload_modules(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModuleListResponse:
    """
    Reload modules from disk.

    **Admin only.** Scans the modules directory and updates the registry.
    """
    module_service = ModuleService(db)
    modules = await module_service.load_modules_from_disk()

    return ModuleListResponse(
        items=[_serialize_module(m) for m in modules],
        total=len(modules),
    )


@router.post("/health-check-all")
async def check_all_modules_health(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, dict[str, Any]]:
    """
    Check health of all enabled modules.

    **Admin only.**
    """
    module_service = ModuleService(db)
    results = await module_service.check_all_health()

    return {
        module_id: {"status": status.value, "message": message}
        for module_id, (status, message) in results.items()
    }
