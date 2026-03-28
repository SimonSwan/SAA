"""Schemas for the Allostasis subsystem.

Allostasis looks ahead: it forecasts future threats to homeostasis and
pre-emptively initiates regulatory actions before errors materialise.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ForecastResult(BaseModel):
    """Predicted future state of a homeostatic variable."""

    variable: str = Field(description="Name of the forecasted variable.")
    predicted_value: float = Field(ge=0.0, le=1.0, description="Expected value at the forecast horizon.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in the prediction.")
    horizon_ticks: int = Field(default=10, ge=1, description="How many ticks into the future the prediction covers.")
    trend: str = Field(default="stable", description="Qualitative trend: 'rising', 'falling', or 'stable'.")
    predicted_error: float = Field(default=0.0, description="Expected signed error at the horizon.")


class RiskHorizon(BaseModel):
    """Aggregate risk assessment across all forecasted variables."""

    forecasts: list[ForecastResult] = Field(default_factory=list, description="Individual variable forecasts.")
    aggregate_risk: float = Field(default=0.0, ge=0.0, le=1.0, description="Combined risk score (0=safe, 1=imminent crisis).")
    tick: int = Field(default=0, ge=0, description="Tick at which this risk assessment was made.")
    dominant_threat: str = Field(default="", description="Variable posing the greatest predicted risk.")


class AnticipAction(BaseModel):
    """A pre-emptive action recommended by the allostatic forecaster."""

    target_variable: str = Field(description="Variable the action aims to protect.")
    action_type: str = Field(default="adjust", description="Type of anticipatory action (e.g. 'adjust', 'reserve', 'alert').")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters.")
    urgency: float = Field(default=0.5, ge=0.0, le=1.0, description="How urgently the action should be executed.")
    expected_benefit: float = Field(default=0.0, ge=0.0, le=1.0, description="Predicted reduction in risk if the action is taken.")
    rationale: str = Field(default="", description="Human-readable justification for the action.")


class AllostasisConfig(BaseModel):
    """Configuration for the Allostasis module."""

    forecast_horizon: int = Field(default=20, ge=1, description="Default number of ticks to forecast ahead.")
    risk_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Aggregate risk above which anticipatory actions are triggered.")
    confidence_floor: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum confidence for a forecast to influence decisions.")
    max_anticipatory_actions: int = Field(default=3, ge=1, description="Maximum pre-emptive actions per tick.")
    update_interval: int = Field(default=5, ge=1, description="Ticks between allostatic re-forecasts.")
    enable_trend_detection: bool = Field(default=True, description="Whether to use trend analysis in forecasting.")
