"""Schemas for the Interoception subsystem.

Interoception monitors internal signals (the agent's 'felt body'),
mapping raw sensor channels to a normalised vector that downstream
modules consume.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """A single raw reading from an internal sensor."""

    channel: str = Field(description="Name of the sensor channel (e.g. 'core_temp', 'cpu_load').")
    raw_value: float = Field(description="Un-normalised sensor value.")
    timestamp: float = Field(default=0.0, ge=0.0, description="Time or tick at which the reading was taken.")
    unit: str = Field(default="", description="Optional measurement unit for the raw value.")
    reliability: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this reading (0=unreliable, 1=perfect).")


class InteroceptiveVector(BaseModel):
    """Normalised snapshot of all interoceptive channels.

    Every value in *channels* is clamped to [0, 1] by convention.
    """

    channels: dict[str, float] = Field(
        default_factory=dict,
        description="Map of channel name -> normalised 0-1 value.",
    )
    tick: int = Field(default=0, ge=0, description="Simulation tick of this snapshot.")
    source_readings: list[SensorReading] = Field(
        default_factory=list,
        description="Raw readings that produced this vector (optional audit trail).",
    )


class InteroceptiveAlert(BaseModel):
    """Alarm raised when an interoceptive channel breaches its safe range."""

    channel: str = Field(description="Channel that triggered the alert.")
    current_value: float = Field(ge=0.0, le=1.0, description="Current normalised value.")
    threshold: float = Field(ge=0.0, le=1.0, description="Threshold that was breached.")
    direction: str = Field(default="above", description="'above' or 'below' the threshold.")
    severity: float = Field(default=0.5, ge=0.0, le=1.0, description="Severity of the alert (0=minor, 1=critical).")
    tick: int = Field(default=0, ge=0, description="Tick when the alert was raised.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context.")


class InteroceptionConfig(BaseModel):
    """Configuration for the Interoception module."""

    default_channels: list[str] = Field(
        default_factory=lambda: [
            "energy",
            "temperature",
            "strain",
            "latency_load",
            "memory_integrity",
            "damage",
        ],
        description="Channel names to initialise by default.",
    )
    alert_threshold_high: float = Field(default=0.85, ge=0.0, le=1.0, description="Default upper-bound alert threshold.")
    alert_threshold_low: float = Field(default=0.15, ge=0.0, le=1.0, description="Default lower-bound alert threshold.")
    smoothing_factor: float = Field(default=0.3, ge=0.0, le=1.0, description="Exponential-moving-average smoothing for noisy channels.")
    update_interval: int = Field(default=1, ge=1, description="Ticks between interoceptive scans.")
