"""BatchOp — sequential execution of ops with LIFO rollback on failure."""

from __future__ import annotations

import logging
from typing import Generic, List, TypeVar

from ops.error import AbortedError, BatchFailedError, OpError
from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext
from ops.batch_metadata import BatchMetadataBuilder

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BatchOp(Op[List[T]], Generic[T]):
    """Executes a sequence of ops, rolling back all succeeded ops on failure."""

    def __init__(self, ops: List[Op[T]], continue_on_error: bool = False) -> None:
        self._ops: List[Op[T]] = list(ops)
        self._continue_on_error = continue_on_error

    def with_continue_on_error(self, continue_on_error: bool) -> "BatchOp[T]":
        self._continue_on_error = continue_on_error
        return self

    def add_op(self, op: Op[T]) -> None:
        self._ops.append(op)

    def len(self) -> int:
        return len(self._ops)

    def is_empty(self) -> bool:
        return len(self._ops) == 0

    async def _rollback_succeeded_ops(
        self, succeeded_ops: List[Op[T]], dry: DryContext, wet: WetContext
    ) -> None:
        for op in reversed(succeeded_ops):
            try:
                await op.rollback(dry, wet)
                logger.debug("Successfully rolled back op %s", op.metadata().name)
            except Exception as e:
                logger.error(
                    "Failed to rollback op %s: %s", op.metadata().name, e
                )

    async def perform(self, dry: DryContext, wet: WetContext) -> List[T]:
        results: List[T] = []
        errors = []
        succeeded_ops: List[Op[T]] = []

        for index, op in enumerate(self._ops):
            if dry.is_aborted():
                await self._rollback_succeeded_ops(succeeded_ops, dry, wet)
                reason = dry.abort_reason() or "Batch operation aborted"
                raise AbortedError(reason)

            try:
                result = await op.perform(dry, wet)
                results.append(result)
                succeeded_ops.append(op)
            except AbortedError as e:
                await self._rollback_succeeded_ops(succeeded_ops, dry, wet)
                raise
            except Exception as e:
                if self._continue_on_error:
                    errors.append((index, e))
                else:
                    await self._rollback_succeeded_ops(succeeded_ops, dry, wet)
                    raise BatchFailedError(
                        f"Op {index}-{op.metadata().name} failed: {e}"
                    )

        return results

    def metadata(self) -> OpMetadata:
        return BatchMetadataBuilder(self._ops).build()

    async def rollback(self, dry: DryContext, wet: WetContext) -> None:
        pass
