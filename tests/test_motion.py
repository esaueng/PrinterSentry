"""Tests for motion sensitivity behavior."""

from __future__ import annotations

from custom_components.sentry3d.coordinator import _motion_cutoff_from_threshold


def test_higher_motion_sensitivity_lowers_required_cutoff() -> None:
    """Higher configured values should trigger motion more easily."""
    assert _motion_cutoff_from_threshold(16) < _motion_cutoff_from_threshold(8)
    assert _motion_cutoff_from_threshold(8) < _motion_cutoff_from_threshold(4)


def test_default_motion_sensitivity_preserves_existing_cutoff() -> None:
    """The default value should preserve the prior effective cutoff."""
    assert _motion_cutoff_from_threshold(8) == 8
