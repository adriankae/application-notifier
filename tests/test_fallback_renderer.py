from application_notifier.fallback_renderer import render_fallback_text
from application_notifier.models import ReminderItem, ReminderPayload, ReminderSubjectGroup


def test_render_fallback_text_is_deterministic():
    payload = ReminderPayload(
        slot="morning",
        timezone="Europe/Berlin",
        subjects=[
            ReminderSubjectGroup(
                subject_name="Adrian",
                items=[
                    ReminderItem(location_name="Right scrotum", phase_number=1),
                    ReminderItem(location_name="Left elbow", phase_number=3),
                ],
            )
        ],
    )
    text = render_fallback_text(payload)
    assert "Eczema reminder for morning" in text
    assert "Timezone: Europe/Berlin" in text
    assert "Adrian" in text
    assert "- Right scrotum (phase 1)" in text
    assert "- Left elbow (phase 3)" in text

