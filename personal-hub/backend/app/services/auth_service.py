"""Authentication service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.schemas.auth import LoginResponse, TokenResponse, UserInfo
from app.services.user_service import UserService


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)

    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResponse | None:
        """Authenticate user and return tokens."""
        user = await self.user_service.get_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login = datetime.now(timezone.utc)

        # Create tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "roles": user.role_names,
            },
        )
        refresh_token = create_refresh_token(subject=user.id)

        # Store refresh token in database
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.refresh_token_expire_seconds
        )
        refresh_token_db = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(refresh_token_db)

        await self.db.flush()

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_seconds,
            user=UserInfo(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                roles=user.role_names,
                is_admin=user.is_admin,
            ),
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse | None:
        """Refresh access token using refresh token."""
        # Verify refresh token JWT
        payload = verify_token_type(refresh_token, "refresh")
        if payload is None:
            return None

        # Check if token exists in database and is valid
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == refresh_token, RefreshToken.is_revoked == False
            )
        )
        token_db = result.scalar_one_or_none()

        if token_db is None or not token_db.is_valid:
            return None

        # Get user
        user = await self.user_service.get_by_id(token_db.user_id)
        if user is None or not user.is_active:
            return None

        # Revoke old refresh token
        token_db.is_revoked = True

        # Create new tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "roles": user.role_names,
            },
        )
        new_refresh_token = create_refresh_token(subject=user.id)

        # Store new refresh token
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.refresh_token_expire_seconds
        )
        new_token_db = RefreshToken(
            token=new_refresh_token,
            user_id=user.id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(new_token_db)

        await self.db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_seconds,
        )

    async def logout(self, user_id: int, refresh_token: str | None = None) -> None:
        """Logout user by revoking refresh tokens."""
        if refresh_token:
            # Revoke specific token
            result = await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.token == refresh_token, RefreshToken.user_id == user_id
                )
            )
            token_db = result.scalar_one_or_none()
            if token_db:
                token_db.is_revoked = True
        else:
            # Revoke all user's refresh tokens
            await self.db.execute(
                delete(RefreshToken).where(RefreshToken.user_id == user_id)
            )

        await self.db.flush()

    async def revoke_all_tokens(self, user_id: int) -> None:
        """Revoke all refresh tokens for a user."""
        await self.db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await self.db.flush()

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired refresh tokens from database."""
        result = await self.db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(timezone.utc))
        )
        await self.db.flush()
        return result.rowcount

    async def seed_admin(self) -> User | None:
        """Create initial admin user if not exists."""
        existing = await self.user_service.get_by_email(settings.init_admin_email)
        if existing:
            return None

        # Create admin role if not exists
        admin_role = await self.user_service.get_or_create_role(
            name="admin", description="Administrator with full access"
        )
        user_role = await self.user_service.get_or_create_role(
            name="user", description="Regular user"
        )

        # Create admin user
        admin = User(
            email=settings.init_admin_email,
            name=settings.init_admin_name,
            hashed_password=get_password_hash(settings.init_admin_password),
            is_active=True,
            is_verified=True,
        )
        admin.roles = [admin_role, user_role]

        self.db.add(admin)
        await self.db.flush()

        return admin
