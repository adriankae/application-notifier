from __future__ import annotations

import fcntl
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .backend_client import BackendClient
from .config import AppConfig, resolve_app_config
from .fallback_renderer import render_fallback_text
from .openclaw_bridge import invoke_bridge, payload_to_dict
from .payload_builder import build_reminder_payload
from .selector import select_due_items


log = logging.getLogger("application_notifier")


@dataclass(slots=True)
class RunResult:
    sent: bool
    skipped_locked: bool
    payload: dict[str, object]
    fallback_text: str
    bridge_stdout: str = ""
    bridge_stderr: str = ""


@contextmanager
def _file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        yield None
        return
    try:
        yield handle
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def run_once(
    slot: str,
    *,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    print_only: bool = False,
    force_fallback: bool = False,
) -> RunResult:
    config = resolve_app_config(env=env)
    return run_with_config(
        config,
        slot,
        env=env,
        dry_run=dry_run,
        print_only=print_only,
        force_fallback=force_fallback,
    )


def run_with_config(
    config: AppConfig,
    slot: str,
    *,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    print_only: bool = False,
    force_fallback: bool = False,
) -> RunResult:
    with _file_lock(config.lock_path) as lock_handle:
        if lock_handle is None:
            log.info("lock is already held; skipping this reminder run")
            return RunResult(sent=False, skipped_locked=True, payload={}, fallback_text="")

        client = BackendClient(config.backend)
        due_items = client.list_due_items()
        selected = select_due_items(slot, due_items)
        subjects = client.list_subjects()
        locations = client.list_locations()
        payload = build_reminder_payload(slot, config.backend.timezone, selected, subjects, locations)
        fallback_text = render_fallback_text(payload)
        payload_dict = payload_to_dict(payload)

        if dry_run or print_only:
            log.info("dry-run payload: %s", json.dumps(payload_dict, ensure_ascii=False, indent=2))
            log.info("dry-run fallback text:\n%s", fallback_text)
            return RunResult(sent=False, skipped_locked=False, payload=payload_dict, fallback_text=fallback_text)

        try:
            bridge_result = invoke_bridge(
                config.bridge,
                payload,
                fallback_text,
                env=env,
                plain_text_mode=force_fallback,
            )
            return RunResult(
                sent=True,
                skipped_locked=False,
                payload=payload_dict,
                fallback_text=fallback_text,
                bridge_stdout=bridge_result.stdout,
                bridge_stderr=bridge_result.stderr,
            )
        except Exception as exc:
            if force_fallback or config.bridge.fallback_command:
                log.warning("primary OpenClaw bridge failed, retrying with plain-text fallback: %s", exc)
                bridge_result = invoke_bridge(
                    config.bridge,
                    payload,
                    fallback_text,
                    env=env,
                    plain_text_mode=True,
                )
                return RunResult(
                    sent=True,
                    skipped_locked=False,
                    payload=payload_dict,
                    fallback_text=fallback_text,
                    bridge_stdout=bridge_result.stdout,
                    bridge_stderr=bridge_result.stderr,
                )
            raise

