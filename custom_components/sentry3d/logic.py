"""Core parsing and incident logic for Sentry3D."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from .const import STATUS_EMPTY, STATUS_HEALTHY, STATUS_UNHEALTHY, STATUS_UNKNOWN

REQUIRED_SIGNAL_KEYS = (
    "bed_adhesion_ok",
    "spaghetti_detected",
    "layer_shift_detected",
    "detached_part_detected",
    "blob_detected",
    "supports_failed_detected",
    "print_missing_detected",
)

DEFECT_SIGNAL_KEYS = (
    "spaghetti_detected",
    "layer_shift_detected",
    "detached_part_detected",
    "blob_detected",
    "supports_failed_detected",
    "print_missing_detected",
)


@dataclass(slots=True)
class InferenceResult:
    """Normalized model output."""

    status: str
    confidence: float | None
    reason: str
    short_explanation: str
    signals: dict[str, bool]
    focus_region: dict[str, float] | None


@dataclass(slots=True)
class IncidentTransition:
    """State transition for consecutive unhealthy and incidents."""

    consecutive_unhealthy_count: int
    incident_active: bool
    new_incident: bool
    cleared_incident: bool


def _derive_short_explanation(text: str, fallback: str = "Unknown") -> str:
    """Build a concise UI-friendly summary from a longer message."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return fallback

    for separator in (":", ";", ".", ",", "\n"):
        normalized = normalized.split(separator, 1)[0].strip()
        if normalized:
            break

    words = normalized.split()
    if len(words) > 6:
        normalized = " ".join(words[:6])

    return normalized[:48].strip() or fallback


def parse_model_output(raw_text: str) -> InferenceResult:
    """Parse and validate strict JSON output from Ollama."""
    stripped = raw_text.strip()
    if not stripped:
        raise ValueError("Empty model output")

    # Require a single JSON object as the complete output.
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError("Model output contains non-JSON content")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as err:
        raise ValueError("Invalid JSON output") from err

    if not isinstance(payload, dict):
        raise ValueError("Output must be a JSON object")

    status = payload.get("status")
    if status not in (STATUS_HEALTHY, STATUS_UNHEALTHY, STATUS_EMPTY):
        raise ValueError("Invalid status")

    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("Confidence must be numeric")
    confidence = float(confidence)
    if confidence <= 0.0 or confidence >= 1.0:
        raise ValueError("Confidence must be between 0 and 1 (exclusive)")

    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Reason must be a non-empty string")
    reason = reason.strip()

    short_explanation = payload.get("short_explanation")
    if isinstance(short_explanation, str) and short_explanation.strip():
        short_explanation = short_explanation.strip()
    else:
        short_explanation = _derive_short_explanation(reason)

    signals_raw = payload.get("signals")
    if not isinstance(signals_raw, dict):
        raise ValueError("Signals must be an object")

    signal_keys = set(signals_raw)
    required_keys = set(REQUIRED_SIGNAL_KEYS)
    if signal_keys != required_keys:
        missing = sorted(required_keys - signal_keys)
        extra = sorted(signal_keys - required_keys)
        raise ValueError(f"Signals keys mismatch: missing={missing}, extra={extra}")

    signals: dict[str, bool] = {}
    for key in REQUIRED_SIGNAL_KEYS:
        value = signals_raw.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"Signal {key} must be boolean")
        signals[key] = value

    if status == STATUS_HEALTHY and any(signals[key] for key in DEFECT_SIGNAL_KEYS):
        raise ValueError("Healthy output cannot have defect signals set")
    if status == STATUS_EMPTY and any(signals.values()):
        raise ValueError("Empty output cannot have any signals set")

    focus_region_raw = payload.get("focus_region")
    focus_region: dict[str, float] | None
    if focus_region_raw is None:
        focus_region = None
    else:
        if not isinstance(focus_region_raw, dict):
            raise ValueError("focus_region must be an object or null")
        required_region_keys = {"x", "y", "width", "height"}
        if set(focus_region_raw) != required_region_keys:
            missing = sorted(required_region_keys - set(focus_region_raw))
            extra = sorted(set(focus_region_raw) - required_region_keys)
            raise ValueError(
                f"focus_region keys mismatch: missing={missing}, extra={extra}"
            )

        focus_region = {}
        for key in ("x", "y", "width", "height"):
            value = focus_region_raw.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"focus_region.{key} must be numeric")
            value = float(value)
            if value < 0.0 or value > 1.0:
                raise ValueError(f"focus_region.{key} must be between 0 and 1")
            focus_region[key] = value

        if focus_region["width"] <= 0.0 or focus_region["height"] <= 0.0:
            raise ValueError("focus_region width and height must be greater than 0")
        if focus_region["x"] + focus_region["width"] > 1.0:
            raise ValueError("focus_region exceeds image width")
        if focus_region["y"] + focus_region["height"] > 1.0:
            raise ValueError("focus_region exceeds image height")

    if status != STATUS_UNHEALTHY and focus_region is not None:
        raise ValueError("focus_region is only valid for UNHEALTHY results")

    return InferenceResult(
        status=status,
        confidence=confidence,
        reason=reason,
        short_explanation=short_explanation,
        signals=signals,
        focus_region=focus_region,
    )


def unknown_result(reason: str) -> InferenceResult:
    """Create a normalized unknown result."""
    return InferenceResult(
        status=STATUS_UNKNOWN,
        confidence=None,
        reason=reason,
        short_explanation=_derive_short_explanation(reason),
        signals={key: False for key in REQUIRED_SIGNAL_KEYS},
        focus_region=None,
    )


def apply_incident_logic(
    *,
    current_status: str,
    previous_consecutive_unhealthy: int,
    incident_active: bool,
    unhealthy_consecutive_threshold: int,
) -> IncidentTransition:
    """Transition consecutive unhealthy counter and incident state."""
    consecutive = previous_consecutive_unhealthy
    new_incident = False
    cleared_incident = False

    if current_status == STATUS_UNHEALTHY:
        consecutive += 1
        if not incident_active and consecutive >= unhealthy_consecutive_threshold:
            incident_active = True
            new_incident = True
    elif current_status in (STATUS_HEALTHY, STATUS_EMPTY):
        consecutive = 0
        if incident_active:
            incident_active = False
            cleared_incident = True

    return IncidentTransition(
        consecutive_unhealthy_count=consecutive,
        incident_active=incident_active,
        new_incident=new_incident,
        cleared_incident=cleared_incident,
    )


def should_send_notification(
    *,
    incident_active: bool,
    new_incident: bool,
    last_notification_time: datetime | None,
    now: datetime,
    min_notification_interval_sec: int,
) -> bool:
    """Determine whether a notification should be sent."""
    if not incident_active:
        return False
    if new_incident:
        return True
    if last_notification_time is None:
        return True
    return (now - last_notification_time) >= timedelta(
        seconds=min_notification_interval_sec
    )
