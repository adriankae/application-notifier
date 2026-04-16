from __future__ import annotations

from .models import ReminderPayload


def render_fallback_text(payload: ReminderPayload) -> str:
    lines: list[str] = []
    lines.append(f"Eczema reminder for {payload.slot}")
    lines.append(f"Timezone: {payload.timezone}")
    if not payload.subjects:
        lines.append("No due items right now.")
        return "\n".join(lines)

    lines.append("")
    for subject in payload.subjects:
        lines.append(subject.subject_name)
        for item in subject.items:
            lines.append(f"- {item.location_name} (phase {item.phase_number})")
        lines.append("")
    return "\n".join(lines).rstrip()

