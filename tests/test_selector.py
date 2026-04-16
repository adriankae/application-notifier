from application_notifier.models import DueItem
from application_notifier.selector import select_due_items


def test_morning_selects_all_due_items():
    items = [
        DueItem(episode_id=1, subject_id=1, location_id=1, current_phase_number=1, treatment_due_today=True),
        DueItem(episode_id=2, subject_id=1, location_id=2, current_phase_number=3, treatment_due_today=True),
    ]
    selected = select_due_items("morning", items)
    assert selected == items


def test_evening_selects_phase_one_only():
    items = [
        DueItem(episode_id=1, subject_id=1, location_id=1, current_phase_number=1, treatment_due_today=True),
        DueItem(episode_id=2, subject_id=1, location_id=2, current_phase_number=3, treatment_due_today=True),
        DueItem(episode_id=3, subject_id=2, location_id=2, current_phase_number=1, treatment_due_today=True),
    ]
    selected = select_due_items("evening", items)
    assert [item.episode_id for item in selected] == [1, 3]

