"""Trigger — reactive pattern for conditional action execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.batch import BatchOp


class Trigger(ABC):
    """Abstract base for triggers.

    A trigger evaluates a predicate; if true, it runs its actions.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the trigger name."""
        ...

    @abstractmethod
    def predicate(self) -> Op[bool]:
        """Return the predicate op."""
        ...

    @abstractmethod
    def actions(self) -> List[Op[None]]:
        """Return the action ops."""
        ...

    async def perform(self, dry: DryContext, wet: WetContext) -> None:
        """Evaluate predicate; if true, run actions as a batch."""
        should = await self.predicate().perform(dry, wet)
        if should:
            batch = BatchOp(self.actions())
            await batch.perform(dry, wet)

    def metadata(self) -> OpMetadata:
        return OpMetadata(
            name=f"Trigger {self.name()} with {len(self.actions())} actions"
        )
