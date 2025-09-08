from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SkillMeta(BaseModel):
    """Metadata describing a skill exposed via MCP."""

    name: str = Field(..., description="Unique skill name")
    description: str | None = Field(None, description="Short description of the skill")
    version: str = Field("0.1.0", description="Skill semantic version")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Input schema description")


class RunRequest(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    success: bool
    result: Any | None = None
    error: str | None = None
