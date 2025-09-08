from __future__ import annotations

from typing import Any, Optional, Dict, List

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


class GenerateSkillRequest(BaseModel):
    """Request to generate a skill from natural language."""
    
    description: str = Field(..., description="Natural language description of what the skill should do")
    name: Optional[str] = Field(None, description="Optional suggested name for the skill")
    inputs: Optional[Dict[str, Any]] = Field(None, description="Optional input schema specification")


class GenerateSkillResponse(BaseModel):
    """Response with generated skill code and metadata."""
    
    success: bool = Field(..., description="Whether generation was successful")
    code: Optional[str] = Field(None, description="Generated Python code")
    meta: Optional[SkillMeta] = Field(None, description="Generated skill metadata")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class RegisterSkillRequest(BaseModel):
    """Request to register a skill from code."""
    
    code: str = Field(..., description="Python code implementing the skill")
    meta: SkillMeta = Field(..., description="Metadata for the skill")


class RegisterSkillResponse(BaseModel):
    """Response to registering a new skill."""
    
    success: bool
    name: Optional[str] = None
    error: Optional[str] = None


class GetSkillCodeResponse(BaseModel):
    """Response containing a skill's source code."""
    
    name: str
    code: str
