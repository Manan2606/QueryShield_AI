import pytest

from app.core import config


def test_production_settings_reject_placeholder_jwt_secret(monkeypatch):
    monkeypatch.setattr(config.settings, "APP_ENV", "production")
    monkeypatch.setattr(config.settings, "JWT_SECRET_KEY", "change_me")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        config.validate_production_settings()


def test_production_settings_require_gemini_key_when_summaries_enabled(monkeypatch):
    monkeypatch.setattr(config.settings, "APP_ENV", "production")
    monkeypatch.setattr(config.settings, "JWT_SECRET_KEY", "x" * 40)
    monkeypatch.setattr(config.settings, "AI_SUMMARY_ENABLED", True)
    monkeypatch.setattr(config.settings, "GEMINI_API_KEY", "")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        config.validate_production_settings()


def test_production_settings_accept_required_values(monkeypatch):
    monkeypatch.setattr(config.settings, "APP_ENV", "production")
    monkeypatch.setattr(config.settings, "JWT_SECRET_KEY", "x" * 40)
    monkeypatch.setattr(config.settings, "AI_SUMMARY_ENABLED", False)
    monkeypatch.setattr(config.settings, "STORAGE_BACKEND", "gcs")
    monkeypatch.setattr(config.settings, "GCS_UPLOAD_BUCKET", "queryshield-test")

    config.validate_production_settings()
