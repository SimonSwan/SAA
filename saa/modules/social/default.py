"""DefaultSocial — relationship formation and external agent weighting.

Uses a networkx DiGraph to track directed relationships.  Each edge stores
trust, dependency, attachment, bond_strength, betrayal_count, and interaction
history.  The module processes social events every tick, applies natural trust
decay, and emits events when relationship thresholds are crossed.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
from pydantic import BaseModel, Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class SocialState(BaseState):
    """Serializable snapshot of the social graph."""

    module_name: str = "social"
    version: str = "0.1.0"

    relationships: dict[str, dict[str, Any]] = Field(default_factory=dict)
    attachment_risk: float = 0.0
    total_bond_strength: float = 0.0


class SocialConfig(BaseConfig):
    """Configuration knobs for the social module."""

    trust_gain_rate: float = 0.05
    trust_decay_rate: float = 0.02
    betrayal_impact: float = 0.3
    attachment_threshold: float = 0.6


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultSocial(BaseModule):
    """Relationship formation and external agent weighting."""

    VERSION = "0.1.0"
    CAPABILITIES = ["social"]
    DEPENDENCIES = ["embodiment"]

    def __init__(self) -> None:
        self._state = SocialState()
        self._config = SocialConfig()
        self._graph: nx.DiGraph = nx.DiGraph()

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = SocialConfig(**config)
        self._state = SocialState()
        self._graph = nx.DiGraph()
        self._graph.add_node("self")

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> SocialState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, SocialState):
            self._state = state.model_copy()
        else:
            self._state = SocialState(**state.model_dump())
        # Rebuild graph from relationships dict
        self._graph = nx.DiGraph()
        for agent_id, props in self._state.relationships.items():
            self._graph.add_edge("self", agent_id, **props)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _ensure_relationship(self, agent_id: str) -> dict[str, Any]:
        """Ensure an edge exists for *agent_id* and return its data dict."""
        if not self._graph.has_edge("self", agent_id):
            defaults = {
                "trust": 0.5,
                "dependency": 0.0,
                "attachment": 0.0,
                "bond_strength": 0.0,
                "betrayal_count": 0,
                "interactions": 0,
                "last_seen_tick": 0,
            }
            self._graph.add_edge("self", agent_id, **defaults)
        return self._graph["self"][agent_id]

    def _compute_bond_strength(self, rel: dict[str, Any]) -> float:
        """Weighted combination of trust, dependency, and attachment."""
        return self._clamp(
            rel["trust"] * 0.4 + rel["dependency"] * 0.25 + rel["attachment"] * 0.35
        )

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        cfg = self._config
        s = self._state
        s.tick = tick
        dt = context.dt
        events_out: list[Event] = []

        present_agents = set(context.environment.social_agents)

        # Ensure all currently visible agents have a relationship
        for agent_id in present_agents:
            self._ensure_relationship(agent_id)

        # ---- Natural trust decay on ALL known agents ----------------------
        for agent_id in list(self._graph.successors("self")):
            rel = self._graph["self"][agent_id]
            if rel["trust"] > 0.0:
                rel["trust"] = self._clamp(
                    rel["trust"] - cfg.trust_decay_rate * dt
                )

        # ---- Process social events from context --------------------------
        for event in context.events:
            agent_id = event.data.get("agent_id")
            if agent_id is None:
                continue

            rel = self._ensure_relationship(agent_id)
            rel["interactions"] = rel.get("interactions", 0) + 1
            old_trust = rel["trust"]

            if event.event_type == "trust_gain":
                # After betrayal, trust recovery is slower (caution persistence)
                gain_factor = 1.0
                if rel["betrayal_count"] > 0:
                    gain_factor = 1.0 / (1.0 + rel["betrayal_count"])
                amount = event.data.get("amount", 1.0)
                rel["trust"] = self._clamp(
                    rel["trust"] + cfg.trust_gain_rate * amount * gain_factor * dt
                )
                # Positive interactions grow attachment slowly
                rel["attachment"] = self._clamp(
                    rel["attachment"] + cfg.trust_gain_rate * 0.3 * dt
                )

            elif event.event_type == "betrayal":
                rel["trust"] = self._clamp(
                    rel["trust"] - cfg.betrayal_impact
                )
                rel["betrayal_count"] = rel.get("betrayal_count", 0) + 1
                # Trust broken event: trust drops below 0.2 from above 0.5
                if old_trust >= 0.5 and rel["trust"] < 0.2:
                    events_out.append(Event(
                        tick=tick,
                        source_module="social",
                        event_type="trust_broken",
                        data={
                            "agent_id": agent_id,
                            "old_trust": round(old_trust, 4),
                            "new_trust": round(rel["trust"], 4),
                        },
                        severity=0.8,
                    ))

            elif event.event_type == "separation":
                rel["last_seen_tick"] = tick
                # Separation stress if bonded
                if rel.get("bond_strength", 0.0) > cfg.attachment_threshold:
                    events_out.append(Event(
                        tick=tick,
                        source_module="social",
                        event_type="separation_stress",
                        data={
                            "agent_id": agent_id,
                            "bond_strength": round(rel["bond_strength"], 4),
                        },
                        severity=0.6,
                    ))

            elif event.event_type == "reunion":
                rel["last_seen_tick"] = tick
                # Small trust and attachment boost on reunion
                rel["trust"] = self._clamp(rel["trust"] + cfg.trust_gain_rate * 0.5)
                rel["attachment"] = self._clamp(rel["attachment"] + cfg.trust_gain_rate * 0.3)

            elif event.event_type == "stabilizing_presence":
                # Agent consistently stabilizes system (reduces stress) ->
                # grow attachment and dependency
                magnitude = event.data.get("magnitude", 0.5)
                rel["attachment"] = self._clamp(
                    rel["attachment"] + magnitude * cfg.trust_gain_rate * dt
                )
                rel["dependency"] = self._clamp(
                    rel["dependency"] + magnitude * cfg.trust_gain_rate * 0.5 * dt
                )

        # ---- Check for absent bonded agents -> separation stress ----------
        for agent_id in list(self._graph.successors("self")):
            rel = self._graph["self"][agent_id]
            if agent_id not in present_agents:
                if rel.get("bond_strength", 0.0) > cfg.attachment_threshold:
                    ticks_absent = tick - rel.get("last_seen_tick", 0)
                    if ticks_absent > 0 and ticks_absent % 10 == 0:
                        events_out.append(Event(
                            tick=tick,
                            source_module="social",
                            event_type="separation_stress",
                            data={
                                "agent_id": agent_id,
                                "bond_strength": round(rel["bond_strength"], 4),
                                "ticks_absent": ticks_absent,
                            },
                            severity=min(0.9, 0.4 + ticks_absent * 0.01),
                        ))

        # ---- Update bond strengths and check thresholds -------------------
        for agent_id in list(self._graph.successors("self")):
            rel = self._graph["self"][agent_id]
            old_attachment = rel.get("attachment", 0.0)
            rel["bond_strength"] = self._compute_bond_strength(rel)

            # Attachment formed event
            if (old_attachment < cfg.attachment_threshold
                    and rel["attachment"] >= cfg.attachment_threshold):
                events_out.append(Event(
                    tick=tick,
                    source_module="social",
                    event_type="attachment_formed",
                    data={
                        "agent_id": agent_id,
                        "attachment": round(rel["attachment"], 4),
                        "bond_strength": round(rel["bond_strength"], 4),
                    },
                    severity=0.5,
                ))

        # ---- Aggregate metrics --------------------------------------------
        all_bonds: list[float] = []
        high_attachment_bonds: list[float] = []
        for agent_id in self._graph.successors("self"):
            rel = self._graph["self"][agent_id]
            bs = rel.get("bond_strength", 0.0)
            all_bonds.append(bs)
            if rel.get("attachment", 0.0) >= cfg.attachment_threshold:
                high_attachment_bonds.append(bs)

        s.total_bond_strength = round(sum(all_bonds), 4)

        # Attachment risk: risk of losing high-attachment relationships
        # Based on trust instability in high-attachment relationships
        if high_attachment_bonds:
            risk_factors: list[float] = []
            for agent_id in self._graph.successors("self"):
                rel = self._graph["self"][agent_id]
                if rel.get("attachment", 0.0) >= cfg.attachment_threshold:
                    # Lower trust = higher risk; betrayal history = higher risk
                    trust_risk = 1.0 - rel["trust"]
                    betrayal_risk = min(1.0, rel.get("betrayal_count", 0) * 0.2)
                    absent = agent_id not in present_agents
                    absence_risk = 0.3 if absent else 0.0
                    risk_factors.append(
                        self._clamp(trust_risk * 0.4 + betrayal_risk * 0.3 + absence_risk * 0.3)
                    )
            s.attachment_risk = round(
                sum(risk_factors) / len(risk_factors) if risk_factors else 0.0, 4
            )
        else:
            s.attachment_risk = 0.0

        # ---- Sync relationship dict for serialization ---------------------
        s.relationships = {}
        for agent_id in self._graph.successors("self"):
            s.relationships[agent_id] = dict(self._graph["self"][agent_id])

        state_dict = s.model_dump()
        return ModuleOutput(
            module_name="social",
            tick=tick,
            state=state_dict,
            events=events_out,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        agent_id = event.data.get("agent_id")
        if agent_id is None:
            return
        rel = self._ensure_relationship(agent_id)
        if event.event_type == "trust_gain":
            amount = event.data.get("amount", 1.0)
            gain_factor = 1.0 / (1.0 + rel.get("betrayal_count", 0))
            rel["trust"] = self._clamp(
                rel["trust"] + self._config.trust_gain_rate * amount * gain_factor
            )
        elif event.event_type == "betrayal":
            rel["trust"] = self._clamp(rel["trust"] - self._config.betrayal_impact)
            rel["betrayal_count"] = rel.get("betrayal_count", 0) + 1
