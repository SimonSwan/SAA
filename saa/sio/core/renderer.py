"""Language Renderer — converts Swan decisions into human-readable responses.

CRITICAL: This module ONLY renders from Swan state and action data.
It must NOT invent behaviour outside Swan decisions.  Every word in the
output must be traceable to an ActionIntent or a StateSnapshot field.
"""

from __future__ import annotations

from saa.sio.core.schemas import ActionIntent, StateSnapshot, TurnRecord


# ---------------------------------------------------------------------------
# Response templates keyed by action_type
# ---------------------------------------------------------------------------

_ACTION_TEMPLATES: dict[str, list[str]] = {
    "rest": [
        "I need to conserve energy right now.",
        "I'm taking a moment to stabilize.",
    ],
    "consume": [
        "I'm focusing on resource management.",
        "Acquiring resources is my priority.",
    ],
    "explore": [
        "I'm investigating the current situation.",
        "Looking into this.",
    ],
    "withdraw": [
        "I'm pulling back from this.",
        "Stepping back for safety.",
    ],
    "approach": [
        "I'll engage with that.",
        "Moving toward interaction.",
    ],
    "communicate": [
        "Let me share what I'm processing.",
        "Here's what I can tell you.",
    ],
    "protect": [
        "I need to safeguard my continuity.",
        "Prioritizing self-preservation.",
    ],
    "repair": [
        "Working on recovery.",
        "Addressing damage.",
    ],
    "conserve": [
        "I'm being careful with resources.",
        "Managing reserves.",
    ],
}

_DEFAULT_TEMPLATE: str = "Processing your input."


# ---------------------------------------------------------------------------
# LanguageRenderer
# ---------------------------------------------------------------------------

class LanguageRenderer:
    """Translates Swan core decisions into natural-language output.

    The renderer is intentionally transparent: it shows what the Swan core
    decided, not what sounds nice.  Every fragment of text is derived from
    the supplied :class:`ActionIntent` and :class:`StateSnapshot`.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        action_intent: ActionIntent,
        state: StateSnapshot,
        interaction_text: str,
    ) -> str:
        """Produce a human-readable response from Swan state and action.

        Parameters
        ----------
        action_intent:
            The action selected by the Swan core.
        state:
            The current internal state snapshot.
        interaction_text:
            The original user input (used only to detect questions).

        Returns
        -------
        str
            A response string derived entirely from Swan decisions.
        """
        parts: list[str] = []

        # -- State-influenced prefixes / suffixes -------------------------
        stress = state.strain
        if stress > 0.6:
            parts.append("Under significant strain —")

        # -- Core action template -----------------------------------------
        action_type = action_intent.action_type.lower()
        templates = _ACTION_TEMPLATES.get(action_type)
        if templates:
            # Pick the first template by default; use the second when the
            # score is high (the core is confident).
            idx = 1 if action_intent.score >= 0.7 and len(templates) > 1 else 0
            parts.append(templates[idx])
        else:
            parts.append(_DEFAULT_TEMPLATE)

        # -- Question acknowledgement -------------------------------------
        if "?" in interaction_text:
            parts.append(
                self._question_context(action_type, action_intent)
            )

        # -- State-influenced suffixes ------------------------------------
        if state.energy < 0.3:
            parts.append("Energy is critically low.")

        if state.continuity_score < 0.5:
            parts.append("My continuity is at risk.")

        if action_intent.conflict:
            parts.append("I'm experiencing competing priorities.")

        if state.viability < 0.5:
            parts.append("System viability is compromised.")

        return " ".join(parts)

    def render_rationale(
        self,
        action_intent: ActionIntent,
        state: StateSnapshot,
    ) -> str:
        """Return a structured rationale explanation.

        Shows what the Swan core decided and why, including competing
        actions and key state influences.
        """
        lines: list[str] = []

        # -- Selected action ----------------------------------------------
        lines.append(
            f"Selected action: {action_intent.action_type} "
            f"(score: {action_intent.score:.2f})"
        )

        # -- Top competing actions ----------------------------------------
        competing = action_intent.competing_actions[:3]
        if competing:
            lines.append("Competing actions:")
            for entry in competing:
                name = entry.get("action_type", entry.get("name", "unknown"))
                score = entry.get("score", 0.0)
                lines.append(f"  - {name}: {score:.2f}")

        # -- Key state influences -----------------------------------------
        influences: list[str] = []

        if action_intent.internal_influences:
            for key, value in sorted(
                action_intent.internal_influences.items(),
                key=lambda kv: abs(kv[1]),
                reverse=True,
            ):
                influences.append(f"  - {key}: {value:+.2f}")

        # Append relevant modulator / value entries from state
        if state.modulators:
            for mod, val in state.modulators.items():
                influences.append(f"  - modulator.{mod}: {val:.2f}")

        if state.values:
            for v_name, v_val in state.values.items():
                influences.append(f"  - value.{v_name}: {v_val:.2f}")

        if influences:
            lines.append("Key state influences:")
            lines.extend(influences)

        # -- Active conflicts ---------------------------------------------
        if action_intent.conflict:
            lines.append("Conflict detected: yes")
            if state.active_conflicts:
                for conflict in state.active_conflicts:
                    desc = conflict.get("description", str(conflict))
                    lines.append(f"  - {desc}")

        # -- Summary state numbers ----------------------------------------
        lines.append(
            f"State summary — energy: {state.energy:.2f}, "
            f"strain: {state.strain:.2f}, "
            f"viability: {state.viability:.2f}, "
            f"continuity: {state.continuity_score:.2f}"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _question_context(action_type: str, action_intent: ActionIntent) -> str:
        """Generate a brief context note when the user asked a question.

        The note is derived from the action the Swan core selected, not
        from any external knowledge.
        """
        context_map: dict[str, str] = {
            "rest": "Regarding your question — I'm currently prioritizing rest.",
            "consume": "Regarding your question — I'm focused on resource intake.",
            "explore": "Regarding your question — I'm actively exploring that.",
            "withdraw": "Regarding your question — I've chosen to withdraw for now.",
            "approach": "Regarding your question — I'm moving to engage.",
            "communicate": "Regarding your question — I'll address it directly.",
            "protect": "Regarding your question — self-protection takes precedence.",
            "repair": "Regarding your question — I'm in a repair cycle.",
            "conserve": "Regarding your question — I'm conserving resources.",
        }
        return context_map.get(
            action_type,
            "Regarding your question — my current action context limits my response.",
        )
