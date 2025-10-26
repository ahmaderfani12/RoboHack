"""Helpers for working with recorded joint configurations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence

from so100_robot import SO100RobotClient


def load_recorded_positions(path: Path | str) -> MutableMapping[str, Any]:
    """Return the dictionary of recorded positions stored in ``path``."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"No recorded positions found at {file_path}")
    try:
        data = json.loads(file_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {file_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {file_path}, got {type(data).__name__}")
    return data


def get_recorded_position(
    positions: Mapping[str, Any], label: str
) -> Mapping[str, Any]:
    """Fetch a recorded pose by label."""
    if label not in positions:
        raise KeyError(f"Pose '{label}' not found in recorded positions.")
    payload = positions[label]
    if not isinstance(payload, Mapping):
        raise ValueError(f"Pose '{label}' has invalid data type {type(payload).__name__}.")
    return payload


def apply_recorded_position(
    client: SO100RobotClient,
    label: str,
    positions: Mapping[str, Any],
    *,
    unit_override: Optional[str] = None,
) -> Mapping[str, Any]:
    """Command the robot to move to a recorded joint configuration."""
    payload = get_recorded_position(positions, label)
    angles = payload.get("angles")
    if not isinstance(angles, Sequence):
        raise ValueError(f"Pose '{label}' is missing an 'angles' list.")

    unit = unit_override or payload.get("unit")
    response = client.write_joints(angles, unit=unit)
    return response
