from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import tomllib

from .models import BackendConfig

DEFAULT_BASE_URL = "http://localhost:28173"


def xdg_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "czm" / "config.toml"


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be an http or https URL")
    return value.rstrip("/")


def load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"config file {path} must contain a TOML table")
    return data


def _pick_value(env: Mapping[str, str], flag_value: str | None, env_name: str, file_data: dict[str, Any], key: str) -> str | None:
    if flag_value is not None and flag_value != "":
        return flag_value
    env_value = env.get(env_name)
    if env_value is not None and env_value != "":
        return env_value
    file_value = file_data.get(key)
    if isinstance(file_value, str) and file_value != "":
        return file_value
    return None


def resolve_backend_config(
    *,
    env: Mapping[str, str] | None = None,
    config_path: Path | None = None,
) -> BackendConfig:
    env = dict(env or os.environ)
    path = Path(env["CZM_CONFIG_PATH"]) if env.get("CZM_CONFIG_PATH") else (config_path or xdg_config_path())
    file_data = load_config_file(path)

    base_url = _pick_value(env, None, "CZM_BASE_URL", file_data, "base_url") or DEFAULT_BASE_URL
    api_key = _pick_value(env, None, "CZM_API_KEY", file_data, "api_key")
    timezone = _pick_value(env, None, "CZM_TIMEZONE", file_data, "timezone") or "UTC"

    if not api_key:
        raise ValueError(
            "missing required backend configuration: api_key. Set CZM_API_KEY or provide a czm config file at "
            f"{path}"
        )

    return BackendConfig(
        base_url=normalize_base_url(base_url),
        api_key=api_key,
        timezone=timezone,
        config_path=path,
    )

