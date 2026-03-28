"""Schemas for the Neuromodulation subsystem.

Eight modulators act as global gain signals that bias perception,
decision-making, and memory consolidation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModulatorState(BaseModel):
    """Instantaneous levels of all eight neuromodulators."""

    reward_drive: float = Field(default=0.5, ge=0.0, le=1.0, description="Dopaminergic reward-seeking signal.")
    stress_load: float = Field(default=0.0, ge=0.0, le=1.0, description="Cortisol-like stress accumulation.")
    trust_level: float = Field(default=0.5, ge=0.0, le=1.0, description="Oxytocin-like trust / social openness.")
    baseline_stability: float = Field(default=0.8, ge=0.0, le=1.0, description="Serotonergic mood stability baseline.")
    damage_salience: float = Field(default=0.0, ge=0.0, le=1.0, description="Salience of damage / pain signals.")
    curiosity_drive: float = Field(default=0.5, ge=0.0, le=1.0, description="Noradrenergic exploration drive.")
    grief_persistence: float = Field(default=0.0, ge=0.0, le=1.0, description="Lingering grief or loss signal.")
    social_dependency: float = Field(default=0.3, ge=0.0, le=1.0, description="Degree of reliance on social bonds for well-being.")
    tick: int = Field(default=0, ge=0, description="Tick of this snapshot.")


class ModulatorShifts(BaseModel):
    """Requested or observed changes to modulator levels."""

    reward_drive_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to reward_drive.")
    stress_load_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to stress_load.")
    trust_level_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to trust_level.")
    baseline_stability_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to baseline_stability.")
    damage_salience_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to damage_salience.")
    curiosity_drive_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to curiosity_drive.")
    grief_persistence_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to grief_persistence.")
    social_dependency_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to social_dependency.")
    source: str = Field(default="", description="Module or event that caused these shifts.")
    tick: int = Field(default=0, ge=0, description="Tick when shifts were applied.")


class ModulatorConfig(BaseModel):
    """Configuration for the Neuromodulation module."""

    clamp_min: float = Field(default=0.0, ge=0.0, le=1.0, description="Global floor for all modulator values.")
    clamp_max: float = Field(default=1.0, ge=0.0, le=1.0, description="Global ceiling for all modulator values.")
    decay_rate: float = Field(default=0.02, ge=0.0, le=1.0, description="Per-tick passive drift toward baseline.")
    stress_recovery_rate: float = Field(default=0.01, ge=0.0, le=1.0, description="Per-tick passive stress recovery.")
    grief_decay_rate: float = Field(default=0.005, ge=0.0, le=1.0, description="Per-tick grief attenuation.")
    update_interval: int = Field(default=1, ge=1, description="Ticks between modulator updates.")
    enable_cross_modulation: bool = Field(default=True, description="Whether modulators influence each other (e.g. stress dampens curiosity).")
