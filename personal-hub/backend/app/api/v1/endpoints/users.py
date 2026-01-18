"""User management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps.auth import ActiveUser, AdminUser
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
) -> UserListResponse:
    """
    List all users with pagination.

    **Admin only.**
    """
    user_service = UserService(db)
    users, total = await user_service.get_all(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
    )

    total_pages = (total + page_size - 1) // page_size

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Create a new user.

    **Admin only.**
    """
    user_service = UserService(db)
    audit_service = AuditService(db)

    try:
        user = await user_service.create(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Audit log
    await audit_service.log_user_create(
        admin_id=current_user.id,
        created_user_id=user.id,
        created_email=user.email,
        ip_address=get_client_ip(request),
    )

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get user by ID.

    Users can only view their own profile unless they are admin.
    """
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user",
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Update user.

    Users can update their own profile (name, avatar).
    Only admins can update roles and is_active status.
    """
    user_service = UserService(db)
    audit_service = AuditService(db)

    user = await user_service.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check permissions
    is_self = user_id == current_user.id
    is_admin = current_user.is_admin

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    # Non-admins can't change roles or is_active
    if not is_admin:
        if user_data.roles is not None or user_data.is_active is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can change roles or active status",
            )

    # Track role changes for audit
    old_roles = user.role_names.copy()

    updated_user = await user_service.update(user, user_data)

    # Audit role changes
    if user_data.roles is not None and set(old_roles) != set(updated_user.role_names):
        await audit_service.log_role_change(
            admin_id=current_user.id,
            target_user_id=user.id,
            old_roles=old_roles,
            new_roles=updated_user.role_names,
            ip_address=get_client_ip(request),
        )

    return UserResponse.model_validate(updated_user)


@router.post("/{user_id}/password")
async def update_password(
    user_id: int,
    password_data: UserPasswordUpdate,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """
    Update user password.

    Users can only change their own password.
    """
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only change your own password",
        )

    user_service = UserService(db)

    success = await user_service.update_password(
        user=current_user,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    return {"message": "Password updated successfully"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a user.

    **Admin only.** Cannot delete yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await user_service.delete(user)


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: int,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Activate a user.

    **Admin only.**
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = await user_service.activate(user)
    return UserResponse.model_validate(updated_user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Deactivate a user.

    **Admin only.** Cannot deactivate yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = await user_service.deactivate(user)
    return UserResponse.model_validate(updated_user)
