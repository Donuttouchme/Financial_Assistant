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

    def resolved_db_path(self) -> str:
        """Return the on-disk path of the live SQLite database.

        Strips the ``sqlite:///`` prefix from ``resolved_database_url`` so the
        backup service (and any other file-IO consumer) can read/write the DB
        file directly without re-parsing the SQLAlchemy URL.
        """
        url = self.resolved_database_url()
        prefix = "sqlite:///"
        if url.startswith(prefix):
            return url[len(prefix):]
        # Non-sqlite URLs have no on-disk file; the backup service should not
        # be invoked in that case, but return the raw URL for clearer errors.
        return url


settings = Settings()
