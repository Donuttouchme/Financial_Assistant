import pytest

from app.services import import_preset_service


def test_create_preset(db_session):
    p = import_preset_service.create_preset(
        db_session,
        user_id=1,
        name="UBS",
        config={"delimiter": ";", "decimal_sep": ".", "amount_format": "signed"},
    )
    assert p.id is not None
    assert p.name == "UBS"
    assert p.config["delimiter"] == ";"


def test_list_presets_returns_only_users_own(db_session):
    import_preset_service.create_preset(db_session, user_id=1, name="UBS",  config={})
    import_preset_service.create_preset(db_session, user_id=1, name="Raif", config={})
    import_preset_service.create_preset(db_session, user_id=2, name="X",    config={})
    names = sorted(p.name for p in import_preset_service.list_presets(db_session, user_id=1))
    assert names == ["Raif", "UBS"]


def test_create_preset_rejects_duplicate_name_for_same_user(db_session):
    import_preset_service.create_preset(db_session, user_id=1, name="UBS", config={})
    with pytest.raises(ValueError, match="already exists"):
        import_preset_service.create_preset(db_session, user_id=1, name="UBS", config={})


def test_update_preset_changes_config(db_session):
    p = import_preset_service.create_preset(
        db_session, user_id=1, name="UBS", config={"a": 1}
    )
    updated = import_preset_service.update_preset(
        db_session, user_id=1, preset_id=p.id, name="UBS", config={"a": 2}
    )
    assert updated.config == {"a": 2}


def test_delete_preset(db_session):
    p = import_preset_service.create_preset(
        db_session, user_id=1, name="UBS", config={}
    )
    import_preset_service.delete_preset(db_session, user_id=1, preset_id=p.id)
    assert import_preset_service.list_presets(db_session, user_id=1) == []
