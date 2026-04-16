from __future__ import annotations

from collections.abc import Mapping

from .models import Location, Subject


def subject_name(subjects: Mapping[int, Subject], subject_id: int) -> str:
    subject = subjects.get(subject_id)
    if subject is not None:
        return subject.display_name
    return f"Subject {subject_id}"


def location_name(locations: Mapping[int, Location], location_id: int) -> str:
    location = locations.get(location_id)
    if location is not None:
        return location.display_name
    return f"Location {location_id}"


def subject_map(subjects: list[Subject]) -> dict[int, Subject]:
    return {subject.id: subject for subject in subjects}


def location_map(locations: list[Location]) -> dict[int, Location]:
    return {location.id: location for location in locations}

