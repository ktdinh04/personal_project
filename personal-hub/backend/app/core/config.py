"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Personal Hub"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "mysql+asyncmy://personalhub:password@localhost:3306/personalhub"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT Authentication
    jwt_secret_key: str = "change_this_secret_key_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = 900  # 15 minutes
    refresh_token_expire_seconds: int = 604800  # 7 days

    # Initial Admin
    init_admin_email: str = "admin@personalhub.local"
    init_admin_password: str = "ChangeThisPassword123!"
    init_admin_name: str = "Administrator"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Modules
    modules_dir: str = "/app/modules"
    modules_auto_load: bool = True

    # External Services
    go2rtc_host: str = "go2rtc"
    go2rtc_api_port: int = 1984
    person_detection_host: str = "person-detection"
    person_detection_port: int = 8001

    # Config paths
    config_dir: str = "/app/config"
    profile_config_path: str = "/app/config/profile.yaml"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_profile_config() -> dict[str, Any]:
    """Load profile configuration from YAML file."""
    settings = get_settings()
    profile_path = Path(settings.profile_config_path)

    if not profile_path.exists():
        # Return default config if file doesn't exist
        return {
            "profile": {
                "displayName": "Your Name",
                "tagline": "Developer",
                "bio": "Welcome to my personal hub.",
                "avatarUrl": "/images/avatar.jpg",
            },
            "theme": {
                "accentColor": "#6366f1",
                "primaryGradient": "from-indigo-500 via-purple-500 to-pink-500",
                "darkMode": True,
            },
            "socialLinks": {},
            "skills": [],
            "featuredProjects": [],
        }

    with open(profile_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


settings = get_settings()
