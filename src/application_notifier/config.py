from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .czm_config import resolve_backend_config
from .models import BackendConfig, OpenClawBridgeConfig


@dataclass(slots=True, frozen=True)
class AppConfig:
    backend: BackendConfig
    bridge: OpenClawBridgeConfig
    lock_path: Path


def _env_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc


def resolve_app_config(*, env: Mapping[str, str] | None = None) -> AppConfig:
    env = dict(env or os.environ)
    backend = resolve_backend_config(env=env)
    bridge = OpenClawBridgeConfig(
        mode=env.get("OPENCLAW_BRIDGE_MODE", "command") or "command",
        command=env.get("OPENCLAW_BRIDGE_COMMAND") or None,
        fallback_command=env.get("OPENCLAW_BRIDGE_FALLBACK_COMMAND") or None,
        target=env.get("OPENCLAW_BRIDGE_TARGET") or None,
        timeout_seconds=_env_int(env, "OPENCLAW_BRIDGE_TIMEOUT_SECONDS", 120),
    )
    lock_path = Path(env.get("APPLICATION_NOTIFIER_LOCK_PATH", "/tmp/application-notifier.lock"))
    return AppConfig(backend=backend, bridge=bridge, lock_path=lock_path)

