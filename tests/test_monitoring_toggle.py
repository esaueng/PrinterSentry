"""Tests for runtime monitoring toggle behavior."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from custom_components.sentry3d.const import (
    DEFAULT_UNHEALTHY_CONFIDENCE_THRESHOLD,
    DEFAULT_VISION_PROMPT,
    LLM_PROVIDER_OLLAMA,
    PLATFORMS,
    STATUS_HEALTHY,
)
from custom_components.sentry3d.coordinator import Sentry3DCoordinator
from custom_components.sentry3d.logic import REQUIRED_SIGNAL_KEYS


def _coordinator_stub(**overrides: Any) -> Sentry3DCoordinator:
    coordinator = object.__new__(Sentry3DCoordinator)
    coordinator.motion_detection_enabled = True
    coordinator.llm_provider = LLM_PROVIDER_OLLAMA
    coordinator.vision_prompt = DEFAULT_VISION_PROMPT
    coordinator.unhealthy_confidence_threshold = DEFAULT_UNHEALTHY_CONFIDENCE_THRESHOLD
    coordinator._monitoring_enabled = False
    coordinator._last_inference_state = None
    coordinator._llm_reachable = None
    coordinator._last_model_output = None
    coordinator._last_model_output_hash = None
    coordinator._last_frame_time = None
    coordinator._last_frame_hash = None
    coordinator._last_llm_frame_time = None
    coordinator._last_llm_frame_hash = None
    coordinator._last_overlay_frame = None
    coordinator._same_frame_count = 0
    coordinator._capture_reused_last_frame = False
    coordinator._consecutive_unhealthy_count = 0
    coordinator._incident_active = False
    coordinator._incident_start_time = None
    coordinator._last_notification_time = None

    for key, value in overrides.items():
        setattr(coordinator, key, value)

    return coordinator


def test_switch_platform_is_registered() -> None:
    assert "switch" in PLATFORMS


def test_monitoring_disabled_state_preserves_last_inference() -> None:
    coordinator = _coordinator_stub(
        _last_inference_state={
            "status": STATUS_HEALTHY,
            "confidence": 0.94,
            "reason": "Print looks normal",
            "short_explanation": "Looks normal",
            "signals": {key: False for key in REQUIRED_SIGNAL_KEYS},
            "focus_region": None,
            "last_llm_frame_time": "2026-04-29T12:00:00+00:00",
            "last_llm_frame_hash": "llm-frame",
            "overlay_available": False,
            "unhealthy_gate_passed": False,
        },
        _last_frame_hash="last-frame",
    )

    state = coordinator._build_monitoring_disabled_state(
        now=datetime(2026, 4, 29, 12, 5, tzinfo=timezone.utc)
    )

    assert state["monitoring_enabled"] is False
    assert state["status"] == STATUS_HEALTHY
    assert state["confidence"] == 0.94
    assert state["inference_skipped"] is True
    assert state["skip_reason"] == "Monitoring disabled"
    assert state["last_frame_hash"] == "last-frame"
    assert state["last_llm_frame_hash"] == "llm-frame"
