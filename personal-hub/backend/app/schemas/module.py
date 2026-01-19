"""Module schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ModuleBase(BaseModel):
    """Base module schema."""

    module_id: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    version: str = "1.0.0"
    tags: list[str] | None = None
    icon: str | None = None
    nav_order: int = 100


class ModuleCreate(ModuleBase):
    """Module creation schema."""

    ui_path: str | None = None
    api_base_path: str | None = None
    health_path: str | None = None
    permissions_required: list[str] | None = None
    services: dict[str, str] | None = None


class ModuleUpdate(BaseModel):
    """Module update schema."""

    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = None
    is_enabled: bool | None = None
    nav_order: int | None = None


class ModuleResponse(ModuleBase):
    """Module response schema."""

    id: int
    ui_path: str | None
    api_base_path: str | None
    health_path: str | None
    permissions_required: list[str] | None
    services: dict[str, str] | None
    is_enabled: bool
    status: str
    last_health_check: datetime | None
    health_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModuleListResponse(BaseModel):
    """Module list response."""

    items: list[ModuleResponse]
    total: int


class ModuleConfigBase(BaseModel):
    """Base module config schema."""

    key: str = Field(..., min_length=1, max_length=100)
    value: str | None = None
    value_type: str = "string"
    description: str | None = None
    is_secret: bool = False


class ModuleConfigCreate(ModuleConfigBase):
    """Module config creation schema."""

    pass


class ModuleConfigUpdate(BaseModel):
    """Module config update schema."""

    value: str | None = None
    description: str | None = None


class ModuleConfigResponse(ModuleConfigBase):
    """Module config response schema."""

    id: int
    module_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModuleUIConfig(BaseModel):
    """Module UI configuration."""

    path: str
    icon: str = "Puzzle"
    nav_order: int = 100


class ModuleAPIConfig(BaseModel):
    """Module API configuration."""

    base_path: str
    health_path: str = "/health"


class ModuleConfigSchema(BaseModel):
    """Module config schema definition."""

    type: str = "string"
    default: str | None = None
    required: bool = False
    description: str | None = None
    is_secret: bool = False


class ModuleManifest(BaseModel):
    """Module manifest schema (loaded from module.json)."""

    id: str
    name: str
    description: str | None = None
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)

    # UI configuration
    ui: ModuleUIConfig | None = None

    # API configuration
    api: ModuleAPIConfig | None = None

    # Permissions
    permissions_required: list[str] = Field(default_factory=list)

    # Docker services
    services: dict[str, str] = Field(default_factory=dict)

    # Configuration schema
    config_schema: dict[str, ModuleConfigSchema] = Field(default_factory=dict)
