"""Experiment configuration — structured config for test runs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for the agent under test."""

    agent_type: str = "swan"
    module_configs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    """Full experiment configuration."""

    test_name: str
    description: str = ""
    agent: AgentConfig = Field(default_factory=AgentConfig)
    seeds: list[int] = Field(default_factory=lambda: [42])
    num_ticks: int = 100
    scenario_params: dict[str, Any] = Field(default_factory=dict)
    output_dir: str = "results"
    save_artifacts: bool = True
    save_state_traces: bool = True


class BatchConfig(BaseModel):
    """Configuration for running multiple experiments."""

    experiments: list[ExperimentConfig] = Field(default_factory=list)
    agents: list[AgentConfig] = Field(default_factory=list)
    seeds: list[int] = Field(default_factory=lambda: [42, 123, 456, 789, 1024])
    output_dir: str = "results"
