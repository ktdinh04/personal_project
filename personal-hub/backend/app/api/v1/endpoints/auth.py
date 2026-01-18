"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps.auth import ActiveUser
from app.db.models.audit_log import AuditAction
from app.schemas.auth import LoginRequest, LoginResponse, RefreshTokenRequest, TokenResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter()


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """
    Authenticate user and return access/refresh tokens.

    - **email**: User email address
    - **password**: User password
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = await auth_service.authenticate(
        email=login_data.email,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if result is None:
        # Log failed login attempt
        await audit_service.log(
            action=AuditAction.LOGIN_FAILED,
            description=f"Failed login attempt for {login_data.email}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log successful login
    await audit_service.log_login(
        user_id=result.user.id,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = await auth_service.refresh_tokens(
        refresh_token=token_data.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return result


@router.post("/logout")
async def logout(
    request: Request,
    current_user: ActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: str | None = None,
) -> dict[str, str]:
    """
    Logout user and revoke refresh tokens.

    - If **refresh_token** provided, revokes only that token
    - Otherwise, revokes all user's refresh tokens
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    await auth_service.logout(user_id=current_user.id, refresh_token=refresh_token)

    # Log logout
    await audit_service.log(
        action=AuditAction.LOGOUT,
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(current_user: ActiveUser) -> dict:
    """Get current authenticated user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "roles": current_user.role_names,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }
