from pathlib import Path

from app.config import Settings


def test_resolved_url_defaults_to_database_url(tmp_path, monkeypatch):
    monkeypatch.delenv("FA_DB_PATH", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.resolved_database_url() == "sqlite:///./financial.db"


def test_resolved_url_uses_fa_db_path_when_set(tmp_path, monkeypatch):
    target = tmp_path / "data" / "fa.db"
    monkeypatch.setenv("FA_DB_PATH", str(target))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings(_env_file=None)
    url = s.resolved_database_url()
    assert url == f"sqlite:///{Path(target).as_posix()}"
    # parent directory created on resolve
    assert target.parent.is_dir()


def test_resolved_url_fa_db_path_overrides_database_url(tmp_path, monkeypatch):
    target = tmp_path / "fa.db"
    monkeypatch.setenv("FA_DB_PATH", str(target))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./should-not-be-used.db")
    s = Settings(_env_file=None)
    assert s.resolved_database_url() == f"sqlite:///{Path(target).as_posix()}"
