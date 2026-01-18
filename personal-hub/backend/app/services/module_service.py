"""Module service for managing plugins/projects."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.module import Module, ModuleConfig, ModuleStatus


class ModuleService:
    """Service for module management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, include_disabled: bool = False) -> list[Module]:
        """Get all modules."""
        query = select(Module).order_by(Module.nav_order, Module.name)

        if not include_disabled:
            query = query.where(Module.is_enabled == True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, module_db_id: int) -> Module | None:
        """Get module by database ID."""
        result = await self.db.execute(select(Module).where(Module.id == module_db_id))
        return result.scalar_one_or_none()

    async def get_by_module_id(self, module_id: str) -> Module | None:
        """Get module by module_id string."""
        result = await self.db.execute(select(Module).where(Module.module_id == module_id))
        return result.scalar_one_or_none()

    async def enable(self, module: Module) -> Module:
        """Enable a module."""
        module.is_enabled = True
        await self.db.flush()
        return module

    async def disable(self, module: Module) -> Module:
        """Disable a module."""
        module.is_enabled = False
        await self.db.flush()
        return module

    async def update_status(
        self,
        module: Module,
        status: ModuleStatus,
        message: str | None = None,
    ) -> Module:
        """Update module status."""
        module.status = status.value
        module.health_message = message
        module.last_health_check = datetime.now(timezone.utc)
        await self.db.flush()
        return module

    async def check_health(self, module: Module) -> tuple[ModuleStatus, str | None]:
        """Check module health via HTTP."""
        if not module.health_path or not module.api_base_path:
            return ModuleStatus.UNKNOWN, "No health endpoint configured"

        # Determine the service host based on module configuration
        services = json.loads(module.services) if module.services else {}
        service_name = services.get("main", module.module_id)

        # Try to construct health URL
        # Assuming services run on predictable ports/hosts
        health_url = f"http://{service_name}:8001{module.health_path}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)

                if response.status_code == 200:
                    return ModuleStatus.HEALTHY, "OK"
                else:
                    return ModuleStatus.UNHEALTHY, f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            return ModuleStatus.UNHEALTHY, "Health check timeout"
        except httpx.ConnectError:
            return ModuleStatus.STOPPED, "Service not reachable"
        except Exception as e:
            return ModuleStatus.ERROR, str(e)

    async def check_all_health(self) -> dict[str, tuple[ModuleStatus, str | None]]:
        """Check health of all enabled modules."""
        modules = await self.get_all(include_disabled=False)
        results: dict[str, tuple[ModuleStatus, str | None]] = {}

        for module in modules:
            status, message = await self.check_health(module)
            await self.update_status(module, status, message)
            results[module.module_id] = (status, message)

        return results

    async def get_config(self, module: Module) -> dict[str, Any]:
        """Get all configuration for a module."""
        result = await self.db.execute(
            select(ModuleConfig).where(ModuleConfig.module_id == module.id)
        )
        configs = result.scalars().all()

        return {
            config.key: (
                "***" if config.is_secret else config.value
            ) for config in configs
        }

    async def set_config(
        self,
        module: Module,
        key: str,
        value: str,
        value_type: str = "string",
        description: str | None = None,
        is_secret: bool = False,
    ) -> ModuleConfig:
        """Set a configuration value for a module."""
        result = await self.db.execute(
            select(ModuleConfig).where(
                ModuleConfig.module_id == module.id, ModuleConfig.key == key
            )
        )
        config = result.scalar_one_or_none()

        if config:
            config.value = value
            if description:
                config.description = description
        else:
            config = ModuleConfig(
                module_id=module.id,
                key=key,
                value=value,
                value_type=value_type,
                description=description,
                is_secret=is_secret,
            )
            self.db.add(config)

        await self.db.flush()
        return config

    async def load_modules_from_disk(self) -> list[Module]:
        """Scan modules directory and load/update module registrations."""
        modules_path = Path(settings.modules_dir)
        loaded_modules: list[Module] = []

        if not modules_path.exists():
            return loaded_modules

        for module_dir in modules_path.iterdir():
            if not module_dir.is_dir():
                continue

            # Look for manifest file
            manifest_path = module_dir / "module.json"
            if not manifest_path.exists():
                manifest_path = module_dir / "module.yaml"

            if not manifest_path.exists():
                continue

            try:
                manifest = self._load_manifest(manifest_path)
                module = await self._register_module(manifest, str(manifest_path))
                loaded_modules.append(module)
            except Exception as e:
                print(f"Error loading module from {module_dir}: {e}")

        return loaded_modules

    def _load_manifest(self, path: Path) -> dict[str, Any]:
        """Load module manifest from file."""
        with open(path, encoding="utf-8") as f:
            if path.suffix == ".yaml" or path.suffix == ".yml":
                return yaml.safe_load(f)
            else:
                return json.load(f)

    async def _register_module(
        self,
        manifest: dict[str, Any],
        manifest_path: str,
    ) -> Module:
        """Register or update a module from manifest."""
        module_id = manifest["id"]

        # Check if module already exists
        existing = await self.get_by_module_id(module_id)

        # Parse UI config
        ui_config = manifest.get("ui", {})
        api_config = manifest.get("api", {})

        # Prepare data
        tags = manifest.get("tags", [])
        permissions = manifest.get("permissions_required", [])
        services = manifest.get("services", {})

        if existing:
            # Update existing module
            existing.name = manifest["name"]
            existing.description = manifest.get("description")
            existing.version = manifest.get("version", "1.0.0")
            existing.tags = json.dumps(tags)
            existing.icon = ui_config.get("icon")
            existing.nav_order = ui_config.get("nav_order", 100)
            existing.ui_path = ui_config.get("path")
            existing.api_base_path = api_config.get("base_path")
            existing.health_path = api_config.get("health_path", "/health")
            existing.permissions_required = json.dumps(permissions)
            existing.services = json.dumps(services)
            existing.manifest_path = manifest_path

            await self.db.flush()
            return existing
        else:
            # Create new module
            module = Module(
                module_id=module_id,
                name=manifest["name"],
                description=manifest.get("description"),
                version=manifest.get("version", "1.0.0"),
                tags=json.dumps(tags),
                icon=ui_config.get("icon"),
                nav_order=ui_config.get("nav_order", 100),
                ui_path=ui_config.get("path"),
                api_base_path=api_config.get("base_path"),
                health_path=api_config.get("health_path", "/health"),
                permissions_required=json.dumps(permissions),
                services=json.dumps(services),
                manifest_path=manifest_path,
                is_enabled=True,
                status=ModuleStatus.UNKNOWN.value,
            )

            self.db.add(module)
            await self.db.flush()

            # Load default configs from schema
            config_schema = manifest.get("config_schema", {})
            for key, schema in config_schema.items():
                await self.set_config(
                    module=module,
                    key=key,
                    value=schema.get("default", ""),
                    value_type=schema.get("type", "string"),
                    description=schema.get("description"),
                    is_secret=schema.get("is_secret", False),
                )

            return module
