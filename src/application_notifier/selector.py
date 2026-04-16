from __future__ import annotations

from .models import DueItem, Slot


def select_due_items(slot: Slot, items: list[DueItem]) -> list[DueItem]:
    if slot == "morning":
        return list(items)
    if slot == "evening":
        return [item for item in items if item.current_phase_number == 1]
    raise ValueError(f"unsupported slot: {slot}")

