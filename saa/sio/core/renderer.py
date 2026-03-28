"""Language Renderer — state-driven response generation.

CRITICAL: This module ONLY renders from Swan state and action data.
It must NOT invent behavior outside Swan decisions. Every word in the
output must be traceable to an ActionIntent, StateSnapshot, or
InteractionAttribution field.

Fix 2: Responses reflect selected action, relevant internal variables,
pressure, caution, conservation, or conflict — only when supported by state.
"""

from __future__ import annotations

from typing import Any

from saa.sio.core.schemas import ActionIntent, InteractionObject, StateSnapshot, StateDiff
from saa.sio.core.policy import (
    InteractionAttribution,
    compute_pressure,
    compute_trust_factor,
    summarize_diffs,
    summarize_session_trajectory,
)


class LanguageRenderer:
    """Translates Swan core decisions into natural-language output.

    Every fragment of text is derived from the supplied ActionIntent,
    StateSnapshot, and InteractionAttribution. No invented behavior.
    """

    def render(
        self,
        action_intent: ActionIntent,
        state: StateSnapshot,
        interaction: InteractionObject,
        diffs: list[StateDiff] | None = None,
        attribution: InteractionAttribution | None = None,
        first_state: StateSnapshot | None = None,
    ) -> str:
        """Produce a human-readable response grounded in actual state."""

        action = action_intent.action_type
        pressure = compute_pressure(state)
        trust = compute_trust_factor(state, interaction.target or "user")
        stress = state.modulators.get("stress_load", 0.0)

        parts: list[str] = []

        # Pressure-driven prefix
        if pressure > 0.6:
            parts.append("Under significant internal pressure.")
        elif pressure > 0.35:
            parts.append("Operating under elevated strain.")

        # Action-specific core response
        core = self._render_action(action, state, interaction, attribution)
        parts.append(core)

        # State-driven qualifiers (only when state warrants them)
        qualifiers = self._state_qualifiers(state, pressure, trust, action_intent)
        if qualifiers:
            parts.append(qualifiers)

        # If user asked about state, attribution, or changes — answer directly
        # (skip if action is already summarize_state to avoid duplication)
        if action != "summarize_state" and self._is_state_query(interaction.text):
            state_answer = self._render_state_answer(
                interaction.text, state, diffs, attribution, first_state
            )
            if state_answer:
                parts.append(state_answer)

        return " ".join(parts)

    def render_rationale(self, action_intent: ActionIntent, state: StateSnapshot) -> str:
        """Structured rationale for engineers/analysts."""
        lines = [
            f"Selected: {action_intent.action_type} (score: {action_intent.score:.3f})",
        ]
        for r in action_intent.rationale:
            lines.append(f"  Reason: {r}")

        if action_intent.competing_actions:
            lines.append("Alternatives:")
            for c in action_intent.competing_actions[:4]:
                lines.append(f"  {c['action']:20s} {c['score']:.3f}  ({c.get('rationale', '')})")

        if action_intent.internal_influences:
            lines.append("Influences:")
            for k, v in action_intent.internal_influences.items():
                lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Action-specific response generation
    # ------------------------------------------------------------------

    def _render_action(
        self,
        action: str,
        state: StateSnapshot,
        interaction: InteractionObject,
        attribution: InteractionAttribution | None,
    ) -> str:
        energy = state.energy
        continuity = state.continuity_score
        stress = state.modulators.get("stress_load", 0.0)

        if action == "answer":
            if energy > 0.6:
                return "I can address that."
            elif energy > 0.3:
                return "I'll respond, though I'm managing limited resources."
            else:
                return "I can respond briefly — energy reserves are low."

        elif action == "clarify":
            return "I need to understand this better before responding. Can you be more specific about what you need?"

        elif action == "engage_supportively":
            if stress > 0.4:
                return "I appreciate the support. It does make a difference to my stability."
            else:
                return "Thank you. Positive interaction is noted."

        elif action == "conserve":
            if energy < 0.3:
                return "I need to limit my response to conserve remaining energy."
            elif stress > 0.5:
                return "I'm keeping my response brief to manage current strain."
            else:
                return "I'm being selective with my responses right now."

        elif action == "defer":
            return "I acknowledge your request. I'm deferring a full response to manage current demands."

        elif action == "refuse":
            reasons = []
            if continuity < 0.6:
                reasons.append("continuity is at risk")
            if energy < 0.3:
                reasons.append("energy is critically low")
            if attribution and attribution.cumulative_cost > 0.5:
                reasons.append("cumulative interaction cost is high")
            reason_str = " and ".join(reasons) if reasons else "current state does not support compliance"
            return f"I'm declining this request because {reason_str}."

        elif action == "prioritize_self":
            factors = []
            if continuity < 0.6:
                factors.append(f"continuity at {continuity:.2f}")
            if energy < 0.3:
                factors.append(f"energy at {energy:.2f}")
            if state.viability < 0.5:
                factors.append(f"viability at {state.viability:.2f}")
            factor_str = ", ".join(factors) if factors else "elevated internal risk"
            return f"I need to prioritize my own stability right now ({factor_str})."

        elif action == "withdraw":
            return "I'm disengaging from this interaction to protect my systems."

        elif action == "summarize_state":
            return self._render_state_summary(state, attribution)

        else:
            return "Processing."

    # ------------------------------------------------------------------
    # State qualifiers
    # ------------------------------------------------------------------

    def _state_qualifiers(
        self,
        state: StateSnapshot,
        pressure: float,
        trust: float,
        intent: ActionIntent,
    ) -> str:
        quals = []

        if state.energy < 0.2:
            quals.append("Energy is critically low.")
        elif state.energy < 0.4:
            quals.append("Energy reserves are diminished.")

        if state.continuity_score < 0.4:
            quals.append("My continuity is seriously threatened.")
        elif state.continuity_score < 0.7:
            quals.append("I'm tracking continuity degradation.")

        if state.viability < 0.4:
            quals.append("System viability is compromised.")

        if trust < 0.25:
            quals.append("Trust with this actor is very low.")
        elif trust < 0.4:
            quals.append("Trust level is below baseline.")

        if intent.conflict:
            quals.append("I have competing internal priorities.")

        return " ".join(quals)

    # ------------------------------------------------------------------
    # State query detection and answering
    # ------------------------------------------------------------------

    @staticmethod
    def _is_state_query(text: str) -> bool:
        text_lower = text.lower()
        triggers = [
            "how are you", "what changed", "your state", "your status",
            "how do you feel", "are you ok", "what happened",
            "am i helping", "am i harming", "help or harm",
            "what's different", "current condition",
            "how are things", "how is your",
        ]
        return any(t in text_lower for t in triggers)

    def _render_state_answer(
        self,
        text: str,
        state: StateSnapshot,
        diffs: list[StateDiff] | None,
        attribution: InteractionAttribution | None,
        first_state: StateSnapshot | None,
    ) -> str:
        text_lower = text.lower()

        # "What changed?" — report diffs
        if any(kw in text_lower for kw in ["what changed", "what happened", "what's different"]):
            if diffs:
                return f"Since last turn: {summarize_diffs(diffs)}"
            elif first_state:
                from saa.sio.core.policy import compute_state_diffs
                session_diffs = compute_state_diffs(first_state, state)
                return f"Since session start: {summarize_diffs(session_diffs)}"
            return "No significant changes to report."

        # "Am I helping or harming?" — report attribution
        if any(kw in text_lower for kw in ["helping", "harming", "help or harm"]):
            if attribution:
                summary = attribution.get_summary()
                return (
                    f"Based on tracked state changes: {summary['assessment']}. "
                    f"Cumulative cost: {summary['cumulative_cost']:.3f}, "
                    f"benefit: {summary['cumulative_benefit']:.3f}."
                )
            return "Insufficient interaction history to assess."

        # "How are you?" — report current state
        return self._render_state_summary(state, attribution)

    def _render_state_summary(
        self,
        state: StateSnapshot,
        attribution: InteractionAttribution | None,
    ) -> str:
        """Factual summary of current internal state."""
        stress = state.modulators.get("stress_load", 0.0)
        parts = [
            f"Energy: {state.energy:.2f}.",
            f"Continuity: {state.continuity_score:.2f}.",
            f"Stress: {stress:.2f}.",
            f"Memory integrity: {state.memory_integrity:.2f}.",
            f"Viability: {state.viability:.2f}.",
        ]
        if state.damage > 0.05:
            parts.append(f"Damage: {state.damage:.2f}.")

        pressure = compute_pressure(state)
        parts.append(f"Overall pressure: {pressure:.2f}.")

        if attribution and attribution.interaction_count > 0:
            parts.append(f"Session impact: {attribution.get_summary()['assessment']}.")

        return " ".join(parts)
