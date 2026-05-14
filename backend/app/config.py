from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./financial.db"
    fa_db_path: str | None = None

    def resolved_database_url(self) -> str:
        if self.fa_db_path:
            p = Path(self.fa_db_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{p.as_posix()}"
        return self.database_url


settings = Settings()
