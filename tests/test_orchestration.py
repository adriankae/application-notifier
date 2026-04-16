from __future__ import annotations

from pathlib import Path

from application_notifier.config import AppConfig
from application_notifier.models import BackendConfig, OpenClawBridgeConfig
from application_notifier.orchestration import run_with_config


class _FakeBackendClient:
    def __init__(self, config):
        self.config = config

    def list_due_items(self):
        from application_notifier.models import DueItem

        return [DueItem(episode_id=1, subject_id=1, location_id=1, current_phase_number=1, treatment_due_today=True)]

    def list_subjects(self):
        from application_notifier.models import Subject

        return [Subject(id=1, display_name="Adrian")]

    def list_locations(self):
        from application_notifier.models import Location

        return [Location(id=1, code="left_elbow", display_name="Left elbow")]


def test_run_uses_structured_bridge_before_fallback(monkeypatch):
    calls: list[bool] = []

    def fake_backend_client(config):
        return _FakeBackendClient(config)

    def fake_invoke_bridge(bridge, payload, fallback_text, *, env=None, plain_text_mode=False, timeout_seconds=None):
        calls.append(plain_text_mode)
        if not plain_text_mode:
            from application_notifier.openclaw_bridge import BridgeResult

            return BridgeResult(
                command=["structured"],
                returncode=0,
                stdout="structured",
                stderr="",
                plain_text_mode=False,
                instructions="structured instructions",
            )
        from application_notifier.openclaw_bridge import BridgeResult

        return BridgeResult(
            command=["fallback"],
            returncode=0,
            stdout="fallback",
            stderr="",
            plain_text_mode=True,
            instructions="fallback instructions",
        )

    monkeypatch.setattr("application_notifier.orchestration.BackendClient", fake_backend_client)
    monkeypatch.setattr("application_notifier.orchestration.invoke_bridge", fake_invoke_bridge)

    config = AppConfig(
        backend=BackendConfig(base_url="http://example", api_key="secret", timezone="Europe/Berlin"),
        bridge=OpenClawBridgeConfig(
            mode="command",
            command="structured-command",
            fallback_command="fallback-command",
            target="6740655890",
            timeout_seconds=5,
        ),
        lock_path=Path("/tmp/application-notifier-test.lock"),
    )

    result = run_with_config(config, "morning")

    assert calls == [False]
    assert result.sent is True
    assert result.bridge_instructions == "structured instructions"


def test_run_falls_back_only_after_structured_bridge_failure(monkeypatch):
    calls: list[bool] = []

    def fake_backend_client(config):
        return _FakeBackendClient(config)

    def fake_invoke_bridge(bridge, payload, fallback_text, *, env=None, plain_text_mode=False, timeout_seconds=None):
        calls.append(plain_text_mode)
        from application_notifier.openclaw_bridge import BridgeResult

        if not plain_text_mode:
            raise RuntimeError("structured path failed")
        return BridgeResult(
            command=["fallback"],
            returncode=0,
            stdout="fallback",
            stderr="",
            plain_text_mode=True,
            instructions="fallback instructions",
        )

    monkeypatch.setattr("application_notifier.orchestration.BackendClient", fake_backend_client)
    monkeypatch.setattr("application_notifier.orchestration.invoke_bridge", fake_invoke_bridge)

    config = AppConfig(
        backend=BackendConfig(base_url="http://example", api_key="secret", timezone="Europe/Berlin"),
        bridge=OpenClawBridgeConfig(
            mode="command",
            command="structured-command",
            fallback_command="fallback-command",
            target="6740655890",
            timeout_seconds=5,
        ),
        lock_path=Path("/tmp/application-notifier-test-fallback.lock"),
    )

    result = run_with_config(config, "morning")

    assert calls == [False, True]
    assert result.sent is True
    assert result.bridge_instructions == "fallback instructions"
