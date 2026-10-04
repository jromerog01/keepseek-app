from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_token: str = ""
    secret_key: str = ""
    data_dir: Path = Path("/data")
    static_dir: Path = Path("/app/static")
    max_concurrent: int = 2
    file_ttl_hours: int = 6
    history_days: int = 30
    secure_cookies: bool = True
    allow_private_urls: bool = False

    @property
    def downloads_dir(self) -> Path:
        return self.data_dir / "downloads"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "clipo.db"

    @property
    def cookies_path(self) -> Path | None:
        path = self.data_dir / "cookies.txt"
        return path if path.is_file() else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
