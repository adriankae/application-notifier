from __future__ import annotations

from collections import defaultdict

from .models import DueItem, Location, ReminderItem, ReminderPayload, ReminderSubjectGroup, Slot, Subject
from .resolver import location_map, location_name, subject_map, subject_name


def build_reminder_payload(
    slot: Slot,
    timezone: str,
    due_items: list[DueItem],
    subjects: list[Subject],
    locations: list[Location],
) -> ReminderPayload:
    subjects_by_id = subject_map(subjects)
    locations_by_id = location_map(locations)
    grouped: dict[int, list[ReminderItem]] = defaultdict(list)

    for item in due_items:
        grouped[item.subject_id].append(
            ReminderItem(
                location_name=location_name(locations_by_id, item.location_id),
                phase_number=item.current_phase_number,
            )
        )

    groups: list[ReminderSubjectGroup] = []
    for subject_id, items in grouped.items():
        subject = subject_name(subjects_by_id, subject_id)
        sorted_items = sorted(items, key=lambda entry: (entry.location_name.casefold(), entry.phase_number))
        groups.append(ReminderSubjectGroup(subject_name=subject, items=sorted_items))

    groups.sort(key=lambda entry: entry.subject_name.casefold())
    return ReminderPayload(slot=slot, timezone=timezone, subjects=groups)

