from pathlib import Path

from application_notifier.czm_config import resolve_backend_config


def test_config_resolution_prefers_env_over_file(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text(
        'base_url = "http://file.example"\napi_key = "file-key"\ntimezone = "Europe/Paris"\n',
        encoding="utf-8",
    )
    resolved = resolve_backend_config(
        env={
            "CZM_BASE_URL": "http://env.example",
            "CZM_API_KEY": "env-key",
            "CZM_TIMEZONE": "Asia/Tokyo",
            "CZM_CONFIG_PATH": str(config),
        }
    )
    assert resolved.base_url == "http://env.example"
    assert resolved.api_key == "env-key"
    assert resolved.timezone == "Asia/Tokyo"


def test_config_resolution_uses_file_when_env_missing(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text(
        'base_url = "http://file.example"\napi_key = "file-key"\n',
        encoding="utf-8",
    )
    resolved = resolve_backend_config(env={"CZM_CONFIG_PATH": str(config)})
    assert resolved.base_url == "http://file.example"
    assert resolved.api_key == "file-key"
    assert resolved.timezone == "UTC"


def test_config_resolution_defaults_base_url(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text('api_key = "file-key"\n', encoding="utf-8")
    resolved = resolve_backend_config(env={"CZM_CONFIG_PATH": str(config)})
    assert resolved.base_url == "http://localhost:28173"
    assert resolved.api_key == "file-key"

