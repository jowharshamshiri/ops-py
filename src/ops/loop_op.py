"""LoopOp — iterative execution with scoped break/continue control flow."""

from __future__ import annotations

import logging
import uuid as uuid_module
from typing import Generic, List, Optional, TypeVar

from ops.error import AbortedError, OpError
from ops.op import Op
from ops.op_metadata import OpMetadata
from ops.contexts import DryContext, WetContext

T = TypeVar("T")
logger = logging.getLogger(__name__)


class LoopOp(Op[List[T]], Generic[T]):
    """Executes a batch of ops repeatedly up to a limit, with scoped control flow."""

    def __init__(
        self,
        counter_var: str,
        limit: int,
        ops: List[Op[T]],
        continue_on_error: bool = False,
    ) -> None:
        self._counter_var = counter_var
        self._limit = limit
        self._ops: List[Op[T]] = list(ops)
        self._loop_id = str(uuid_module.uuid4())
        self._continue_var = f"__continue_loop_{self._loop_id}"
        self._break_var = f"__break_loop_{self._loop_id}"
        self._continue_on_error = continue_on_error

    def add_op(self, op: Op[T]) -> "LoopOp[T]":
        """Add an op to the loop (builder pattern)."""
        self._ops.append(op)
        return self

    def with_continue_on_error(self, continue_on_error: bool) -> "LoopOp[T]":
        self._continue_on_error = continue_on_error
        return self

    async def _rollback_iteration_ops(
        self, succeeded_ops: List[Op[T]], dry: DryContext, wet: WetContext
    ) -> None:
        for op in reversed(succeeded_ops):
            try:
                await op.rollback(dry, wet)
                logger.debug(
                    "Successfully rolled back op %s in loop iteration",
                    op.metadata().name,
                )
            except Exception as e:
                logger.error(
                    "Failed to rollback op %s in loop iteration: %s",
                    op.metadata().name,
                    e,
                )

    def _get_counter(self, dry: DryContext) -> int:
        val = dry.get(self._counter_var)
        if val is None:
            return 0
        return int(val)

    def _set_counter(self, dry: DryContext, value: int) -> None:
        dry.insert(self._counter_var, value)

    async def perform(self, dry: DryContext, wet: WetContext) -> List[T]:
        results: List[T] = []
        counter = self._get_counter(dry)

        if not dry.contains(self._counter_var):
            self._set_counter(dry, counter)

        # Store loop ID for scoped control flow
        dry.insert("__current_loop_id", self._loop_id)

        while counter < self._limit:
            if dry.is_aborted():
                reason = dry.abort_reason() or "Loop operation aborted"
                raise AbortedError(reason)

            # Clear scoped control flags for this iteration
            dry.insert(self._continue_var, False)
            dry.insert(self._break_var, False)

            iteration_succeeded_ops: List[Op[T]] = []

            for op in self._ops:
                if dry.is_aborted():
                    await self._rollback_iteration_ops(
                        iteration_succeeded_ops, dry, wet
                    )
                    reason = dry.abort_reason() or "Loop operation aborted"
                    raise AbortedError(reason)

                try:
                    result = await op.perform(dry, wet)
                    results.append(result)
                    iteration_succeeded_ops.append(op)

                    # Check scoped continue flag
                    if dry.get(self._continue_var) is True:
                        dry.insert(self._continue_var, False)
                        break  # continue to next iteration

                    # Check scoped break flag
                    if dry.get(self._break_var) is True:
                        dry.insert(self._break_var, False)
                        return results  # break out of entire loop

                except AbortedError:
                    await self._rollback_iteration_ops(
                        iteration_succeeded_ops, dry, wet
                    )
                    raise
                except Exception as e:
                    if self._continue_on_error:
                        logger.warning(
                            "Operation %s failed in loop iteration %d: %s. "
                            "Continuing with next iteration.",
                            op.metadata().name,
                            counter,
                            e,
                        )
                        await self._rollback_iteration_ops(
                            iteration_succeeded_ops, dry, wet
                        )
                        break  # continue to next iteration
                    else:
                        await self._rollback_iteration_ops(
                            iteration_succeeded_ops, dry, wet
                        )
                        raise

            counter += 1
            self._set_counter(dry, counter)

        return results

    def metadata(self) -> OpMetadata:
        if self._continue_on_error:
            desc = (
                f"Loop {self._limit} times over {len(self._ops)} ops "
                f"(continue on error)"
            )
        else:
            desc = f"Loop {self._limit} times over {len(self._ops)} ops"
        return OpMetadata.builder("LoopOp").description(desc).build()

    async def rollback(self, dry: DryContext, wet: WetContext) -> None:
        pass
