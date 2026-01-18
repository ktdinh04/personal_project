"""User and Role schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=2, max_length=50)
    description: str | None = None
    permissions: list[str] | None = None


class RoleCreate(RoleBase):
    """Role creation schema."""

    pass


class RoleResponse(RoleBase):
    """Role response schema."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    avatar_url: str | None = None


class UserCreate(UserBase):
    """User creation schema - admin only."""

    password: str = Field(..., min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=lambda: ["user"])
    is_active: bool = True


class UserUpdate(BaseModel):
    """User update schema."""

    name: str | None = Field(None, min_length=2, max_length=100)
    avatar_url: str | None = None
    is_active: bool | None = None
    roles: list[str] | None = None


class UserPasswordUpdate(BaseModel):
    """Password update schema."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    """User response schema."""

    id: int
    is_active: bool
    is_verified: bool
    roles: list[RoleResponse]
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """User list response with pagination."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserSimple(BaseModel):
    """Simplified user schema for references."""

    id: int
    email: str
    name: str
    avatar_url: str | None
    is_admin: bool

    model_config = {"from_attributes": True}
