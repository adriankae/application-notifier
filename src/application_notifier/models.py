from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


Slot = Literal["morning", "evening"]


@dataclass(slots=True, frozen=True)
class BackendConfig:
    base_url: str
    api_key: str
    timezone: str
    config_path: Path | None = None


@dataclass(slots=True, frozen=True)
class OpenClawBridgeConfig:
    mode: str
    command: str | None
    fallback_command: str | None
    target: str | None
    timeout_seconds: int


@dataclass(slots=True, frozen=True)
class Subject:
    id: int
    display_name: str


@dataclass(slots=True, frozen=True)
class Location:
    id: int
    code: str
    display_name: str


@dataclass(slots=True, frozen=True)
class DueItem:
    episode_id: int
    subject_id: int
    location_id: int
    current_phase_number: int
    treatment_due_today: bool
    next_due_at: str | None = None
    last_application_at: str | None = None


@dataclass(slots=True, frozen=True)
class ReminderItem:
    location_name: str
    phase_number: int


@dataclass(slots=True, frozen=True)
class ReminderSubjectGroup:
    subject_name: str
    items: list[ReminderItem] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ReminderPayload:
    slot: Slot
    timezone: str
    subjects: list[ReminderSubjectGroup]


@dataclass(slots=True, frozen=True)
class BridgeInvocation:
    command: list[str]
    payload_file: Path
    instructions_file: Path
    fallback_file: Path
    plain_text_mode: bool = False
