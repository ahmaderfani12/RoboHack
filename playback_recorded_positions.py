"""Interactive playback of recorded joint configurations."""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from robot_motion_utils import load_recorded_positions
from so100_robot import SO100RobotClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay stored joint configurations.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Robot control server base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--robot-id",
        type=int,
        default=0,
        help="Robot identifier to control (default: %(default)s).",
    )
    parser.add_argument(
        "--positions",
        default="recorded_positions.json",
        help="Path to the JSON file with recorded joint configurations.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Time in seconds to interpolate between poses (default: %(default)s).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=30,
        help="Number of interpolation steps (default: %(default)s).",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.6,
        help="Lower bound on motion duration after scaling (default: %(default)s).",
    )
    parser.add_argument(
        "--reference-motion",
        type=float,
        default=1.0,
        help="Reference distance (same units as joints) that maps to the base duration.",
    )
    parser.add_argument(
        "--letter-pause",
        type=float,
        default=0.5,
        help="Pause duration (seconds) between sequential letters (default: %(default)s).",
    )
    return parser.parse_args()


def interpolate_joint_path(start, end, steps):
    start_arr = np.asarray(start, dtype=float)
    end_arr = np.asarray(end, dtype=float)
    if start_arr.shape != end_arr.shape:
        raise ValueError("Start and end joint arrays must have the same length.")
    if steps <= 0:
        return [start_arr.tolist(), end_arr.tolist()]
    weights = np.linspace(0.0, 1.0, steps + 1)
    return [((1 - w) * start_arr + w * end_arr).tolist() for w in weights]


def normalize_angles_for_playback(raw_angles, unit):
    if not isinstance(raw_angles, list):
        raise ValueError("Angle payload is not a list.")
    unit_normalized = (unit or "degrees").lower()
    if unit_normalized == "degrees":
        converted = np.deg2rad(raw_angles).tolist()
        playback_unit = "rad"
    elif unit_normalized in {"rad", "radian", "radians"}:
        converted = [float(a) for a in raw_angles]
        playback_unit = "rad"
    elif unit_normalized == "motor_units":
        converted = [float(a) for a in raw_angles]
        playback_unit = "motor_units"
    else:
        raise ValueError(f"Unsupported joint angle unit '{unit}'.")
    return converted, playback_unit


def expand_label_sequence(label: str, positions) -> list[str] | None:
    """Resolve the input label to a sequence of recorded keys."""
    if label in positions:
        return [label]
    sequence: list[str] = []
    for ch in label:
        if ch.isspace():
            continue
        candidates = (ch, ch.lower(), ch.upper())
        match = next((candidate for candidate in candidates if candidate in positions), None)
        if match is None:
            return None
        sequence.append(match)
    return sequence if sequence else None


def main() -> int:
    args = parse_args()
    client = SO100RobotClient(args.base_url, robot_id=args.robot_id)

    try:
        positions = load_recorded_positions(args.positions)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load recorded positions: {exc}", file=sys.stderr)
        return 1

    print("Initializing robot…", flush=True)
    client.initialize()

    last_state = None  # tuple of (angles list, unit string)
    print("Type a recorded label to move there (or 'end' to exit).")

    while True:
        try:
            label = input("Target label: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting playback loop.")
            break

        if not label:
            print("Empty label ignored.")
            continue
        if label.lower() == "end":
            break
        label_sequence = expand_label_sequence(label, positions)
        if not label_sequence:
            print(
                f"Label '{label}' not found. Available keys: {', '.join(sorted(positions))}",
            )
            continue

        word_aborted = False
        print(f"Label sequence resolved to: {', '.join(label_sequence)}")
        for resolved_label in label_sequence:
            payload = positions[resolved_label]
            try:
                target_angles, playback_unit = normalize_angles_for_playback(
                    payload.get("angles"), payload.get("unit")
                )
            except ValueError as exc:
                print(f"Recorded entry '{resolved_label}' is invalid: {exc}")
                continue

            if last_state and last_state[1] == playback_unit:
                current_angles = last_state[0]
            else:
                try:
                    current_payload = client.read_joints(unit=playback_unit)
                except Exception as exc:  # noqa: BLE001
                    print(f"Failed to read current joints: {exc}")
                    word_aborted = True
                    break
                current_raw = current_payload.get("angles")
                if not isinstance(current_raw, list):
                    print("Controller returned invalid joint data; aborting move.")
                    word_aborted = True
                    break
                try:
                    current_angles, _ = normalize_angles_for_playback(current_raw, playback_unit)
                except ValueError as exc:
                    print(f"Controller joint data invalid: {exc}")
                    word_aborted = True
                    break

            if len(target_angles) != len(current_angles):
                print("Mismatch in joint counts; skipping move.")
                word_aborted = True
                break

            try:
                max_delta = max(
                    abs(t - c) for t, c in zip(target_angles, current_angles)
                )
            except ValueError:
                print("Mismatch in joint counts; skipping move.")
                word_aborted = True
                break

            reference = args.reference_motion if args.reference_motion > 0 else max_delta or 1.0
            scale = min(1.0, max_delta / reference if reference else 0.0)
            motion_duration = max(args.min_duration, args.duration * scale)
            step_scale = max(scale, 0.1)
            effective_steps = max(1, int(round(args.steps * step_scale)))

            try:
                path = interpolate_joint_path(current_angles, target_angles, effective_steps)
            except ValueError as exc:
                print(f"Interpolation error: {exc}")
                word_aborted = True
                break

            delay = motion_duration / max(effective_steps, 1)
            print(
                f"Moving to '{resolved_label}' over {motion_duration:.2f}s "
                f"using {effective_steps} steps."
            )
            for joint_set in path[1:]:
                client.write_joints(joint_set, unit=playback_unit)
                time.sleep(delay)

            last_state = (target_angles, playback_unit)
            print(f"Reached '{resolved_label}'.")
            if len(label_sequence) > 1:
                time.sleep(args.letter_pause)
            if word_aborted:
                continue

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
