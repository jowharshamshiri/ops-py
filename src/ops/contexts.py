"""DryContext and WetContext — dual context system for ops.

DryContext: serializable JSON-compatible data values.
WetContext: non-serializable runtime references (services, connections, etc.).
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterator, Optional, TYPE_CHECKING

from ops.error import ContextError


def _json_type_name(value: Any) -> str:
    """Return the JSON type name of a Python value."""
    if value is None:
        return "null"
    if isinstance(value, bool):  # must precede int since bool is subclass of int
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


class DryContext:
    """Serializable context holding plain data values."""

    def __init__(self) -> None:
        self._values: Dict[str, Any] = {}
        self._aborted: bool = False
        self._abort_reason: Optional[str] = None

    @classmethod
    def _from_parts(
        cls,
        values: Dict[str, Any],
        aborted: bool,
        abort_reason: Optional[str],
    ) -> "DryContext":
        ctx = cls.__new__(cls)
        ctx._values = values
        ctx._aborted = aborted
        ctx._abort_reason = abort_reason
        return ctx

    def with_value(self, key: str, value: Any) -> "DryContext":
        """Builder pattern: insert a value and return self."""
        self.insert(key, value)
        return self

    def insert(self, key: str, value: Any) -> None:
        """Insert a serializable value."""
        self._values[key] = value

    def get(self, key: str, expected_type: type = None) -> Any:
        """Return the value for key, or None if not found.

        If expected_type is given, returns None on type mismatch instead of raising.
        """
        value = self._values.get(key)
        if value is None and key not in self._values:
            return None
        if expected_type is not None and not isinstance(value, expected_type):
            return None
        return value

    def get_required(self, key: str, expected_type: type = None) -> Any:
        """Return the value for key, raising ContextError if missing or wrong type."""
        if key not in self._values:
            raise ContextError(f"Required dry context key '{key}' not found")
        value = self._values[key]
        if expected_type is not None and not isinstance(value, expected_type):
            actual_type = _json_type_name(value)
            expected_name = expected_type.__name__
            raise ContextError(
                f"Type mismatch for dry context key '{key}': "
                f"expected type '{expected_name}', "
                f"but found '{actual_type}' value: {json.dumps(value)}"
            )
        return value

    def contains(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._values

    def keys(self) -> Iterator[str]:
        """Iterate over all keys."""
        return iter(self._values.keys())

    def values(self) -> Dict[str, Any]:
        """Return the raw values dict."""
        return self._values

    def get_or_insert_with(self, key: str, factory: Callable[[], Any]) -> Any:
        """Return existing value or insert via factory and return new value."""
        if key in self._values:
            return self._values[key]
        new_value = factory()
        self._values[key] = new_value
        return new_value

    def get_or_compute_with(
        self, key: str, computer: Callable[["DryContext", str], Any]
    ) -> Any:
        """Return existing value or compute via closure that receives context and key."""
        if key in self._values:
            return self._values[key]
        new_value = computer(self, key)
        self._values[key] = new_value
        return new_value

    async def ensure(
        self,
        key: str,
        wet: "WetContext",
        factory: Callable[["DryContext", "WetContext", str], Any],
    ) -> Any:
        """Async: return existing value or compute via async factory."""
        if key in self._values:
            return self._values[key]
        new_value = await factory(self, wet, key)
        self._values[key] = new_value
        return new_value

    def merge(self, other: "DryContext") -> None:
        """Merge other into self. Other's values overwrite self's on conflicts.

        Abort flag is inherited only if self is not already aborted.
        """
        self._values.update(other._values)
        if other._aborted and not self._aborted:
            self._aborted = True
            self._abort_reason = other._abort_reason

    def set_abort(self, reason: Optional[str]) -> None:
        """Set the abort flag with optional reason."""
        self._aborted = True
        self._abort_reason = reason

    def is_aborted(self) -> bool:
        """Check if abort flag is set."""
        return self._aborted

    def abort_reason(self) -> Optional[str]:
        """Return the abort reason if set."""
        return self._abort_reason

    def clear_control_flags(self) -> None:
        """Clear all control flags."""
        self._aborted = False
        self._abort_reason = None

    def clone(self) -> "DryContext":
        """Return an independent deep copy."""
        return DryContext._from_parts(
            dict(self._values),
            self._aborted,
            self._abort_reason,
        )

    def __copy__(self) -> "DryContext":
        return self.clone()

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = {
            "values": self._values,
            "control_flags": {
                "aborted": self._aborted,
                "abort_reason": self._abort_reason,
            },
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DryContext":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        ctx = cls.__new__(cls)
        ctx._values = data.get("values", {})
        flags = data.get("control_flags", {})
        ctx._aborted = flags.get("aborted", False)
        ctx._abort_reason = flags.get("abort_reason", None)
        return ctx

    def __repr__(self) -> str:
        return f"DryContext(keys={list(self._values.keys())}, aborted={self._aborted})"


class WetContext:
    """Non-serializable context holding runtime references."""

    def __init__(self) -> None:
        self._references: Dict[str, Any] = {}

    def with_ref(self, key: str, value: Any) -> "WetContext":
        """Builder pattern: insert a reference and return self."""
        self.insert_ref(key, value)
        return self

    def insert_ref(self, key: str, value: Any) -> None:
        """Insert a runtime reference."""
        self._references[key] = value

    def insert_arc(self, key: str, value: Any) -> None:
        """Insert a runtime reference (alias for insert_ref)."""
        self._references[key] = value

    def get_ref(self, key: str, expected_type: type = None) -> Optional[Any]:
        """Return the reference for key, or None if missing or wrong type."""
        value = self._references.get(key)
        if value is None and key not in self._references:
            return None
        if expected_type is not None and not isinstance(value, expected_type):
            return None
        return value

    def get_required(self, key: str, expected_type: type = None) -> Any:
        """Return the reference for key, raising ContextError if missing or wrong type."""
        if key not in self._references:
            raise ContextError(f"Required wet context reference '{key}' not found")
        value = self._references[key]
        if expected_type is not None and not isinstance(value, expected_type):
            expected_name = expected_type.__name__
            raise ContextError(
                f"Type mismatch for wet context reference '{key}': "
                f"expected type '{expected_name}', but found a different type"
            )
        return value

    def contains(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._references

    def keys(self) -> Iterator[str]:
        """Iterate over all keys."""
        return iter(self._references.keys())

    async def ensure(
        self,
        key: str,
        dry: "DryContext",
        factory: Callable[["DryContext", "WetContext", str], Any],
    ) -> Any:
        """Async: return existing reference or create via async factory."""
        if key in self._references:
            return self._references[key]
        new_value = await factory(dry, self, key)
        self._references[key] = new_value
        return new_value

    def merge(self, other: "WetContext") -> None:
        """Merge other into self. Other's references overwrite self's on conflicts."""
        self._references.update(other._references)

    def __repr__(self) -> str:
        return f"WetContext(keys={list(self._references.keys())})"
