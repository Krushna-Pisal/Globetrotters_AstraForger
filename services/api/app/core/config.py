"""Runtime settings. Values come from the environment (see .env.example); defaults match docker-compose."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# services/api/app/core/config.py -> repo root is four levels up
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql+psycopg://ps4:ps4@db:5432/ps4"
    test_database_url: str = "postgresql+psycopg://ps4:ps4@db:5432/ps4_test"
    jwt_secret: str = "change-me-demo-only"
    jwt_ttl_minutes: int = 720
    demo_login_enabled: bool = False  # passwordless POST /v1/auth/demo-login (off for the prototype)
    warm_caches: bool = True  # pre-build the default views at API start-up
    configs_dir: Path = REPO_ROOT / "configs"
    data_dir: Path = REPO_ROOT / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
