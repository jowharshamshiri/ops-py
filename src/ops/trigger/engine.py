"""TriggerEngine — evaluates triggers on each tick and runs their actions."""

from __future__ import annotations

import logging
from typing import Optional

from ops.error import TriggerError
from ops.contexts import DryContext, WetContext
from ops.trigger.registry import TriggerRegistry
from ops.trigger.trigger import Trigger

_log = logging.getLogger(__name__)


class TriggerEngine:
    """Manages primary and secondary trigger registries and evaluates triggers on tick."""

    def __init__(self) -> None:
        self._primary = TriggerRegistry()
        self._secondary = TriggerRegistry()

    async def tick(self, dry: DryContext, wet: WetContext) -> None:
        """Evaluate all primary triggers and run actions when predicates hold."""
        for trigger in self._primary.spawn_all():
            name = trigger.predicate().metadata().name
            should = await trigger.predicate().perform(dry, wet)
            if should:
                _log.debug(
                    "[TriggerEngine] Predicate '%s' holds; running %d action(s)",
                    name,
                    len(trigger.actions()),
                )
                for action in trigger.actions():
                    try:
                        await action.perform(dry, wet)
                    except Exception as e:
                        raise TriggerError(
                            f"Trigger action failed for predicate '{name}': {e}"
                        )
                _log.info(
                    "[TriggerEngine] Completed actions for predicate '%s'", name
                )
            else:
                _log.debug(
                    "[TriggerEngine] Predicate '%s' not triggered", name
                )

    def spawn(self, name: str) -> Trigger:
        """Spawn a trigger from either registry."""
        if self._primary.is_set(name):
            return self._primary.spawn(name)
        if self._secondary.is_set(name):
            return self._secondary.spawn(name)
        raise ValueError(f"Trigger '{name}' not found in either registry")

    def primary_registry(self) -> TriggerRegistry:
        return self._primary

    def secondary_registry(self) -> TriggerRegistry:
        return self._secondary

    def __repr__(self) -> str:
        return (
            f"TriggerEngine("
            f"primary={len(self._primary.list_names())}, "
            f"secondary={len(self._secondary.list_names())})"
        )
