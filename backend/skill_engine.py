"""SkillEngine with SQLite persistence for AutoLearn."""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import os
import traceback
import uuid
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import db
from . import sandbox
from .schemas import SkillMeta


logger = logging.getLogger("autolearn.skill_engine")


class SkillNotFound(Exception):
    pass


class SkillRuntimeError(Exception):
    pass


class SkillRegistrationError(Exception):
    pass


class SkillContext:
    """Execution context for skills with access to other skills.
    
    This context is injected into skill execution environments to allow
    skills to call other skills in a controlled manner with protection
    against circular dependencies and excessive recursion.
    """
    
    def __init__(self, engine: 'SkillEngine', call_stack: Optional[List[str]] = None, max_call_depth: int = 5):
        """Initialize skill execution context.
        
        Args:
            engine: The SkillEngine instance that manages skills
            call_stack: Current call stack to track nested calls
            max_call_depth: Maximum allowed call depth to prevent runaway recursion
        """
        self._engine = engine
        self._call_stack: List[str] = call_stack or []
        self._max_call_depth = max_call_depth
    
    def call_skill(self, name: str, **kwargs) -> Any:
        """Call another skill from within a skill.
        
        This function is injected into the skill's execution environment,
        allowing skills to compose functionality by calling other registered skills.
        
        Args:
            name: Name of the skill to call
            **kwargs: Arguments to pass to the skill
            
        Returns:
            The result from the called skill
            
        Raises:
            SkillRuntimeError: If circular dependency detected or max depth exceeded
            SkillNotFound: If the requested skill doesn't exist
            
        Example:
            # Within a skill function
            result = call_skill('calculator', operation='add', a=5, b=3)
        """
        # Check for circular dependencies
        if name in self._call_stack:
            call_chain = ' -> '.join(self._call_stack + [name])
            raise SkillRuntimeError(
                f"Circular dependency detected: {call_chain}"
            )
        
        # Check max depth
        if len(self._call_stack) >= self._max_call_depth:
            call_chain = ' -> '.join(self._call_stack + [name])
            raise SkillRuntimeError(
                f"Max call depth ({self._max_call_depth}) exceeded: {call_chain}"
            )
        
        # Track the call
        new_call_stack = self._call_stack + [name]
        logger.info(f"Skill calling skill: {' -> '.join(new_call_stack)}")
        
        try:
            # Call the skill with the extended call stack
            return self._engine._run_with_context(name, kwargs, new_call_stack)
        except Exception as e:
            logger.error(f"Skill call failed: {name} - {str(e)}")
            raise


class SkillEngine:
    """Registry for skills with simple register/list/run primitives with SQLite persistence.

    This keeps execution synchronous and in-process, but adds SQLite persistence
    so skills are saved between server restarts.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Tuple[SkillMeta, Callable[..., Any]]] = {}
        self._modules: Dict[str, Any] = {}  # Keep references to loaded modules
        
        # Load skills from database
        self._load_skills_from_db()

    def _load_skills_from_db(self) -> None:
        """Load all skills from the database into memory."""
        skills = db.list_skills()
        
        for skill_meta in skills:
            try:
                # Get the code for this skill
                _, code = db.get_skill(skill_meta.name)
                if code:
                    # Register the skill from code (this will add it to in-memory registry)
                    self.register_from_code(code, skill_meta, persist=False)
                    logger.info(f"Loaded skill from database: {skill_meta.name}")
            except Exception as e:
                logger.error(f"Error loading skill {skill_meta.name}: {str(e)}")

    def register(self, meta: SkillMeta, func: Callable[..., Any]) -> None:
        """Register a skill by name with its callable.

        Overwrites any existing registration with the same name.
        """
        self._registry[meta.name] = (meta, func)
        logger.info(f"Registered skill: {meta.name}")

    def register_from_code(self, code: str, meta: SkillMeta, persist: bool = True) -> None:
        """Register a skill from Python code string.
        
        Args:
            code: Python code string containing a function
            meta: Metadata for the skill
            persist: Whether to persist the skill to the database (default: True)
            
        Raises:
            SkillRegistrationError: If the code is invalid or no suitable function is found
        """
        try:
            # Generate a unique module name to avoid collisions
            module_name = f"autolearn_skill_{uuid.uuid4().hex}"
            
            # Create a module spec and module from the code
            spec: Optional[ModuleSpec] = importlib.util.spec_from_loader(module_name, loader=None)
            if not spec:
                raise SkillRegistrationError("Failed to create module spec")
            
            module = importlib.util.module_from_spec(spec)
            
            # Execute the code in the module's namespace
            # TODO: Add sandboxing here for secure execution
            exec(code, module.__dict__)
            
            # Find the function to use as the skill
            func = None
            # Try to find a function with the same name as the skill
            if hasattr(module, meta.name):
                func = getattr(module, meta.name)
            else:
                # Otherwise find the first function defined in the module
                for name, obj in module.__dict__.items():
                    if inspect.isfunction(obj) and not name.startswith("_"):
                        func = obj
                        break
            
            if not func or not callable(func):
                raise SkillRegistrationError("No suitable function found in the provided code")
            
            # Store a reference to the module to prevent garbage collection
            self._modules[meta.name] = module
            
            # Register the function as a skill
            self.register(meta, func)
            
            # Persist to database if requested
            if persist:
                db.save_skill(meta, code)
                
            return
            
        except Exception as e:
            logger.error(f"Error registering skill from code: {str(e)}")
            raise SkillRegistrationError(f"Failed to register skill: {str(e)}") from e

    def list_skills(self) -> list[SkillMeta]:
        return [meta for meta, _ in self._registry.values()]

    def run(self, name: str, args: dict[str, Any]) -> Any:
        """Run a skill by name with the given arguments.
        
        This is the public entry point for skill execution. It creates a new
        execution context with an empty call stack.
        
        Args:
            name: Name of the skill to run
            args: Arguments to pass to the skill
            
        Returns:
            The result from the skill execution
            
        Raises:
            SkillNotFound: If the skill doesn't exist
            SkillRuntimeError: If execution fails
        """
        return self._run_with_context(name, args, call_stack=[])
    
    def _run_with_context(self, name: str, args: dict[str, Any], call_stack: List[str]) -> Any:
        """Internal method to run a skill with a specific call stack context.
        
        This method is used both for top-level skill execution and for
        nested skill calls via call_skill().
        
        Args:
            name: Name of the skill to run
            args: Arguments to pass to the skill
            call_stack: Current call stack for tracking nested calls
            
        Returns:
            The result from the skill execution
            
        Raises:
            SkillNotFound: If the skill doesn't exist
            SkillRuntimeError: If execution fails
        """
        if name not in self._registry:
            raise SkillNotFound(name)
        
        meta, func = self._registry[name]
        
        # Create execution context for this skill
        context = SkillContext(self, call_stack, max_call_depth=5)
        
        try:
            # Run the function in a sandbox with the context
            return sandbox.run_skill_sandboxed(func, args, skill_context=context)
        except sandbox.SandboxError as exc:
            # Wrap sandbox errors in SkillRuntimeError
            raise SkillRuntimeError(f"Skill {name} failed in sandbox: {str(exc)}")
        except Exception as exc:  # pragma: no cover - runtime passthrough
            tb = traceback.format_exc()
            # Return a wrapped error to avoid leaking internal state in raw form
            raise SkillRuntimeError(f"Skill {name} raised: {exc}\n{tb}") from exc
    
    def unregister(self, name: str) -> None:
        """Unregister a skill by name.
        
        Args:
            name: Name of the skill to unregister
            
        Raises:
            SkillNotFound: If no skill with the given name exists
        """
        if name not in self._registry:
            raise SkillNotFound(name)
        
        # Remove from registry and module cache
        self._registry.pop(name)
        if name in self._modules:
            self._modules.pop(name)
        
        # Remove from database
        db.delete_skill(name)
        logger.info(f"Unregistered skill: {name}")
    
    def get_skill_code(self, name: str) -> str:
        """Get the source code for a registered skill.
        
        Args:
            name: Name of the skill
            
        Returns:
            The Python source code for the skill
            
        Raises:
            SkillNotFound: If the skill is not registered
        """
        _, code = db.get_skill(name)
        if not code:
            raise SkillNotFound(name)
        return code


def create_default_engine() -> SkillEngine:
    """Create a SkillEngine with one hardcoded skill registered.

    The `echo` skill simply returns the payload back. This is useful for
    testing the MCP surface and the `/run` endpoint.
    
    Uses a SQLite database for persistence.
    """
    # Make sure the database is initialized
    db.init_db()
    
    # Create a new engine
    engine = SkillEngine()

    # If echo skill isn't already in the database, register it
    try:
        engine.get_skill_code("echo")
    except SkillNotFound:
        # Create the echo skill code
        echo_code = """def echo(payload: Any = None) -> dict[str, Any]:
    \"\"\"Echo skill: returns the provided payload unchanged.\"\"\"
    return {"echo": payload}"""
        
        meta = SkillMeta(name="echo", description="Return the input payload", inputs={"payload": "any"})
        
        # Register the echo skill with the code
        engine.register_from_code(echo_code, meta)
    
    return engine


# Global engine instance for dependency injection
_engine_instance: Optional[SkillEngine] = None

def get_engine() -> SkillEngine:
    """Get the global SkillEngine instance.
    
    Returns:
        The global SkillEngine instance
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = create_default_engine()
    return _engine_instance


def get_mcp_spec(engine: SkillEngine) -> dict:
    """Generate the MCP specification from registered skills.
    
    Args:
        engine: SkillEngine instance
        
    Returns:
        MCP specification as a dictionary
    """
    tools = []
    for meta in engine.list_skills():
        tools.append({
            "type": "function",
            "function": {
                "name": meta.name,
                "description": meta.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": v} for k, v in meta.inputs.items()
                    },
                    "required": list(meta.inputs.keys())
                }
            }
        })
    
    return {
        "schema_version": "1.0",
        "server_info": {
            "name": "AutoLearn",
            "version": "0.1.0",
            "description": "Dynamic skill creation for AI agents"
        },
        "tools": tools
    }
