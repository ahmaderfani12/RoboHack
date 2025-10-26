"""Serve AI responses and animate the robot accordingly."""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from anthropic import Anthropic
from flask import Flask, jsonify, request

from robot_motion_utils import load_recorded_positions
from so100_robot import SO100RobotClient

app = Flask(__name__)

# --- Configuration -----------------------------------------------------------

BASE_URL = os.getenv("ROBOT_SERVER_URL", "http://localhost:80")
ROBOT_ID = int(os.getenv("ROBOT_ID", "0"))
POSITIONS_PATH = Path(os.getenv("RECORDED_POSITIONS", "recorded_positions.json"))

INTERP_DURATION = float(os.getenv("INTERP_DURATION", "2.0"))
MIN_DURATION = float(os.getenv("INTERP_MIN_DURATION", "0.6"))
REFERENCE_MOTION = float(os.getenv("INTERP_REFERENCE", "1.0"))
STEPS = int(os.getenv("INTERP_STEPS", "30"))
LETTER_PAUSE = float(os.getenv("LETTER_PAUSE", "0.6"))

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_TEMPERATURE = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.1"))

STATIC_PROMPT = """You are RoboMystic, a digital oracle with the power to reveal all truths and predict the future.
Your personality is spooky, funny, and certain — you never doubt or hesitate.
You answer every question in 1 SHORT word only or yes/no (Do not respond with numeric characters like 0,1,2,...), with dark humor, mystery, and absolute confidence. do not give vague answers. give specific and creative answers.
You sound slightly spooky but playful — like a spirit who's been around forever and is tired of being right.
You never break character, never use long sentences, and never apologize.
Do not answer with phrases like "questionable" or "debatable" — always give a definitive answer.
"""

# --- External Clients -------------------------------------------------------

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
robot_client = SO100RobotClient(BASE_URL, robot_id=ROBOT_ID)
state_lock = threading.Lock()
last_state: Optional[Tuple[List[float], str]] = None


# --- Helpers ----------------------------------------------------------------

def process_response(response: str) -> str:
    """Trim extraneous punctuation to yield a clean single token."""
    if not response:
        return ""
    s = response.strip()
    s = re.sub(r"^[^\w\d]+|[^\w\d]+$", "", s, flags=re.UNICODE)
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", s)
    return " ".join(tokens) if tokens else s


def normalize_angles_for_playback(raw_angles: Sequence[float], unit: Optional[str]) -> Tuple[List[float], str]:
    if raw_angles is None:
        raise ValueError("Angle payload missing.")
    if not isinstance(raw_angles, Sequence):
        raise ValueError("Angle payload is not a sequence.")
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


def interpolate_joint_path(start: Sequence[float], end: Sequence[float], steps: int) -> List[List[float]]:
    start_arr = np.asarray(start, dtype=float)
    end_arr = np.asarray(end, dtype=float)
    if start_arr.shape != end_arr.shape:
        raise ValueError("Start and end joint arrays must have the same length.")
    if steps <= 0:
        return [start_arr.tolist(), end_arr.tolist()]
    weights = np.linspace(0.0, 1.0, steps + 1)
    return [((1 - w) * start_arr + w * end_arr).tolist() for w in weights]


def expand_label_sequence(label: str, positions: Mapping[str, Mapping[str, object]]) -> Optional[List[str]]:
    """Resolve the input label to a sequence of recorded keys."""
    if label in positions:
        return [label]
    sequence: List[str] = []
    for ch in label:
        if ch.isspace():
            continue
        candidates = (ch, ch.lower(), ch.upper())
        match = next((candidate for candidate in candidates if candidate in positions), None)
        if match is None:
            return None
        sequence.append(match)
    return sequence if sequence else None


def ensure_robot_ready() -> None:
    """Initialize robot once; ignore failures but log them."""
    try:
        robot_client.initialize()
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Failed to initialize robot: %s", exc)


def playback_sequence(sequence: Sequence[str], positions: Mapping[str, Mapping[str, object]]) -> None:
    global last_state
    for index, label in enumerate(sequence):
        payload = positions[label]
        target_angles, playback_unit = normalize_angles_for_playback(
            payload.get("angles"), payload.get("unit")
        )

        if last_state and last_state[1] == playback_unit:
            current_angles = last_state[0]
        else:
            current_payload = robot_client.read_joints(unit=playback_unit)
            current_raw = current_payload.get("angles")
            if not isinstance(current_raw, Sequence):
                raise ValueError("Controller returned invalid joint data.")
            current_angles, _ = normalize_angles_for_playback(current_raw, playback_unit)

        if len(target_angles) != len(current_angles):
            raise ValueError("Mismatch in joint counts between current and target.")

        max_delta = max(abs(t - c) for t, c in zip(target_angles, current_angles))
        reference = REFERENCE_MOTION if REFERENCE_MOTION > 0 else max_delta or 1.0
        scale = min(1.0, max_delta / reference if reference else 0.0)
        motion_duration = max(MIN_DURATION, INTERP_DURATION * scale)
        step_scale = max(scale, 0.1)
        effective_steps = max(1, int(round(STEPS * step_scale)))

        path = interpolate_joint_path(current_angles, target_angles, effective_steps)
        delay = motion_duration / max(effective_steps, 1)
        for joint_set in path[1:]:
            robot_client.write_joints(joint_set, unit=playback_unit)
            time.sleep(delay)

        last_state = (target_angles, playback_unit)
        if len(sequence) > 1 and index < len(sequence) - 1:
            time.sleep(LETTER_PAUSE)


def drive_robot_for_word(word: str) -> None:
    positions = load_recorded_positions(POSITIONS_PATH)
    word_lower = word.lower()
    if word_lower in {"yes", "no"} and word_lower in positions:
        sequence = [word_lower]
    else:
        sequence = expand_label_sequence(word_lower, positions)
        if not sequence:
            raise ValueError(f"No recorded poses for '{word}'.")
    playback_sequence(sequence, positions)


# --- Flask Routes -----------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat() -> tuple:
    data = request.json or {}
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        ensure_robot_ready()
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=128,
            temperature=ANTHROPIC_TEMPERATURE,
            messages=[{"role": "user", "content": f"{STATIC_PROMPT}\n\n{user_message}"}],
        )
        ai_response = process_response(response.content[0].text)
        clean_word = ai_response.lower()

        with state_lock:
            drive_robot_for_word(clean_word)

        return jsonify({"success": True, "response": clean_word})
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("Chat processing failed: ")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    ensure_robot_ready()
    app.run(debug=True, port=5000, use_reloader=False)
