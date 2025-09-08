"""A small in-memory SkillEngine stub for Milestone 1."""

from __future__ import annotations

import traceback
from typing import Any, Callable, Dict, Tuple

from .schemas import SkillMeta


class SkillNotFound(Exception):
    pass


class SkillRuntimeError(Exception):
    pass


class SkillEngine:
    """Registry for skills with simple register/list/run primitives.

    This intentionally keeps execution synchronous and in-process. Later
    milestones will add persistence and sandboxing.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Tuple[SkillMeta, Callable[..., Any]]] = {}

    def register(self, meta: SkillMeta, func: Callable[..., Any]) -> None:
        """Register a skill by name with its callable.

        Overwrites any existing registration with the same name.
        """
        self._registry[meta.name] = (meta, func)

    def list_skills(self) -> list[SkillMeta]:
        return [meta for meta, _ in self._registry.values()]

    def run(self, name: str, args: dict[str, Any]) -> Any:
        if name not in self._registry:
            raise SkillNotFound(name)
        meta, func = self._registry[name]
        try:
            return func(**args)
        except Exception as exc:  # pragma: no cover - runtime passthrough
            tb = traceback.format_exc()
            # Return a wrapped error to avoid leaking internal state in raw form
            raise SkillRuntimeError(f"Skill {name} raised: {exc}\n{tb}") from exc


def create_default_engine() -> SkillEngine:
    """Create a SkillEngine with one hardcoded skill registered.

    The `echo` skill simply returns the payload back. This is useful for
    testing the MCP surface and the `/run` endpoint.
    """
    engine = SkillEngine()

    def echo(payload: Any = None) -> dict[str, Any]:
        """Echo skill: returns the provided payload unchanged."""
        return {"echo": payload}

    meta = SkillMeta(name="echo", description="Return the input payload", inputs={"payload": "any"})
    engine.register(meta, echo)
    return engine
