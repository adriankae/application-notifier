from __future__ import annotations

import json
from types import SimpleNamespace

from application_notifier.models import (
    OpenClawBridgeConfig,
    ReminderItem,
    ReminderPayload,
    ReminderSubjectGroup,
)
from application_notifier.openclaw_bridge import invoke_bridge


def _payload() -> ReminderPayload:
    return ReminderPayload(
        slot="morning",
        timezone="Europe/Berlin",
        subjects=[
            ReminderSubjectGroup(
                subject_name="Adrian",
                items=[ReminderItem(location_name="Left elbow", phase_number=1)],
            )
        ],
    )


def test_structured_bridge_passes_payload_and_instructions(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(command, env, capture_output, text, timeout, check):
        captured["command"] = command
        captured["env"] = env
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("application_notifier.openclaw_bridge.subprocess.run", fake_run)

    bridge = OpenClawBridgeConfig(
        mode="command",
        command="sh -lc 'cat'",
        fallback_command=None,
        target="6740655890",
        timeout_seconds=5,
    )

    result = invoke_bridge(bridge, _payload(), "fallback text")

    env = captured["env"]
    assert env["APPLICATION_NOTIFIER_RENDER_MODE"] == "structured"
    assert "APPLICATION_NOTIFIER_MESSAGE_TEXT" not in env
    assert json.loads(env["APPLICATION_NOTIFIER_PAYLOAD_JSON"])["slot"] == "morning"
    assert "Write a short, human-sounding reminder" in env["APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS"]
    assert "Do not use a dry heading" in env["APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS"]
    assert "Left elbow" in env["APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS"]
    assert result.instructions


def test_structured_bridge_includes_custom_style_guide(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(command, env, capture_output, text, timeout, check):
        captured["env"] = env
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("application_notifier.openclaw_bridge.subprocess.run", fake_run)

    bridge = OpenClawBridgeConfig(
        mode="command",
        command="sh -lc 'cat'",
        fallback_command=None,
        target="6740655890",
        timeout_seconds=5,
        reminder_style_guide="Sound warm, lightly playful, and avoid sounding like a checklist.",
    )

    invoke_bridge(bridge, _payload(), "fallback text")

    instructions = captured["env"]["APPLICATION_NOTIFIER_BRIDGE_INSTRUCTIONS"]
    assert "Style guide to follow:" in instructions
    assert "lightly playful" in instructions


def test_plain_text_bridge_uses_message_text_only_when_forced(monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(command, env, capture_output, text, timeout, check):
        captured["command"] = command
        captured["env"] = env
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("application_notifier.openclaw_bridge.subprocess.run", fake_run)

    bridge = OpenClawBridgeConfig(
        mode="command",
        command="sh -lc 'cat'",
        fallback_command="sh -lc 'cat'",
        target="6740655890",
        timeout_seconds=5,
    )

    invoke_bridge(bridge, _payload(), "fallback text", plain_text_mode=True)

    env = captured["env"]
    assert env["APPLICATION_NOTIFIER_RENDER_MODE"] == "plain_text"
    assert env["APPLICATION_NOTIFIER_MESSAGE_TEXT"] == "fallback text"
