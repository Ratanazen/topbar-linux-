"""
Ratana Dynamic Island — Event Manager
=====================================
Manages event lifecycle, transient event queuing, deduplication, auto-expiration,
and priority arbitration across all active states.
"""

from typing import List, Optional

from core.priority_manager import Priority
from core.state_manager import IslandState


class EventManager:
    """Manages transient state queues and priority-based state arbitration."""

    def __init__(self):
        self.transient_states: List[IslandState] = []

    def push_transient(self, state: IslandState):
        """
        Pushes an auto-expiring event.
        Deduplicates prior events of the same source & state name.
        """
        # Deduplicate
        self.transient_states = [
            s for s in self.transient_states
            if not (s.source == state.source and s.state == state.state)
        ]
        self.transient_states.append(state)

    def dismiss(self, state_name: Optional[str] = None):
        """Dismiss active transient events immediately."""
        if state_name:
            self.transient_states = [s for s in self.transient_states if s.state != state_name]
        else:
            self.transient_states.clear()

    def prune_expired(self) -> List[IslandState]:
        """Removes expired transient states and returns remaining valid states."""
        self.transient_states = [s for s in self.transient_states if not s.is_expired]
        return self.transient_states

    def arbitrate(
        self,
        persistent_states: List[Optional[IslandState]],
        default_idle: IslandState
    ) -> IslandState:
        """
        Determines the current winning IslandState based on the priority matrix.
        Higher priority integer wins. When priorities are equal, the most recently
        created state wins.
        """
        self.prune_expired()

        candidates: List[IslandState] = list(self.transient_states)
        for ps in persistent_states:
            if ps is not None:
                candidates.append(ps)

        if not candidates:
            return default_idle

        # Sort descending by (priority, created_at)
        candidates.sort(key=lambda s: (int(s.priority), s.created_at), reverse=True)
        return candidates[0]
