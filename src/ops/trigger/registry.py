"""TriggerRegistry — maps trigger names to factory functions."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List

from ops.error import TriggerError
from ops.trigger.trigger import Trigger

_log = logging.getLogger(__name__)

TriggerFactory = Callable[[], Trigger]


class TriggerRegistry:
    """Registry for trigger factories."""

    def __init__(self) -> None:
        self._factories: Dict[str, TriggerFactory] = {}

    def set(self, factory: TriggerFactory) -> None:
        """Register a trigger factory. Raises TriggerError if already registered."""
        temp = factory()
        name = temp.name()
        if name in self._factories:
            raise TriggerError(f"Trigger type {name} is already registered")
        _log.info("Registered trigger %s", name)
        self._factories[name] = factory

    def spawn(self, trigger_name: str) -> Trigger:
        """Create a trigger instance by name. Raises ValueError if not found."""
        factory = self._factories.get(trigger_name)
        if factory is None:
            raise ValueError(
                f"No trigger registered for trigger name: {trigger_name}, "
                f"Registered triggers: {self.list_names()}"
            )
        return factory()

    def spawn_all(self) -> List[Trigger]:
        """Create all registered triggers."""
        return [factory() for factory in self._factories.values()]

    def list_names(self) -> List[str]:
        """Return all registered trigger names."""
        return list(self._factories.keys())

    def list(self) -> List[str]:
        """Alias for list_names."""
        return self.list_names()

    def is_set(self, trigger_name: str) -> bool:
        """Check if a trigger is registered."""
        return trigger_name in self._factories

    def unregister(self, trigger_name: str) -> bool:
        """Remove a trigger. Returns True if it was found and removed."""
        if trigger_name in self._factories:
            del self._factories[trigger_name]
            return True
        return False

    def __repr__(self) -> str:
        return f"TriggerRegistry(triggers={self.list_names()})"
