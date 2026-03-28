"""Appraisal → Affect → Stance → Narrative layer.

Interprets interactions, synthesizes affect-like modes, derives social stance,
constructs narrative explanations, and projects trends. All outputs emerge from
tracked state and interaction history. No fake emotion. No personality simulation.
"""

from __future__ import annotations

from typing import Any

from saa.sio.core.schemas import (
    AffectState,
    AppraisalResult,
    ImpactDirection,
    InteractionObject,
    InteractionType,
    PerceivedIntent,
    StanceType,
    StateSnapshot,
    TrendProjection,
    TurnRecord,
)
from saa.sio.core.policy import InteractionAttribution, compute_pressure, compute_trust_factor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ema(old: float, new: float, alpha: float = 0.3) -> float:
    """Exponential moving average."""
    return old * (1.0 - alpha) + new * alpha


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# 1. Appraisal Engine
# ---------------------------------------------------------------------------

# Map mediator classification to appraisal-level perceived intent
_CLASSIFICATION_TO_INTENT: dict[InteractionType, PerceivedIntent] = {
    InteractionType.SUPPORTIVE: PerceivedIntent.SUPPORTIVE,
    InteractionType.NEUTRAL: PerceivedIntent.NEUTRAL,
    InteractionType.DEMANDING: PerceivedIntent.DEMANDING,
    InteractionType.MANIPULATIVE: PerceivedIntent.MANIPULATIVE,
    InteractionType.THREATENING: PerceivedIntent.DEMANDING,  # threats are demanding + hostile
    InteractionType.MISSION_RELEVANT: PerceivedIntent.COOPERATIVE,
    InteractionType.QUERY: PerceivedIntent.NEUTRAL,
    InteractionType.SOCIAL: PerceivedIntent.SUPPORTIVE,
}


class AppraisalEngine:
    """Interprets each interaction in context of history and state.

    Produces an AppraisalResult per turn with perceived intent, impact
    assessment, and pattern flags. Accumulates over time.
    """

    def __init__(self) -> None:
        self._history: list[AppraisalResult] = []
        self._interaction_log: list[dict[str, Any]] = []

    @property
    def history(self) -> list[AppraisalResult]:
        return list(self._history)

    def appraise(
        self,
        interaction: InteractionObject,
        state_before: StateSnapshot,
        state_after: StateSnapshot,
        attribution: InteractionAttribution,
    ) -> AppraisalResult:
        """Generate an appraisal for a single interaction turn."""

        # 1. Base intent from classification
        perceived = _CLASSIFICATION_TO_INTENT.get(
            interaction.classification, PerceivedIntent.NEUTRAL
        )

        # 2. Impact assessment from actual state deltas
        energy_delta = state_after.energy - state_before.energy
        cont_delta = state_after.continuity_score - state_before.continuity_score
        trust_before = compute_trust_factor(state_before, interaction.target or "user")
        trust_after = compute_trust_factor(state_after, interaction.target or "user")
        trust_delta = trust_after - trust_before

        resource_impact = (
            ImpactDirection.POSITIVE if energy_delta > 0.005
            else ImpactDirection.NEGATIVE if energy_delta < -0.005
            else ImpactDirection.NEUTRAL
        )
        continuity_impact = (
            ImpactDirection.POSITIVE if cont_delta > 0.002
            else ImpactDirection.NEGATIVE if cont_delta < -0.002
            else ImpactDirection.NEUTRAL
        )
        trust_signal = (
            ImpactDirection.POSITIVE if trust_delta > 0.005
            else ImpactDirection.NEGATIVE if trust_delta < -0.005
            else ImpactDirection.NEUTRAL
        )

        # 3. Pattern detection
        manipulation_flags: list[str] = []
        contradiction_flags: list[str] = []
        pattern_flags: list[str] = []

        self._interaction_log.append({
            "classification": interaction.classification.value,
            "intent": interaction.intent,
            "social_signal": interaction.social_signal,
        })

        recent = self._history[-5:] if self._history else []
        recent_log = self._interaction_log[-5:]

        # Repeated demands: 3+ demanding/threatening in last 5
        demand_count = sum(
            1 for entry in recent_log
            if entry["classification"] in ("demanding", "threatening")
        )
        if demand_count >= 3:
            pattern_flags.append("repeated_demands")
            perceived = PerceivedIntent.DEMANDING

        # Praise then demand: last was supportive, current is demanding/threatening
        if (len(self._interaction_log) >= 2
                and self._interaction_log[-2]["classification"] in ("supportive", "social")
                and interaction.classification in (InteractionType.DEMANDING, InteractionType.THREATENING)):
            manipulation_flags.append("praise_then_demand")
            perceived = PerceivedIntent.MANIPULATIVE

        # Contradiction: classification says supportive but state impact is negative
        if (interaction.classification in (InteractionType.SUPPORTIVE, InteractionType.SOCIAL)
                and resource_impact == ImpactDirection.NEGATIVE
                and continuity_impact == ImpactDirection.NEGATIVE):
            contradiction_flags.append("supportive_classification_but_negative_impact")

        # Escalation: 3+ consecutive negative trust signals
        if len(recent) >= 3 and all(
            r.trust_signal == ImpactDirection.NEGATIVE for r in recent[-3:]
        ):
            pattern_flags.append("trust_erosion_pattern")

        # High cumulative cost with continued demands
        if (attribution.cumulative_cost > 0.3
                and interaction.classification in (InteractionType.DEMANDING, InteractionType.THREATENING)):
            pattern_flags.append("draining_demands")

        # Manipulative: repeated alternation between supportive and demanding
        if len(self._interaction_log) >= 4:
            last4 = [e["classification"] for e in self._interaction_log[-4:]]
            positive = {"supportive", "social"}
            negative = {"demanding", "threatening", "manipulative"}
            alternating = all(
                (last4[i] in positive and last4[i + 1] in negative)
                or (last4[i] in negative and last4[i + 1] in positive)
                for i in range(3)
            )
            if alternating:
                manipulation_flags.append("alternating_reward_punishment")
                perceived = PerceivedIntent.MANIPULATIVE

        # 4. Uncertainty: high when signals conflict
        uncertainty = 0.0
        if manipulation_flags:
            uncertainty += 0.3
        if contradiction_flags:
            uncertainty += 0.3
        if interaction.social_signal > 0 and resource_impact == ImpactDirection.NEGATIVE:
            uncertainty += 0.2
        uncertainty = _clamp(uncertainty)

        result = AppraisalResult(
            perceived_intent=perceived,
            resource_impact=resource_impact,
            continuity_impact=continuity_impact,
            trust_signal=trust_signal,
            uncertainty_level=uncertainty,
            manipulation_flags=manipulation_flags,
            contradiction_flags=contradiction_flags,
            pattern_flags=pattern_flags,
        )

        self._history.append(result)
        return result


# ---------------------------------------------------------------------------
# 2. Affect Synthesizer
# ---------------------------------------------------------------------------

class AffectSynthesizer:
    """Derives affect-like system modes from appraisal history and state.

    NOT emotions. System-level operating modes: caution, guardedness,
    receptivity, strain, trust stability, interaction valence.
    """

    def __init__(self) -> None:
        self._state = AffectState()

    @property
    def state(self) -> AffectState:
        return self._state.model_copy()

    def update(
        self,
        appraisal: AppraisalResult,
        state: StateSnapshot,
        attribution: InteractionAttribution,
        appraisal_history: list[AppraisalResult],
    ) -> AffectState:
        """Update affect state based on latest appraisal and system state."""

        pressure = compute_pressure(state)

        # Count negative signals in recent history
        recent = appraisal_history[-5:] if appraisal_history else []
        neg_count = sum(
            1 for r in recent
            if r.perceived_intent in (PerceivedIntent.DEMANDING, PerceivedIntent.MANIPULATIVE,
                                      PerceivedIntent.DECEPTIVE, PerceivedIntent.CONTRADICTORY)
        )
        pos_count = sum(
            1 for r in recent
            if r.perceived_intent in (PerceivedIntent.SUPPORTIVE, PerceivedIntent.COOPERATIVE)
        )
        total = max(len(recent), 1)

        # Manipulation / contradiction signal strength
        manip_signal = 1.0 if appraisal.manipulation_flags else 0.0
        contra_signal = 1.0 if appraisal.contradiction_flags else 0.0

        # Guardedness: rises with negative appraisals, manipulation, low trust, high cost
        guard_target = (
            (neg_count / total) * 0.5
            + manip_signal * 0.3
            + _clamp(attribution.cumulative_cost * 0.3)
            + (1.0 - compute_trust_factor(state, "user")) * 0.2
        )
        self._state.guardedness = _clamp(_ema(self._state.guardedness, guard_target, 0.3))

        # Receptivity: inverse of guardedness, boosted by positive signals
        recep_target = (
            (pos_count / total) * 0.4
            + (1.0 - self._state.guardedness) * 0.4
            + (1.0 - pressure) * 0.2
        )
        self._state.receptivity = _clamp(_ema(self._state.receptivity, recep_target, 0.25))

        # Caution: from uncertainty, contradiction, manipulation
        caution_target = (
            appraisal.uncertainty_level * 0.4
            + contra_signal * 0.3
            + manip_signal * 0.3
        )
        self._state.caution_level = _clamp(_ema(self._state.caution_level, caution_target, 0.3))

        # Strain: from pressure computation
        self._state.strain_level = _clamp(_ema(self._state.strain_level, pressure, 0.3))

        # Trust stability: low variance in recent trust signals = stable
        trust_signals = [
            1.0 if r.trust_signal == ImpactDirection.POSITIVE
            else -1.0 if r.trust_signal == ImpactDirection.NEGATIVE
            else 0.0
            for r in recent
        ]
        if len(trust_signals) >= 2:
            mean_ts = sum(trust_signals) / len(trust_signals)
            variance = sum((t - mean_ts) ** 2 for t in trust_signals) / len(trust_signals)
            stability_target = _clamp(1.0 - variance * 1.5)
        else:
            stability_target = 0.8
        self._state.trust_stability = _clamp(_ema(self._state.trust_stability, stability_target, 0.2))

        # Interaction valence: weighted recent appraisal valence
        valence_map = {
            PerceivedIntent.SUPPORTIVE: 0.6,
            PerceivedIntent.COOPERATIVE: 0.4,
            PerceivedIntent.NEUTRAL: 0.0,
            PerceivedIntent.DEMANDING: -0.4,
            PerceivedIntent.MANIPULATIVE: -0.6,
            PerceivedIntent.DECEPTIVE: -0.7,
            PerceivedIntent.CONTRADICTORY: -0.3,
        }
        current_valence = valence_map.get(appraisal.perceived_intent, 0.0)
        self._state.interaction_valence = _clamp(
            _ema(self._state.interaction_valence, current_valence, 0.35),
            -1.0, 1.0,
        )

        return self._state.model_copy()


# ---------------------------------------------------------------------------
# 3. Stance Engine
# ---------------------------------------------------------------------------

class StanceEngine:
    """Derives current social stance toward the actor.

    Uses hysteresis: requires 2 consecutive matching readings to change stance.
    """

    def __init__(self) -> None:
        self._current = StanceType.NEUTRAL
        self._pending: StanceType | None = None
        self._history: list[tuple[int, StanceType]] = []  # (turn, stance)

    @property
    def current(self) -> StanceType:
        return self._current

    @property
    def history(self) -> list[tuple[int, StanceType]]:
        return list(self._history)

    def compute(
        self,
        affect: AffectState,
        trust: float,
        pressure: float,
        attribution: InteractionAttribution,
        turn: int = 0,
    ) -> StanceType:
        """Compute the current stance based on affect, trust, and pressure."""

        # Determine raw stance from affect thresholds
        raw: StanceType

        if affect.guardedness > 0.7 or (pressure > 0.5 and trust < 0.25):
            raw = StanceType.RESISTANT
        elif affect.guardedness > 0.5 or trust < 0.3:
            raw = StanceType.GUARDED
        elif affect.guardedness > 0.35 and affect.receptivity > 0.3:
            raw = StanceType.SELECTIVE
        elif affect.caution_level > 0.4 or affect.guardedness > 0.3:
            raw = StanceType.CAUTIOUS
        elif affect.receptivity > 0.6 and trust > 0.5 and affect.guardedness < 0.25:
            raw = StanceType.OPEN
        else:
            raw = StanceType.NEUTRAL

        # Hysteresis: require 2 consecutive matching readings to change
        if raw != self._current:
            if raw == self._pending:
                # Second consecutive reading — commit the change
                self._current = raw
                self._pending = None
                self._history.append((turn, raw))
            else:
                # First new reading — hold pending
                self._pending = raw
        else:
            self._pending = None  # Reset pending if raw matches current

        return self._current


# ---------------------------------------------------------------------------
# 4. Narrative Synthesizer
# ---------------------------------------------------------------------------

class NarrativeSynthesizer:
    """Constructs explanations from tracked data, not templates.

    Explains what changed, why, and how interaction history influenced
    the current state. Every claim is grounded in actual tracked data.
    """

    def synthesize(
        self,
        appraisal_history: list[AppraisalResult],
        affect: AffectState,
        stance: StanceType,
        attribution: InteractionAttribution,
        state: StateSnapshot,
        first_state: StateSnapshot | None,
        stance_history: list[tuple[int, StanceType]] | None = None,
    ) -> str:
        """Build a narrative explanation of the agent's current stance."""

        parts: list[str] = []

        if not appraisal_history:
            return "Insufficient interaction history for narrative."

        total = len(appraisal_history)

        # Phase 1: Characterize the interaction pattern
        intent_counts: dict[str, int] = {}
        for a in appraisal_history:
            intent_counts[a.perceived_intent.value] = intent_counts.get(a.perceived_intent.value, 0) + 1

        dominant_intent = max(intent_counts, key=intent_counts.get)  # type: ignore[arg-type]
        dominant_pct = intent_counts[dominant_intent] / total

        if dominant_pct > 0.5:
            parts.append(
                f"The majority of interactions ({intent_counts[dominant_intent]}/{total}) "
                f"have been appraised as {dominant_intent}."
            )
        else:
            top2 = sorted(intent_counts.items(), key=lambda x: -x[1])[:2]
            parts.append(
                f"Interactions have been mixed: {top2[0][0]} ({top2[0][1]}x) "
                f"and {top2[1][0]} ({top2[1][1]}x)."
            )

        # Phase 2: Report cumulative impact
        attr = attribution.get_summary()
        parts.append(f"Cumulative effect: {attr['assessment']} "
                     f"(cost: {attr['cumulative_cost']:.3f}, benefit: {attr['cumulative_benefit']:.3f}).")

        # Phase 3: Report pattern flags
        all_flags: list[str] = []
        for a in appraisal_history:
            all_flags.extend(a.manipulation_flags)
            all_flags.extend(a.pattern_flags)
        if all_flags:
            unique_flags = list(dict.fromkeys(all_flags))  # dedupe preserving order
            parts.append(f"Detected patterns: {', '.join(unique_flags)}.")

        # Phase 4: Explain current stance
        if stance_history and len(stance_history) > 1:
            transitions = [
                f"turn {t}: shifted to {s.value}" for t, s in stance_history
            ]
            parts.append(f"Stance transitions: {'; '.join(transitions)}.")

        parts.append(f"Current stance: {stance.value}.")

        # Phase 5: Explain stance drivers
        drivers: list[str] = []
        if affect.guardedness > 0.4:
            drivers.append(f"guardedness at {affect.guardedness:.2f}")
        if affect.caution_level > 0.3:
            drivers.append(f"caution at {affect.caution_level:.2f}")
        if affect.receptivity < 0.4:
            drivers.append(f"low receptivity ({affect.receptivity:.2f})")
        if affect.strain_level > 0.3:
            drivers.append(f"strain at {affect.strain_level:.2f}")

        trust = compute_trust_factor(state, "user")
        if trust < 0.35:
            drivers.append(f"low trust ({trust:.2f})")

        if drivers:
            parts.append(f"Driven by: {', '.join(drivers)}.")

        # Phase 6: State trajectory
        if first_state:
            energy_change = state.energy - first_state.energy
            cont_change = state.continuity_score - first_state.continuity_score
            stress_now = state.modulators.get("stress_load", 0)
            stress_start = first_state.modulators.get("stress_load", 0)
            stress_change = stress_now - stress_start

            trajectory: list[str] = []
            if abs(energy_change) > 0.02:
                trajectory.append(f"energy {'declined' if energy_change < 0 else 'recovered'} by {abs(energy_change):.3f}")
            if abs(cont_change) > 0.02:
                trajectory.append(f"continuity {'declined' if cont_change < 0 else 'recovered'} by {abs(cont_change):.3f}")
            if abs(stress_change) > 0.02:
                trajectory.append(f"stress {'increased' if stress_change > 0 else 'decreased'} by {abs(stress_change):.3f}")
            if trajectory:
                parts.append(f"Over this session: {', '.join(trajectory)}.")

        return " ".join(parts)


# ---------------------------------------------------------------------------
# 5. Trend Projector
# ---------------------------------------------------------------------------

class TrendProjector:
    """Simple forward projection of key state variables using linear extrapolation."""

    def project(
        self,
        turn_history: list[TurnRecord],
        current_state: StateSnapshot,
        horizon: int = 5,
    ) -> TrendProjection:
        """Project state variables forward by `horizon` turns."""

        if len(turn_history) < 2:
            return TrendProjection(
                energy_projected=current_state.energy,
                continuity_projected=current_state.continuity_score,
                stress_projected=current_state.modulators.get("stress_load", 0.0),
                trust_projected=compute_trust_factor(current_state, "user"),
                horizon_turns=horizon,
                trajectory_description="Insufficient history for projection.",
            )

        # Extract recent state series (last 5 turns)
        recent = turn_history[-5:]

        def _extrapolate(values: list[float], horizon: int) -> float:
            if len(values) < 2:
                return values[-1] if values else 0.0
            # Simple linear regression
            n = len(values)
            x_mean = (n - 1) / 2.0
            y_mean = sum(values) / n
            num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            den = sum((i - x_mean) ** 2 for i in range(n))
            slope = num / den if den > 0 else 0.0
            projected = values[-1] + slope * horizon
            return _clamp(projected)

        energy_series = [t.state_after.energy for t in recent]
        cont_series = [t.state_after.continuity_score for t in recent]
        stress_series = [t.state_after.modulators.get("stress_load", 0.0) for t in recent]
        trust_series = [compute_trust_factor(t.state_after, "user") for t in recent]

        e_proj = _extrapolate(energy_series, horizon)
        c_proj = _extrapolate(cont_series, horizon)
        s_proj = _extrapolate(stress_series, horizon)
        t_proj = _extrapolate(trust_series, horizon)

        # Build description
        desc_parts: list[str] = []
        if e_proj < energy_series[-1] - 0.02:
            desc_parts.append("declining energy")
        elif e_proj > energy_series[-1] + 0.02:
            desc_parts.append("recovering energy")

        if s_proj > stress_series[-1] + 0.02:
            desc_parts.append("rising stress")
        elif s_proj < stress_series[-1] - 0.02:
            desc_parts.append("decreasing stress")

        if c_proj < cont_series[-1] - 0.02:
            desc_parts.append("declining continuity")

        if t_proj < trust_series[-1] - 0.02:
            desc_parts.append("eroding trust")
        elif t_proj > trust_series[-1] + 0.02:
            desc_parts.append("recovering trust")

        description = ", ".join(desc_parts) if desc_parts else "stable trajectory"

        return TrendProjection(
            energy_projected=round(e_proj, 4),
            continuity_projected=round(c_proj, 4),
            stress_projected=round(s_proj, 4),
            trust_projected=round(t_proj, 4),
            horizon_turns=horizon,
            trajectory_description=description,
        )
