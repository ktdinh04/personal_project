"""Profile endpoints for landing page configuration."""

from typing import Any

from fastapi import APIRouter

from app.core.config import load_profile_config

router = APIRouter()


@router.get("")
async def get_profile() -> dict[str, Any]:
    """
    Get profile configuration for landing page.

    This endpoint is public and returns the profile configuration
    loaded from config/profile.yaml.
    """
    config = load_profile_config()
    return config


@router.get("/public")
async def get_public_profile() -> dict[str, Any]:
    """
    Get public profile data only.

    Returns only the public-facing parts of the profile.
    """
    config = load_profile_config()

    return {
        "profile": config.get("profile", {}),
        "theme": config.get("theme", {}),
        "socialLinks": config.get("socialLinks", {}),
        "skills": config.get("skills", []),
        "featuredProjects": config.get("featuredProjects", []),
        "seo": config.get("seo", {}),
    }
