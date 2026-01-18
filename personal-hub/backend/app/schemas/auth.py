"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    """Login response with user info and tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    """Basic user info for login response."""

    id: int
    email: str
    name: str
    avatar_url: str | None
    roles: list[str]
    is_admin: bool


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Token payload schema."""

    sub: str
    exp: int
    type: str
    iat: int


# Update forward reference
LoginResponse.model_rebuild()
