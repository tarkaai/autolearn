"""OpenAI client for code generation in AutoLearn."""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

# Import OpenAI upfront to catch import errors early
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("WARNING: OpenAI package not found. Install with: pip install openai")

from pydantic import BaseModel, Field

logger = logging.getLogger("autolearn.openai")


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI API client."""

    api_key: str = Field(..., description="OpenAI API key")
    model_name: str = Field("gpt-4o", description="OpenAI model name")
    temperature: float = Field(0.1, description="Temperature for generation (0.0-1.0)")
    max_tokens: int = Field(4000, description="Maximum tokens in response")


class SkillGenerationRequest(BaseModel):
    """Request to generate a skill from natural language."""

    description: str = Field(..., description="Natural language description of the skill")
    name: Optional[str] = Field(None, description="Suggested name for the skill")
    inputs: Optional[Dict[str, Any]] = Field(None, description="Expected input schema")


class CodeGenerationResult(BaseModel):
    """Result of code generation."""

    code: str = Field(..., description="Generated Python code")
    meta: Dict[str, Any] = Field(..., description="Skill metadata")


class OpenAIClient:
    """Client for OpenAI API, focused on code generation.
    
    This client abstracts away the details of calling OpenAI APIs and
    focuses on the core use case: generating Python code for skills.
    """

    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize OpenAI client with configuration.
        
        If config is not provided, it will be loaded from environment variables:
        - OPENAI_API_KEY: Required
        - OPENAI_MODEL: Optional, defaults to gpt-4.1
        """
        if config is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            model_name = os.environ.get("OPENAI_MODEL", "gpt-4.1")
            self.config = OpenAIConfig(
                api_key=api_key,
                model_name=model_name,
            )
        else:
            self.config = config
        
        # Import inside __init__ to avoid dependency errors if OpenAI is not installed
        if not HAS_OPENAI:
            logger.error("OpenAI Python package not installed. Install with: pip install openai")
            raise ImportError("OpenAI Python package not installed")
        
        self.client = openai.OpenAI(api_key=self.config.api_key)

    def generate_skill_code(self, request: SkillGenerationRequest) -> CodeGenerationResult:
        """Generate Python code for a skill based on natural language description.
        
        Args:
            request: The skill generation request with description and optional params
            
        Returns:
            A CodeGenerationResult with Python code and metadata
            
        Raises:
            Exception: If the OpenAI API call fails
        """
        logger.info(f"Generating code for skill: {request.name or request.description[:30]}...")
        
        system_prompt = """You are an expert Python code generator for AutoLearn skills.
Generate clean, well-typed Python functions that implement the requested skill.
Your response must be valid JSON with two keys:
1. "code": A string containing a single Python function that implements the skill
2. "meta": A dictionary with skill metadata (name, description, version, inputs)

The function should:
- Have clear type hints
- Include docstring with description and parameters
- Be self-contained (except for standard library imports)
- Return a dictionary with the results
- Handle errors gracefully

The metadata should include:
- name: Skill name (lowercase with underscores)
- description: 1-2 sentence description
- version: "0.1.0"
- inputs: Dictionary describing expected inputs with types
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a Python skill function for: {request.description}"}
        ]
        
        if request.name:
            messages.append({"role": "user", "content": f"The skill should be named: {request.name}"})
        
        if request.inputs:
            input_desc = json.dumps(request.inputs, indent=2)
            messages.append({"role": "user", "content": f"The skill should accept these inputs: {input_desc}"})
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse response content as JSON
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate result has required keys
            if "code" not in result or "meta" not in result:
                raise ValueError("OpenAI response missing required keys: code, meta")
            
            logger.info(f"Successfully generated code for skill: {result['meta'].get('name', 'unnamed')}")
            
            return CodeGenerationResult(
                code=result["code"],
                meta=result["meta"]
            )
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            raise


def create_default_client() -> OpenAIClient:
    """Create an OpenAI client with default configuration from environment."""
    return OpenAIClient()


# Dependency for FastAPI
def get_openai_client() -> OpenAIClient:
    """Get the OpenAI client for dependency injection."""
    return create_default_client()
