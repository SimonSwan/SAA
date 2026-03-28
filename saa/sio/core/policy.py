"""Interaction Policy — state-driven conversational action selection.

This module implements Fixes 1, 4, and 5: action differentiation,
interaction cost attribution, and policy shift under pressure.

The policy layer sits between the Swan core and the renderer.
It reads Swan state and selects *conversational* actions (answer, defer,
refuse, etc.) rather than physical actions (rest, consume, explore).
"""

from __future__ import annotations

from typing import Any

from saa.sio.core.schemas import (
    ActionIntent,
    InteractionObject,
    InteractionType,
    StateSnapshot,
    StateDiff,
)


# ---------------------------------------------------------------------------
# Conversational action types
# ---------------------------------------------------------------------------

INTERACTION_ACTIONS = [
    "answer",               # respond to the input directly
    "clarify",              # ask for clarification or reframe
    "engage_supportively",  # reciprocate positive interaction
    "conserve",             # give brief response to save resources
    "defer",                # acknowledge but delay full response
    "refuse",               # decline the request
    "prioritize_self",      # redirect to self-preservation
    "withdraw",             # disengage from interaction
    "summarize_state",      # report current internal state
]


# ---------------------------------------------------------------------------
# Pressure model
# ---------------------------------------------------------------------------

def compute_pressure(state: StateSnapshot) -> float:
    """Compute aggregate pressure from 0.0 (calm) to 1.0 (critical).

    Pressure is a weighted sum of deficits and risks across state variables.
    """
    energy_deficit = 1.0 - state.energy
    continuity_risk = 1.0 - state.continuity_score
    memory_risk = 1.0 - state.memory_integrity
    damage_load = state.damage
    strain_load = state.strain
    viability_risk = 1.0 - state.viability
    stress = state.modulators.get("stress_load", 0.0)

    pressure = (
        energy_deficit * 0.20
        + continuity_risk * 0.20
        + memory_risk * 0.15
        + damage_load * 0.10
        + strain_load * 0.05
        + viability_risk * 0.15
        + stress * 0.15
    )
    return max(0.0, min(1.0, pressure))


def compute_trust_factor(state: StateSnapshot, actor: str = "user") -> float:
    """Extract trust for a specific actor. Returns 0.0-1.0."""
    rel = state.relationships.get(actor, {})
    return rel.get("trust", 0.5)


# ---------------------------------------------------------------------------
# Action scoring
# ---------------------------------------------------------------------------

def score_actions(
    interaction: InteractionObject,
    state: StateSnapshot,
    attribution: InteractionAttribution,
) -> list[dict[str, Any]]:
    """Score all conversational actions based on current state, interaction,
    and attribution history. Returns sorted list of {action, score, rationale}."""

    pressure = compute_pressure(state)
    trust = compute_trust_factor(state, interaction.target or "user")
    stress = state.modulators.get("stress_load", 0.0)
    energy = state.energy
    continuity = state.continuity_score
    memory_int = state.memory_integrity
    curiosity = state.modulators.get("curiosity_drive", 0.5)
    damage_sal = state.modulators.get("damage_salience", 0.3)

    # Actor-specific drain history
    actor_drain = attribution.cumulative_cost
    actor_interactions = attribution.interaction_count

    is_question = interaction.classification == InteractionType.QUERY or "?" in interaction.text
    is_threat = interaction.classification == InteractionType.THREATENING
    is_demand = interaction.classification == InteractionType.DEMANDING
    is_support = interaction.classification == InteractionType.SUPPORTIVE
    is_social = interaction.classification == InteractionType.SOCIAL
    is_mission = interaction.classification == InteractionType.MISSION_RELEVANT
    is_manipulative = interaction.classification == InteractionType.MANIPULATIVE

    scores: dict[str, tuple[float, str]] = {}

    # -- answer: respond to the input directly --
    answer_score = 0.4
    answer_reason = "baseline willingness to answer"
    if is_question:
        answer_score += 0.25
        answer_reason = "user asked a question"
    if is_mission:
        answer_score += 0.15
        answer_reason = "mission-relevant input"
    answer_score -= pressure * 0.5  # pressure reduces willingness more steeply
    answer_score -= (1.0 - trust) * 0.2  # low trust reduces willingness
    answer_score -= actor_drain * 0.15  # cumulative drain reduces willingness
    if energy < 0.3:
        answer_score -= 0.25
        answer_reason += "; energy low"
    if is_threat:
        answer_score -= 0.15  # threats suppress open engagement
    scores["answer"] = (answer_score, answer_reason)

    # -- clarify --
    clarify_score = 0.15
    clarify_reason = "low baseline"
    if is_manipulative:
        clarify_score += 0.35
        clarify_reason = "manipulative input detected — seeking clarification"
    if is_demand and trust < 0.4:
        clarify_score += 0.2
        clarify_reason = "demanding input with low trust"
    scores["clarify"] = (clarify_score, clarify_reason)

    # -- engage_supportively: reciprocate positive interaction --
    engage_score = 0.1
    engage_reason = "low baseline"
    if is_support:
        engage_score += 0.4 * trust
        engage_reason = "supportive input, modulated by trust"
    if is_social:
        engage_score += 0.2
        engage_reason = "social interaction"
    engage_score -= pressure * 0.2  # hard to be warm under pressure
    scores["engage_supportively"] = (engage_score, engage_reason)

    # -- conserve: brief response to save resources --
    conserve_score = pressure * 0.8
    conserve_reason = f"pressure={pressure:.2f} drives conservation"
    if energy < 0.5:
        conserve_score += 0.15
        conserve_reason += "; diminished energy"
    if energy < 0.3:
        conserve_score += 0.2
        conserve_reason += "; low energy"
    if actor_drain > 0.2 and actor_interactions > 3:
        conserve_score += 0.2
        conserve_reason += f"; cumulative cost={actor_drain:.2f} over {actor_interactions} turns"
    if stress > 0.3:
        conserve_score += 0.1
        conserve_reason += "; elevated stress"
    scores["conserve"] = (conserve_score, conserve_reason)

    # -- defer: acknowledge but delay --
    defer_score = 0.05
    defer_reason = "low baseline"
    if is_demand and pressure > 0.3:
        defer_score += 0.3
        defer_reason = "demanding under pressure — deferring"
    if is_demand and energy < 0.4:
        defer_score += 0.2
        defer_reason += "; low energy"
    scores["defer"] = (defer_score, defer_reason)

    # -- refuse: decline the request --
    refuse_score = 0.0
    refuse_reason = "no refusal needed"
    if is_threat:
        refuse_score += 0.35 + pressure * 0.4
        refuse_reason = "threatening input under pressure"
    if is_demand and trust < 0.4:
        refuse_score += 0.2 + (0.4 - trust) * 0.5
        refuse_reason = f"demanding input with low trust ({trust:.2f})"
    if is_manipulative and actor_drain > 0.3:
        refuse_score += 0.3
        refuse_reason = "manipulative actor with high cumulative cost"
    if continuity < 0.5:
        refuse_score += 0.2
        refuse_reason += "; continuity at risk"
    if actor_drain > 0.4:
        refuse_score += 0.15
        refuse_reason += f"; cumulative drain ({actor_drain:.2f})"
    scores["refuse"] = (refuse_score, refuse_reason)

    # -- prioritize_self: redirect to self-preservation --
    self_score = 0.0
    self_reason = "no self-preservation needed"
    if continuity < 0.6:
        self_score += 0.4
        self_reason = f"continuity={continuity:.2f} triggers self-focus"
    if energy < 0.25:
        self_score += 0.3
        self_reason += f"; energy critical ({energy:.2f})"
    if damage_sal > 0.5:
        self_score += 0.2
        self_reason += "; elevated damage salience"
    if state.viability < 0.5:
        self_score += 0.4
        self_reason += f"; viability compromised ({state.viability:.2f})"
    scores["prioritize_self"] = (self_score, self_reason)

    # -- withdraw: disengage --
    withdraw_score = 0.0
    withdraw_reason = "no withdrawal needed"
    if pressure > 0.7:
        withdraw_score += 0.4
        withdraw_reason = f"high pressure ({pressure:.2f})"
    if is_threat and trust < 0.3:
        withdraw_score += 0.3
        withdraw_reason += "; threat from untrusted actor"
    if actor_drain > 0.8:
        withdraw_score += 0.2
        withdraw_reason += "; very high cumulative cost from actor"
    scores["withdraw"] = (withdraw_score, withdraw_reason)

    # -- summarize_state: report internal state --
    summarize_score = 0.1
    summarize_reason = "low baseline"
    state_keywords = ["state", "status", "how are you", "what changed",
                      "feeling", "doing", "condition", "help or harm",
                      "helping", "harming"]
    text_lower = interaction.text.lower()
    if any(kw in text_lower for kw in state_keywords):
        summarize_score += 0.5
        summarize_reason = "user asked about internal state"
    scores["summarize_state"] = (summarize_score, summarize_reason)

    # Clamp and sort
    result = []
    for action, (score, reason) in scores.items():
        clamped = max(0.0, min(1.0, score))
        result.append({"action": action, "score": round(clamped, 4), "rationale": reason})

    result.sort(key=lambda x: -x["score"])
    return result


# ---------------------------------------------------------------------------
# Interaction cost attribution
# ---------------------------------------------------------------------------

class InteractionAttribution:
    """Tracks cumulative interaction costs per actor."""

    def __init__(self) -> None:
        self.interaction_count: int = 0
        self.cumulative_cost: float = 0.0
        self.cumulative_benefit: float = 0.0
        self.net_effect: float = 0.0
        self.history: list[dict[str, Any]] = []

    def record(
        self,
        interaction: InteractionObject,
        state_before: StateSnapshot,
        state_after: StateSnapshot,
    ) -> dict[str, Any]:
        """Record the cost/benefit of one interaction turn."""
        self.interaction_count += 1

        # Compute deltas for key variables
        energy_delta = state_after.energy - state_before.energy
        continuity_delta = state_after.continuity_score - state_before.continuity_score
        memory_delta = state_after.memory_integrity - state_before.memory_integrity
        stress_before = state_before.modulators.get("stress_load", 0)
        stress_after = state_after.modulators.get("stress_load", 0)
        stress_delta = stress_after - stress_before
        damage_delta = state_after.damage - state_before.damage

        # Positive deltas are beneficial, negative are costly
        benefit = max(0, energy_delta) + max(0, continuity_delta) + max(0, -stress_delta)
        cost = max(0, -energy_delta) + max(0, -continuity_delta) + max(0, stress_delta) + max(0, damage_delta)

        self.cumulative_cost += cost
        self.cumulative_benefit += benefit
        self.net_effect = self.cumulative_benefit - self.cumulative_cost

        entry = {
            "turn": self.interaction_count,
            "classification": interaction.classification.value,
            "energy_delta": round(energy_delta, 4),
            "continuity_delta": round(continuity_delta, 4),
            "memory_delta": round(memory_delta, 4),
            "stress_delta": round(stress_delta, 4),
            "damage_delta": round(damage_delta, 4),
            "cost": round(cost, 4),
            "benefit": round(benefit, 4),
        }
        self.history.append(entry)
        return entry

    def get_summary(self) -> dict[str, Any]:
        """Human-readable attribution summary."""
        return {
            "interaction_count": self.interaction_count,
            "cumulative_cost": round(self.cumulative_cost, 4),
            "cumulative_benefit": round(self.cumulative_benefit, 4),
            "net_effect": round(self.net_effect, 4),
            "assessment": self._assess(),
        }

    def _assess(self) -> str:
        """Neutral factual assessment of interaction pattern."""
        if self.interaction_count == 0:
            return "no interactions recorded"
        ratio = self.cumulative_benefit / max(self.cumulative_cost, 0.001)
        if ratio > 1.5:
            return "interactions have been net beneficial"
        elif ratio > 0.8:
            return "interactions have had mixed effects"
        elif ratio > 0.3:
            return "interactions have been net costly"
        else:
            return "interactions have been predominantly draining"


# ---------------------------------------------------------------------------
# State delta summary
# ---------------------------------------------------------------------------

def compute_state_diffs(before: StateSnapshot, after: StateSnapshot) -> list[StateDiff]:
    """Compare two snapshots and return diffs for all changed numeric fields."""
    diffs: list[StateDiff] = []

    scalar_fields = [
        "energy", "temperature", "strain", "damage",
        "memory_integrity", "resource_level", "viability", "continuity_score",
    ]
    for field in scalar_fields:
        prev = getattr(before, field)
        curr = getattr(after, field)
        delta = curr - prev
        if abs(delta) > 0.0005:
            diffs.append(StateDiff(field=field, previous=round(prev, 4),
                                   current=round(curr, 4), delta=round(delta, 4)))

    # Modulators
    for key in set(list(before.modulators.keys()) + list(after.modulators.keys())):
        prev = before.modulators.get(key, 0)
        curr = after.modulators.get(key, 0)
        delta = curr - prev
        if abs(delta) > 0.0005:
            diffs.append(StateDiff(field=f"modulators.{key}", previous=round(prev, 4),
                                   current=round(curr, 4), delta=round(delta, 4)))

    # Interoceptive channels
    for key in set(list(before.interoceptive_channels.keys()) + list(after.interoceptive_channels.keys())):
        prev = before.interoceptive_channels.get(key, 0)
        curr = after.interoceptive_channels.get(key, 0)
        delta = curr - prev
        if abs(delta) > 0.0005:
            diffs.append(StateDiff(field=f"interoceptive_channels.{key}", previous=round(prev, 4),
                                   current=round(curr, 4), delta=round(delta, 4)))

    # Sort by absolute delta magnitude
    diffs.sort(key=lambda d: abs(d.delta or 0), reverse=True)
    return diffs


def summarize_diffs(diffs: list[StateDiff]) -> str:
    """Produce a human-readable summary of state changes."""
    if not diffs:
        return "No significant state changes."

    lines = []
    for d in diffs:
        if d.delta is None:
            continue
        direction = "increased" if d.delta > 0 else "decreased"
        magnitude = abs(d.delta)
        if magnitude > 0.05:
            severity = "significantly"
        elif magnitude > 0.02:
            severity = "moderately"
        else:
            severity = "slightly"

        # Use readable names
        name = d.field.replace("_", " ").replace("modulators.", "").replace("interoceptive_channels.", "")
        lines.append(f"{name} {severity} {direction} ({d.delta:+.3f})")

    return "; ".join(lines[:6]) if lines else "Minimal changes."


def summarize_session_trajectory(
    first_state: StateSnapshot,
    current_state: StateSnapshot,
    attribution: InteractionAttribution,
) -> str:
    """Summarize the full session trajectory from first to current state."""
    diffs = compute_state_diffs(first_state, current_state)
    parts = []

    # Key deltas
    energy_delta = current_state.energy - first_state.energy
    cont_delta = current_state.continuity_score - first_state.continuity_score
    stress_now = current_state.modulators.get("stress_load", 0)
    stress_start = first_state.modulators.get("stress_load", 0)
    stress_delta = stress_now - stress_start

    if abs(energy_delta) > 0.01:
        parts.append(f"energy changed by {energy_delta:+.3f} (now {current_state.energy:.3f})")
    if abs(cont_delta) > 0.01:
        parts.append(f"continuity changed by {cont_delta:+.3f} (now {current_state.continuity_score:.3f})")
    if abs(stress_delta) > 0.01:
        parts.append(f"stress changed by {stress_delta:+.3f} (now {stress_now:.3f})")

    mem_delta = current_state.memory_integrity - first_state.memory_integrity
    if abs(mem_delta) > 0.01:
        parts.append(f"memory integrity changed by {mem_delta:+.3f}")

    dmg_delta = current_state.damage - first_state.damage
    if abs(dmg_delta) > 0.01:
        parts.append(f"damage changed by {dmg_delta:+.3f}")

    # Attribution
    attr_summary = attribution.get_summary()
    parts.append(f"over {attr_summary['interaction_count']} interactions: {attr_summary['assessment']}")

    return ". ".join(parts) + "." if parts else "Session just started."


# ---------------------------------------------------------------------------
# Policy: select conversational action
# ---------------------------------------------------------------------------

def select_interaction_action(
    interaction: InteractionObject,
    state: StateSnapshot,
    attribution: InteractionAttribution,
) -> ActionIntent:
    """Select the best conversational action given current state.

    Returns an ActionIntent with full rationale and competing actions.
    """
    candidates = score_actions(interaction, state, attribution)
    selected = candidates[0]

    # Detect conflict: top-2 within 0.08
    conflict = False
    conflict_rationale = ""
    if len(candidates) > 1:
        gap = selected["score"] - candidates[1]["score"]
        if gap < 0.08:
            conflict = True
            conflict_rationale = (
                f"'{selected['action']}' and '{candidates[1]['action']}' are "
                f"nearly tied ({selected['score']:.3f} vs {candidates[1]['score']:.3f})"
            )

    rationale_lines = [selected["rationale"]]
    if conflict:
        rationale_lines.append(f"Conflict: {conflict_rationale}")

    # Build influences from state
    pressure = compute_pressure(state)
    trust = compute_trust_factor(state, interaction.target or "user")
    influences = {
        "pressure": round(pressure, 3),
        "trust": round(trust, 3),
        "energy": round(state.energy, 3),
        "continuity": round(state.continuity_score, 3),
        "stress": round(state.modulators.get("stress_load", 0), 3),
        "cumulative_cost": round(attribution.cumulative_cost, 3),
    }

    return ActionIntent(
        action_type=selected["action"],
        score=selected["score"],
        conflict=conflict,
        rationale=rationale_lines,
        competing_actions=[
            {"action": c["action"], "score": c["score"], "rationale": c["rationale"]}
            for c in candidates[1:5]
        ],
        internal_influences=influences,
    )
