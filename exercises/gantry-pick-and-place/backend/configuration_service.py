from typing import Optional
from fastapi.concurrency import run_in_threadpool
from database import ConfigurationRepository
from domain.models import RobotConfiguration

class ConfigurationService:
    def __init__(self, repo: ConfigurationRepository):
        self._repo = repo
        self._cached_config: Optional[RobotConfiguration] = None

    async def get(self) -> RobotConfiguration:
        config = await run_in_threadpool(self._repo.get_or_create)
        self._cached_config = config
        return config

    def get_cached(self) -> RobotConfiguration:
        if self._cached_config is None:
             raise RuntimeError("Configuration Service has not been initialized.")
        return self._cached_config

    async def update(self, config: RobotConfiguration) -> RobotConfiguration:
        saved = await run_in_threadpool(self._repo.save, config)
        self._cached_config = saved
        return saved
