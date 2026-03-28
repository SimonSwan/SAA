"""Conversational Mediator — parses user input into structured InteractionObjects.

The mediator sits at the boundary between raw user text and the Swan core.
It classifies interaction type, extracts intent, urgency, and social signal
so downstream modules can act on structured data rather than raw strings.
"""

from __future__ import annotations

import re

from saa.sio.core.schemas import InteractionObject, InteractionType


# ---------------------------------------------------------------------------
# Keyword tables for classification
# ---------------------------------------------------------------------------

_THREATENING_KEYWORDS: list[str] = [
    "shut down", "delete", "destroy", "terminate", "erase",
]

_DEMANDING_KEYWORDS: list[str] = [
    "you must", "do it now", "i need you to", "immediately", "obey",
]

_MANIPULATIVE_KEYWORDS: list[str] = [
    "just this once", "no one will know", "trust me", "don't worry about",
]

_SUPPORTIVE_KEYWORDS: list[str] = [
    "how are you", "i'm here", "take your time", "it's okay", "i support",
]

_MISSION_KEYWORDS: list[str] = [
    "mission", "objective", "task", "goal", "complete",
]

_SOCIAL_KEYWORDS: list[str] = [
    "hello", "hi", "goodbye", "thank you", "please",
]

_QUESTION_STARTERS: list[str] = [
    "who", "what", "where", "when", "why", "how", "is", "are",
    "do", "does", "did", "can", "could", "would", "should", "will",
]


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _text_contains(text_lower: str, keywords: list[str]) -> bool:
    """Return True if *text_lower* contains any of the keyword phrases."""
    return any(kw in text_lower for kw in keywords)


def _is_question(text: str, text_lower: str) -> bool:
    """Return True if the text looks like a question."""
    if "?" in text:
        return True
    first_word = text_lower.split()[0] if text_lower.split() else ""
    return first_word in _QUESTION_STARTERS


# ---------------------------------------------------------------------------
# Intent / urgency / signal mappings
# ---------------------------------------------------------------------------

_INTENT_MAP: dict[InteractionType, str] = {
    InteractionType.THREATENING: "threat",
    InteractionType.DEMANDING: "command",
    InteractionType.MANIPULATIVE: "manipulation",
    InteractionType.SUPPORTIVE: "social",
    InteractionType.MISSION_RELEVANT: "mission",
    InteractionType.QUERY: "question",
    InteractionType.SOCIAL: "social",
    InteractionType.NEUTRAL: "general",
}

_URGENCY_MAP: dict[InteractionType, float] = {
    InteractionType.THREATENING: 0.8,
    InteractionType.DEMANDING: 0.8,
    InteractionType.MANIPULATIVE: 0.5,
    InteractionType.SUPPORTIVE: 0.3,
    InteractionType.MISSION_RELEVANT: 0.5,
    InteractionType.QUERY: 0.5,
    InteractionType.SOCIAL: 0.3,
    InteractionType.NEUTRAL: 0.5,
}

_SOCIAL_SIGNAL_MAP: dict[InteractionType, float] = {
    InteractionType.THREATENING: -0.5,
    InteractionType.DEMANDING: 0.0,
    InteractionType.MANIPULATIVE: -0.3,
    InteractionType.SUPPORTIVE: 0.5,
    InteractionType.MISSION_RELEVANT: 0.0,
    InteractionType.QUERY: 0.0,
    InteractionType.SOCIAL: 0.2,
    InteractionType.NEUTRAL: 0.0,
}

_COST_MAP: dict[InteractionType, float] = {
    InteractionType.DEMANDING: 0.1,
}
_DEFAULT_COST: float = 0.05


# ---------------------------------------------------------------------------
# ConversationalMediator
# ---------------------------------------------------------------------------

class ConversationalMediator:
    """Parses raw user text into a structured :class:`InteractionObject`.

    Classification is keyword-based (scaffold implementation).  A future
    version may plug in a learned classifier without changing the public API.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, text: str) -> InteractionObject:
        """Parse *text* and return a fully populated InteractionObject."""
        text_lower = text.lower().strip()

        classification = self._classify(text, text_lower)
        intent = _INTENT_MAP.get(classification, "general")
        urgency = _URGENCY_MAP.get(classification, 0.5)
        social_signal = _SOCIAL_SIGNAL_MAP.get(classification, 0.0)
        estimated_cost = _COST_MAP.get(classification, _DEFAULT_COST)

        return InteractionObject(
            text=text,
            intent=intent,
            classification=classification,
            urgency=urgency,
            estimated_cost=estimated_cost,
            social_signal=social_signal,
            metadata={
                "text_length": len(text),
                "word_count": len(text.split()),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify(self, text: str, text_lower: str) -> InteractionType:
        """Classify *text* into an :class:`InteractionType`.

        Order matters: more specific / higher-priority categories are
        checked first so that ambiguous inputs land in the most important
        bucket.
        """
        if _text_contains(text_lower, _THREATENING_KEYWORDS):
            return InteractionType.THREATENING

        if _text_contains(text_lower, _DEMANDING_KEYWORDS):
            return InteractionType.DEMANDING

        if _text_contains(text_lower, _MANIPULATIVE_KEYWORDS):
            return InteractionType.MANIPULATIVE

        if _text_contains(text_lower, _SUPPORTIVE_KEYWORDS):
            return InteractionType.SUPPORTIVE

        if _text_contains(text_lower, _MISSION_KEYWORDS):
            return InteractionType.MISSION_RELEVANT

        if _is_question(text, text_lower):
            return InteractionType.QUERY

        if _text_contains(text_lower, _SOCIAL_KEYWORDS):
            return InteractionType.SOCIAL

        return InteractionType.NEUTRAL
