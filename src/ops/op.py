"""Op — the core operation trait.

Mirrors Rust's Op<T> async trait.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

T = TypeVar("T")


class Op(ABC, Generic[T]):
    """Core operation interface.

    All ops implement perform() and metadata(). Rollback is optional (default no-op).
    """

    @abstractmethod
    async def perform(self, dry: "DryContext", wet: "WetContext") -> T:
        """Execute this operation."""
        ...

    @abstractmethod
    def metadata(self) -> "OpMetadata":
        """Return metadata describing this operation."""
        ...

    async def rollback(self, dry: "DryContext", wet: "WetContext") -> None:
        """Roll back this operation. Default is a no-op."""
        pass


if TYPE_CHECKING:
    from ops.contexts import DryContext, WetContext
    from ops.op_metadata import OpMetadata
