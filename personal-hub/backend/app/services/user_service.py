"""User service for user management."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.db.models.user import Role, User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """Get all users with pagination and filtering."""
        query = select(User).options(selectinload(User.roles))

        # Apply filters
        if search:
            query = query.where(
                (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
            )

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(User.created_at.desc())

        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = await self.get_by_email(user_data.email)
        if existing:
            raise ValueError("Email already registered")

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create user
        user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            avatar_url=user_data.avatar_url,
            is_active=user_data.is_active,
        )

        # Assign roles
        if user_data.roles:
            roles = await self._get_roles_by_names(user_data.roles)
            user.roles = roles

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def update(self, user: User, user_data: UserUpdate) -> User:
        """Update a user."""
        update_data = user_data.model_dump(exclude_unset=True)

        # Handle roles separately
        roles = update_data.pop("roles", None)
        if roles is not None:
            user.roles = await self._get_roles_by_names(roles)

        # Update other fields
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def update_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Update user password."""
        if not verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()

        return True

    async def delete(self, user: User) -> None:
        """Delete a user."""
        await self.db.delete(user)
        await self.db.flush()

    async def activate(self, user: User) -> User:
        """Activate a user."""
        user.is_active = True
        await self.db.flush()
        return user

    async def deactivate(self, user: User) -> User:
        """Deactivate a user."""
        user.is_active = False
        await self.db.flush()
        return user

    async def _get_roles_by_names(self, role_names: list[str]) -> list[Role]:
        """Get roles by their names."""
        result = await self.db.execute(select(Role).where(Role.name.in_(role_names)))
        return list(result.scalars().all())

    async def get_or_create_role(self, name: str, description: str | None = None) -> Role:
        """Get or create a role."""
        result = await self.db.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()

        if role is None:
            role = Role(name=name, description=description)
            self.db.add(role)
            await self.db.flush()

        return role

    async def get_all_roles(self) -> list[Role]:
        """Get all roles."""
        result = await self.db.execute(select(Role).order_by(Role.name))
        return list(result.scalars().all())
