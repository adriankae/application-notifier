from application_notifier.models import DueItem, Location, Subject
from application_notifier.payload_builder import build_reminder_payload


def test_payload_builder_groups_and_sorts():
    items = [
        DueItem(episode_id=2, subject_id=2, location_id=20, current_phase_number=3, treatment_due_today=True),
        DueItem(episode_id=1, subject_id=1, location_id=10, current_phase_number=1, treatment_due_today=True),
        DueItem(episode_id=3, subject_id=1, location_id=30, current_phase_number=2, treatment_due_today=True),
    ]
    subjects = [
        Subject(id=2, display_name="Zoe"),
        Subject(id=1, display_name="Adrian"),
    ]
    locations = [
        Location(id=20, code="right_elbow", display_name="Right elbow"),
        Location(id=10, code="left_elbow", display_name="Left elbow"),
        Location(id=30, code="neck", display_name="Neck"),
    ]
    payload = build_reminder_payload("evening", "Europe/Berlin", items, subjects, locations)
    assert payload.slot == "evening"
    assert payload.timezone == "Europe/Berlin"
    assert [subject.subject_name for subject in payload.subjects] == ["Adrian", "Zoe"]
    assert [item.location_name for item in payload.subjects[0].items] == ["Left elbow", "Neck"]
    assert [item.phase_number for item in payload.subjects[0].items] == [1, 2]

