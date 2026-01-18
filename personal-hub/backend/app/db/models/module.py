"""Module and ModuleConfig models."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ModuleStatus(str, Enum):
    """Module status types."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    ERROR = "error"


class Module(Base, TimestampMixin):
    """Module model representing a plugin/project."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)

    # Module metadata
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array string
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nav_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Paths
    ui_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    api_base_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    health_path: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Permissions
    permissions_required: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array string

    # Docker service mapping
    services: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object string

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ModuleStatus.UNKNOWN.value, nullable=False
    )
    last_health_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    health_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Manifest source
    manifest_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    configs: Mapped[list["ModuleConfig"]] = relationship(
        "ModuleConfig",
        back_populates="module",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Module(id={self.id}, module_id={self.module_id}, name={self.name})>"


class ModuleConfig(Base, TimestampMixin):
    """Module configuration key-value store."""

    __tablename__ = "module_configs"
    __table_args__ = (UniqueConstraint("module_id", "key", name="uix_module_config_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    module: Mapped["Module"] = relationship("Module", back_populates="configs")

    def __repr__(self) -> str:
        return f"<ModuleConfig(module_id={self.module_id}, key={self.key})>"
