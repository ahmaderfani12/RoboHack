"""Interactive script to record joint configurations and store them in JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from so100_robot import SO100RobotClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Disable torque, then record named joint configurations."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:80",
        help="Robot control server base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--robot-id",
        type=int,
        default=0,
        help="Robot identifier to control (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("recorded_positions.json"),
        help="Path to the JSON file where positions are stored (default: %(default)s).",
    )
    return parser.parse_args()


def load_positions(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse existing JSON at {path}: {exc}") from exc


def save_positions(path: Path, positions: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(positions, indent=2, sort_keys=True))


def main() -> int:
    args = parse_args()
    client = SO100RobotClient(args.base_url, robot_id=args.robot_id)

    print("Disabling torque…", flush=True)
    try:
        client.initialize()
        client.toggle_torque(False)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: failed to disable torque ({exc}). Continuing anyway.", file=sys.stderr)

    positions = load_positions(args.output)
    print(
        "Enter pose labels (type 'end' to finish). "
        "Each entry will snapshot the current joint angles.",
        flush=True,
    )

    while True:
        try:
            label = input("Pose label: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInput interrupted. Saving any recorded poses.")
            break

        if not label:
            print("Empty label ignored.")
            continue

        if label.lower() == "end":
            break

        try:
            joint_payload = client.read_joints(unit="degrees")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to read joints ({exc}). Try again.", file=sys.stderr)
            continue

        positions[label] = joint_payload
        print(f"Recorded {label}: {joint_payload.get('angles')}")

    save_positions(args.output, positions)
    print(f"Saved {len(positions)} entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
