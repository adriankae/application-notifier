from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .models import BridgeInvocation, OpenClawBridgeConfig, ReminderPayload


@dataclass(slots=True)
class BridgeResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    plain_text_mode: bool


def _write_payload_files(payload: ReminderPayload, fallback_text: str) -> tuple[Path, Path]:
    payload_fd, payload_name = tempfile.mkstemp(prefix="application-notifier-payload-", suffix=".json")
    fallback_fd, fallback_name = tempfile.mkstemp(prefix="application-notifier-fallback-", suffix=".txt")
    os.close(payload_fd)
    os.close(fallback_fd)
    payload_file = Path(payload_name)
    fallback_file = Path(fallback_name)
    payload_file.write_text(json.dumps(payload_to_dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    fallback_file.write_text(fallback_text, encoding="utf-8")
    return payload_file, fallback_file


def payload_to_dict(payload: ReminderPayload) -> dict[str, object]:
    return {
        "slot": payload.slot,
        "timezone": payload.timezone,
        "subjects": [
            {
                "subject_name": subject.subject_name,
                "items": [
                    {"location_name": item.location_name, "phase_number": item.phase_number}
                    for item in subject.items
                ],
            }
            for subject in payload.subjects
        ],
    }


def build_invocation(
    bridge: OpenClawBridgeConfig,
    payload: ReminderPayload,
    fallback_text: str,
    *,
    plain_text_mode: bool = False,
) -> BridgeInvocation:
    command = bridge.fallback_command if plain_text_mode and bridge.fallback_command else bridge.command
    if not command:
        raise ValueError("OPENCLAW_BRIDGE_COMMAND is not configured")
    payload_file, fallback_file = _write_payload_files(payload, fallback_text)
    return BridgeInvocation(
        command=shlex.split(command),
        payload_file=payload_file,
        fallback_file=fallback_file,
        plain_text_mode=plain_text_mode,
    )


def invoke_bridge(
    bridge: OpenClawBridgeConfig,
    payload: ReminderPayload,
    fallback_text: str,
    *,
    env: Mapping[str, str] | None = None,
    plain_text_mode: bool = False,
    timeout_seconds: int | None = None,
) -> BridgeResult:
    invocation = build_invocation(bridge, payload, fallback_text, plain_text_mode=plain_text_mode)
    child_env = dict(os.environ)
    if env:
        child_env.update(env)
    child_env.update(
        {
            "APPLICATION_NOTIFIER_PAYLOAD_FILE": str(invocation.payload_file),
            "APPLICATION_NOTIFIER_FALLBACK_FILE": str(invocation.fallback_file),
            "APPLICATION_NOTIFIER_PAYLOAD_JSON": json.dumps(payload_to_dict(payload), ensure_ascii=False),
            "APPLICATION_NOTIFIER_MESSAGE_TEXT": fallback_text,
            "APPLICATION_NOTIFIER_SLOT": payload.slot,
            "APPLICATION_NOTIFIER_TIMEZONE": payload.timezone,
            "APPLICATION_NOTIFIER_BRIDGE_TARGET": bridge.target or "",
            "APPLICATION_NOTIFIER_RENDER_MODE": "plain_text" if plain_text_mode else "structured",
        }
    )

    proc = subprocess.run(
        invocation.command,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds or bridge.timeout_seconds,
        check=False,
    )
    try:
        invocation.payload_file.unlink(missing_ok=True)
        invocation.fallback_file.unlink(missing_ok=True)
    except OSError:
        pass
    if proc.returncode != 0:
        raise RuntimeError(
            "OpenClaw bridge command failed with exit code "
            f"{proc.returncode}: {' '.join(invocation.command)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return BridgeResult(
        command=invocation.command,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        plain_text_mode=plain_text_mode,
    )
