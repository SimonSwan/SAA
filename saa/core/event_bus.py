"""EventBus — pub/sub for cross-module communication."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from saa.core.types import Event


class EventBus:
    """Simple synchronous pub/sub event bus.

    Modules publish events and subscribe to event types.
    All events are logged for replay and inspection.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Register a callback for a given event type."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Remove a callback for a given event type."""
        subs = self._subscribers.get(event_type, [])
        if callback in subs:
            subs.remove(callback)

    def publish(self, event: Event) -> None:
        """Publish an event, notifying all subscribers and logging it."""
        self._history.append(event)
        for callback in self._subscribers.get(event.event_type, []):
            callback(event)
        # Also notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            callback(event)

    def get_history(self, event_type: str | None = None, since_tick: int = 0) -> list[Event]:
        """Return event history, optionally filtered by type and tick."""
        events = self._history
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        if since_tick > 0:
            events = [e for e in events if e.tick >= since_tick]
        return events

    def clear_history(self) -> None:
        """Clear the event log."""
        self._history.clear()

    @property
    def history(self) -> list[Event]:
        return list(self._history)
