"""Convenience client for the SO-100 robot control REST API.

The client focuses on the motion-control endpoints exposed in ``openapi.json``.
It wraps the robot control primitives (initialization, absolute/relative moves,
teleoperation, joint and torque control, etc.) in a small Python class.

Typical usage::

    from so100_robot import SO100RobotClient

    robot = SO100RobotClient(\"http://localhost:8000\", robot_id=0)
    robot.initialize()
    robot.move_absolute(
        x=30,
        y=0,
        z=10,
        rx=0,
        ry=0,
        rz=0,
        open=1,
        angle_unit=\"degrees\",  # or \"rad\"
    )
    robot.move_relative(z=-5)
    joints_deg = robot.read_joints(unit=\"degrees\")
    robot.write_joints([0.0] * len(joints_deg[\"angles\"]))

    robot.move_absolute(
        table=[
            {\"x\": 25, \"z\": 15, \"open\": 1},
            {\"x\": 20, \"z\": 20, \"open\": 0},
        ],
        angle_unit=\"degrees\",
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from math import degrees
from typing import Any, Dict, Mapping, Optional, Sequence

import requests


class RobotAPIError(RuntimeError):
    """Raised when the robot returns a non-ok status response."""


def _drop_none(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a new dict without keys whose value is ``None``."""
    return {key: value for key, value in mapping.items() if value is not None}


def _normalize_angle_unit(unit: Optional[str], *, allow_motor_units: bool = False) -> str:
    """Normalize angle unit strings to API-friendly values."""
    if unit is None:
        return "degrees"
    normalized = unit.lower()
    alias_map = {
        "deg": "degrees",
        "degree": "degrees",
        "degs": "degrees",
        "radians": "rad",
        "radian": "rad",
        "rads": "rad",
        "motor-unit": "motor_units",
        "motorunits": "motor_units",
        "motor unit": "motor_units",
    }
    normalized = alias_map.get(normalized, normalized)
    allowed = {"degrees", "rad"}
    if allow_motor_units:
        allowed = allowed | {"motor_units"}
    if normalized not in allowed:
        extra = " or 'motor_units'" if allow_motor_units else ""
        raise ValueError(f"Unsupported angle unit '{unit}'. Use 'degrees', 'rad'{extra}.")
    return normalized


def _maybe_to_degrees(value: Optional[float], unit: str) -> Optional[float]:
    if value is None or unit == "degrees":
        return value
    return degrees(value)


_MOVE_ABSOLUTE_FIELDS = {
    "x",
    "y",
    "z",
    "rx",
    "ry",
    "rz",
    "open",
    "max_trials",
    "position_tolerance",
    "orientation_tolerance",
    "angle_unit",
    "robot_id",
}


@dataclass(frozen=True)
class UDPServerInfo:
    """Information about the UDP teleoperation server."""

    ip: str
    port: int

    @classmethod
    def from_response(cls, payload: Mapping[str, Any]) -> "UDPServerInfo":
        return cls(ip=payload["ip"], port=payload["port"])


class SO100RobotClient:
    """Small helper around the SO-100 control REST API."""

    def __init__(
        self,
        base_url: str,
        robot_id: Optional[int] = None,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._robot_id = robot_id
        self._timeout = timeout
        self._session = session or requests.Session()

    @property
    def robot_id(self) -> Optional[int]:
        """Default robot id attached to this client."""
        return self._robot_id

    @robot_id.setter
    def robot_id(self, value: Optional[int]) -> None:
        self._robot_id = value

    def _params_with_robot_id(self, robot_id: Optional[int]) -> Optional[Dict[str, int]]:
        rid = robot_id if robot_id is not None else self._robot_id
        if rid is None:
            return None
        return {"robot_id": rid}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        response = self._session.request(
            method,
            url,
            params=params,
            json=json,
            timeout=self._timeout,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    def _expect_ok(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        status = payload.get("status", "ok")
        if status != "ok":
            raise RobotAPIError(payload.get("message", "Robot returned an error status."))
        return payload

    # --- Convenience methods -------------------------------------------------

    def initialize(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Call ``/move/init`` to reset the robot pose."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request("POST", "/move/init", params=params)
        return self._expect_ok(payload)

    def _move_absolute_single(
        self,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        rx: Optional[float] = None,
        ry: Optional[float] = None,
        rz: Optional[float] = None,
        open: Optional[float] = None,
        max_trials: Optional[int] = None,
        position_tolerance: Optional[float] = None,
        orientation_tolerance: Optional[float] = None,
        angle_unit: Optional[str] = None,
        robot_id: Optional[int] = None,
    ) -> Mapping[str, Any]:
        params = self._params_with_robot_id(robot_id)
        unit = _normalize_angle_unit(angle_unit)
        body = _drop_none(
            {
                "x": x,
                "y": y,
                "z": z,
                "rx": _maybe_to_degrees(rx, unit),
                "ry": _maybe_to_degrees(ry, unit),
                "rz": _maybe_to_degrees(rz, unit),
                "open": open,
                "max_trials": max_trials,
                "position_tolerance": position_tolerance,
                "orientation_tolerance": _maybe_to_degrees(orientation_tolerance, unit)
                if orientation_tolerance is not None
                else None,
            }
        )
        payload = self._request("POST", "/move/absolute", params=params, json=body)
        return self._expect_ok(payload)

    def move_absolute(
        self,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        rx: Optional[float] = None,
        ry: Optional[float] = None,
        rz: Optional[float] = None,
        open: Optional[float] = None,
        max_trials: Optional[int] = None,
        position_tolerance: Optional[float] = None,
        orientation_tolerance: Optional[float] = None,
        angle_unit: Optional[str] = None,
        robot_id: Optional[int] = None,
        table: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Mapping[str, Any] | list[Mapping[str, Any]]:
        """Move the end-effector to an absolute pose (centimeters, degrees by default).

        If ``table`` is provided, it should be an iterable of mappings where each mapping
        contains the same keyword arguments accepted by this method. Base keyword values
        supplied alongside ``table`` act as defaults for every row. The method returns a
        list with the response payload for each entry in the table.
        """
        if table is not None:
            defaults = {
                "x": x,
                "y": y,
                "z": z,
                "rx": rx,
                "ry": ry,
                "rz": rz,
                "open": open,
                "max_trials": max_trials,
                "position_tolerance": position_tolerance,
                "orientation_tolerance": orientation_tolerance,
                "angle_unit": angle_unit,
                "robot_id": robot_id,
            }
            results: list[Mapping[str, Any]] = []
            for idx, row in enumerate(table):
                if not isinstance(row, Mapping):
                    raise TypeError(
                        f"Entry {idx} in table must be a mapping; received {type(row).__name__}."
                    )
                unexpected = set(row) - _MOVE_ABSOLUTE_FIELDS
                if unexpected:
                    details = ", ".join(sorted(unexpected))
                    raise ValueError(f"Table row {idx} includes unsupported keys: {details}")
                combined = dict(defaults)
                combined.update(row)
                results.append(self._move_absolute_single(**combined))
            return results

        return self._move_absolute_single(
            x=x,
            y=y,
            z=z,
            rx=rx,
            ry=ry,
            rz=rz,
            open=open,
            max_trials=max_trials,
            position_tolerance=position_tolerance,
            orientation_tolerance=orientation_tolerance,
            angle_unit=angle_unit,
            robot_id=robot_id,
        )

    def move_relative(
        self,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        rx: Optional[float] = None,
        ry: Optional[float] = None,
        rz: Optional[float] = None,
        open: Optional[float] = None,
        angle_unit: Optional[str] = None,
        robot_id: Optional[int] = None,
    ) -> Mapping[str, Any]:
        """Move the end-effector by relative deltas (centimeters, degrees by default)."""
        params = self._params_with_robot_id(robot_id)
        unit = _normalize_angle_unit(angle_unit)
        body = _drop_none(
            {
                "x": x,
                "y": y,
                "z": z,
                "rx": _maybe_to_degrees(rx, unit),
                "ry": _maybe_to_degrees(ry, unit),
                "rz": _maybe_to_degrees(rz, unit),
                "open": open,
            }
        )
        payload = self._request("POST", "/move/relative", params=params, json=body)
        return self._expect_ok(payload)

    def teleop_control(
        self,
        *,
        x: float,
        y: float,
        z: float,
        rx: float,
        ry: float,
        rz: float,
        open: float,
        direction_x: Optional[float] = None,
        direction_y: Optional[float] = None,
        source: Optional[str] = None,
        timestamp: Optional[float] = None,
        angle_unit: Optional[str] = None,
        robot_id: Optional[int] = None,
    ) -> Mapping[str, Any]:
        """Send a MetaQuest-style teleoperation frame (angles assumed degrees unless set otherwise)."""
        params = self._params_with_robot_id(robot_id)
        unit = _normalize_angle_unit(angle_unit)
        body = _drop_none(
            {
                "x": x,
                "y": y,
                "z": z,
                "rx": _maybe_to_degrees(rx, unit),
                "ry": _maybe_to_degrees(ry, unit),
                "rz": _maybe_to_degrees(rz, unit),
                "open": open,
                "direction_x": direction_x,
                "direction_y": direction_y,
                "source": source,
                "timestamp": timestamp,
            }
        )
        payload = self._request("POST", "/move/teleop", params=params, json=body)
        return self._expect_ok(payload)

    def start_teleop_udp(self) -> UDPServerInfo:
        """Start the UDP teleoperation bridge."""
        payload = self._request("POST", "/move/teleop/udp")
        info = self._expect_ok(payload)
        return UDPServerInfo.from_response(info)

    def stop_teleop_udp(self) -> Mapping[str, Any]:
        """Stop a running UDP teleoperation bridge."""
        payload = self._request("POST", "/move/teleop/udp/stop")
        return self._expect_ok(payload)

    def say_hello(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Test the gripper by opening and closing it once."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request("POST", "/move/hello", params=params)
        return self._expect_ok(payload)

    def sleep(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Send the robot to its sleep pose and disable torque."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request("POST", "/move/sleep", params=params)
        return self._expect_ok(payload)

    def calibrate(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Run the calibration routine."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request("POST", "/calibrate", params=params)
        return self._expect_ok(payload)

    def read_end_effector(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Read the last known end-effector pose."""
        params = self._params_with_robot_id(robot_id)
        return self._request("POST", "/end-effector/read", params=params)

    def read_voltage(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Return voltage information for the robot joints."""
        params = self._params_with_robot_id(robot_id)
        return self._request("POST", "/voltage/read", params=params)

    def read_temperature(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Return temperature information for the robot joints."""
        params = self._params_with_robot_id(robot_id)
        return self._request("POST", "/temperature/read", params=params)

    def set_temperature_limits(
        self, maximum_temperature: Sequence[int], robot_id: Optional[int] = None
    ) -> Mapping[str, Any]:
        """Update the allowed maximum temperature per joint."""
        params = self._params_with_robot_id(robot_id)
        body = {"maximum_temperature": list(maximum_temperature)}
        payload = self._request("POST", "/temperature/write", params=params, json=body)
        return self._expect_ok(payload)

    def read_torque(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Return torque values for the robot joints."""
        params = self._params_with_robot_id(robot_id)
        return self._request("POST", "/torque/read", params=params)

    def toggle_torque(self, enable: bool, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Enable or disable torque control."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request(
            "POST",
            "/torque/toggle",
            params=params,
            json={"torque_status": enable},
        )
        return self._expect_ok(payload)

    def read_joints(
        self,
        *,
        unit: Optional[str] = None,
        joints_ids: Optional[Sequence[int]] = None,
        source: Optional[str] = None,
        robot_id: Optional[int] = None,
    ) -> Mapping[str, Any]:
        """Return the current joint angles with optional unit/source filtering."""
        params = self._params_with_robot_id(robot_id)
        payload: Dict[str, Any] = {}
        if unit is not None:
            payload["unit"] = _normalize_angle_unit(unit, allow_motor_units=True)
        if joints_ids is not None:
            payload["joints_ids"] = list(joints_ids)
        if source is not None:
            payload["source"] = source
        body = payload or None
        return self._request("POST", "/joints/read", params=params, json=body)

    def write_joints(
        self,
        angles: Sequence[float],
        *,
        unit: Optional[str] = None,
        joints_ids: Optional[Sequence[int]] = None,
        robot_id: Optional[int] = None,
    ) -> Mapping[str, Any]:
        """Set joint angles directly."""
        params = self._params_with_robot_id(robot_id)
        body: Dict[str, Any] = {"angles": list(angles)}
        if unit is not None:
            body["unit"] = _normalize_angle_unit(unit, allow_motor_units=True)
        if joints_ids is not None:
            body["joints_ids"] = list(joints_ids)
        payload = self._request("POST", "/joints/write", params=params, json=body)
        return self._expect_ok(payload)

    def start_gravity_compensation(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Enable gravity compensation."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request("POST", "/gravity/start", params=params)
        return self._expect_ok(payload)

    def stop_gravity_compensation(self, robot_id: Optional[int] = None) -> Mapping[str, Any]:
        """Disable gravity compensation."""
        params = self._params_with_robot_id(robot_id)
        payload = self._request("POST", "/gravity/stop", params=params)
        return self._expect_ok(payload)

    # --- Generic helpers -----------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """Call any endpoint on the API."""
        robot_params = self._params_with_robot_id(None)
        merged_params: Dict[str, Any] = {}
        if params:
            merged_params.update(params)
        if robot_params:
            merged_params.setdefault("robot_id", robot_params["robot_id"])
        return self._request(method, path, params=merged_params or None, json=json)
