"""SkillEngine with SQLite persistence for AutoLearn."""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import os
import sqlite3
import traceback
import uuid
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

from .schemas import SkillMeta


logger = logging.getLogger("autolearn.skill_engine")


class SkillNotFound(Exception):
    pass


class SkillRuntimeError(Exception):
    pass


class SkillRegistrationError(Exception):
    pass


class SkillEngine:
    """Registry for skills with simple register/list/run primitives with SQLite persistence.

    This keeps execution synchronous and in-process, but adds SQLite persistence
    so skills are saved between server restarts.
    """

    def __init__(self, db_path: str = "skills.db") -> None:
        self._registry: Dict[str, Tuple[SkillMeta, Callable[..., Any]]] = {}
        self._modules: Dict[str, Any] = {}  # Keep references to loaded modules
        self.db_path = db_path
        
        # Initialize the database
        self._init_db()
        
        # Load any existing skills from the database
        self._load_skills_from_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database with the necessary tables."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Create skills table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    name TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    meta TEXT NOT NULL
                )
            ''')
            conn.commit()
            logger.info(f"Initialized skill database at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
        finally:
            conn.close()

    def _load_skills_from_db(self) -> None:
        """Load all skills from the database into memory."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, code, meta FROM skills")
            rows = cursor.fetchall()
            
            for name, code, meta_json in rows:
                try:
                    meta_dict = json.loads(meta_json)
                    meta = SkillMeta(**meta_dict)
                    # Register the skill from code (this will add it to in-memory registry)
                    self.register_from_code(code, meta, persist=False)
                    logger.info(f"Loaded skill from database: {name}")
                except Exception as e:
                    logger.error(f"Error loading skill {name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error querying database: {str(e)}")
        finally:
            conn.close()

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
                self._persist_skill_to_db(meta.name, code, meta)
                
            return
            
        except Exception as e:
            logger.error(f"Error registering skill from code: {str(e)}")
            raise SkillRegistrationError(f"Failed to register skill: {str(e)}") from e

    def _persist_skill_to_db(self, name: str, code: str, meta: SkillMeta) -> None:
        """Persist a skill to the SQLite database.
        
        Args:
            name: Name of the skill
            code: Python code string
            meta: Skill metadata
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Convert meta to JSON for storage
            meta_json = json.dumps(meta.dict())
            
            # Insert or replace the skill in the database
            cursor.execute(
                "INSERT OR REPLACE INTO skills (name, code, meta) VALUES (?, ?, ?)",
                (name, code, meta_json)
            )
            conn.commit()
            logger.info(f"Persisted skill to database: {name}")
        except Exception as e:
            logger.error(f"Error persisting skill to database: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()

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
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skills WHERE name = ?", (name,))
            conn.commit()
            logger.info(f"Unregistered skill: {name}")
        except Exception as e:
            logger.error(f"Error removing skill from database: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_skill_code(self, name: str) -> str:
        """Get the source code for a registered skill.
        
        Args:
            name: Name of the skill
            
        Returns:
            The Python source code for the skill
            
        Raises:
            SkillNotFound: If the skill is not registered
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM skills WHERE name = ?", (name,))
            result = cursor.fetchone()
            if not result:
                raise SkillNotFound(name)
            return result[0]
        except sqlite3.Error as e:
            logger.error(f"Database error retrieving skill code: {str(e)}")
            raise
        finally:
            conn.close()


def create_default_engine() -> SkillEngine:
    """Create a SkillEngine with one hardcoded skill registered.

    The `echo` skill simply returns the payload back. This is useful for
    testing the MCP surface and the `/run` endpoint.
    
    Uses a SQLite database in the current directory for persistence.
    """
    # Use a database in the current directory
    db_path = os.path.join(os.getcwd(), "skills.db")
    engine = SkillEngine(db_path=db_path)

    # If echo skill isn't already in the database, register it
    try:
        engine.get_skill_code("echo")
    except SkillNotFound:
        def echo(payload: Any = None) -> dict[str, Any]:
            """Echo skill: returns the provided payload unchanged."""
            return {"echo": payload}

        meta = SkillMeta(name="echo", description="Return the input payload", inputs={"payload": "any"})
        
        # Create the echo skill code
        echo_code = """def echo(payload: Any = None) -> dict[str, Any]:
    \"\"\"Echo skill: returns the provided payload unchanged.\"\"\"
    return {"echo": payload}"""
        
        # Register the echo skill with the code
        engine.register_from_code(echo_code, meta)
    
    return engine
