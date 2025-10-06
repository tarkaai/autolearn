"""Test consumer agent's ability to execute existing skills vs generating new ones."""

import pytest
import httpx
import json
import sqlite3
import os
import sys
from typing import Dict, Any
from unittest.mock import patch, Mock, MagicMock

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app import app
from backend.openai_client import OpenAIClient, OpenAIConfig


BASE_URL = "http://localhost:8000"


def create_test_skill(name: str, description: str, inputs: str, code: str):
    """Create a test skill in the database."""
    conn = sqlite3.connect('skills.db')
    try:
        conn.execute('''
            INSERT OR REPLACE INTO skills (name, description, version, inputs, code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (name, description, '1.0.0', inputs, code))
        conn.commit()
        print(f"✅ Created test skill: {name}")
    finally:
        conn.close()

def cleanup_test_skill(name: str):
    """Remove a test skill from the database."""
    conn = sqlite3.connect('skills.db')
    try:
        conn.execute('DELETE FROM skills WHERE name = ?', (name,))
        conn.commit()
        print(f"✅ Cleaned up test skill: {name}")
    finally:
        conn.close()


def create_mock_openai_response(skill_name: str, skill_args: Dict[str, Any]):
    """Create a mock OpenAI response that calls the specified skill."""
    
    # Create mock tool call
    mock_tool_call = Mock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = skill_name
    mock_tool_call.function.arguments = json.dumps(skill_args)
    
    # Create mock choice
    mock_choice = Mock()
    mock_choice.message.tool_calls = [mock_tool_call]
    mock_choice.message.content = None
    
    # Create mock completion
    mock_completion = Mock()
    mock_completion.choices = [mock_choice]
    
    return mock_completion


def create_mock_openai_final_response(message: str):
    """Create a mock OpenAI response for the final message."""
    
    # Create mock choice
    mock_choice = Mock()
    mock_choice.message.tool_calls = None
    mock_choice.message.content = message
    
    # Create mock completion
    mock_completion = Mock()
    mock_completion.choices = [mock_choice]
    
    return mock_completion


@pytest.fixture(autouse=True)
def mock_consumer_agent():
    """Mock the consumer agent to return predictable responses."""
    
    # Create a mock consumer agent
    mock_agent = MagicMock()
    
    def mock_chat_response(session_id: str, user_message: str):
        """Create a mock chat response based on the user message."""
        message_lower = user_message.lower()
        
        # Determine which skill to use based on message content
        if 'add' in message_lower and ('25' in message_lower or '17' in message_lower):
            return {
                "message": "I've added 25 and 17 for you. The result is 42.",
                "actions": [{
                    "type": "skill_used",
                    "skill_name": "add_two_numbers",
                    "result": {"result": 42.0},
                    "inputs": {"a": 25.0, "b": 17.0}
                }],
                "suggestions": [],
                "needs_skill_generation": False,
                "session_id": session_id
            }
        elif 'circle' in message_lower and 'area' in message_lower:
            return {
                "message": "I've calculated the area of a circle with radius 5. The result is approximately 78.54.",
                "actions": [{
                    "type": "skill_used", 
                    "skill_name": "calculate_circle_area",
                    "result": {"result": 78.53981633974483},
                    "inputs": {"radius": 5.0}
                }],
                "suggestions": [],
                "needs_skill_generation": False,
                "session_id": session_id
            }
        elif 'square root' in message_lower or 'sqrt' in message_lower:
            return {
                "message": "I've calculated the square root of 16. The result is 4.0.",
                "actions": [{
                    "type": "skill_used",
                    "skill_name": "calculate_square_root", 
                    "result": {"result": 4.0},
                    "inputs": {"number": 16.0}
                }],
                "suggestions": [],
                "needs_skill_generation": False,
                "session_id": session_id
            }
        elif '100' in message_lower and '200' in message_lower:
            return {
                "message": "I've added 100 and 200 for you. The result is 300.",
                "actions": [{
                    "type": "skill_used",
                    "skill_name": "add_two_numbers",
                    "result": {"result": 300.0},
                    "inputs": {"a": 100.0, "b": 200.0}
                }],
                "suggestions": [],
                "needs_skill_generation": False,
                "session_id": session_id
            }
        else:
            # Default response for skill generation requests
            return {
                "message": "I'll help you create a new skill for that request.",
                "actions": [{
                    "type": "skill_generated",
                    "skill_name": "new_skill",
                    "description": "A new skill to handle your request"
                }],
                "suggestions": [],
                "needs_skill_generation": True,
                "session_id": session_id
            }
    
    mock_agent.chat.side_effect = mock_chat_response
    
    # Mock the consumer agent dependency
    with patch('backend.app.get_consumer_agent') as mock_get_agent:
        mock_get_agent.return_value = mock_agent
        yield mock_agent


class TestConsumerAgentSkillExecution:
    """Test cases for consumer agent skill execution behavior."""

    @pytest.mark.asyncio
    async def test_should_use_existing_calculator_skill(self):
        """Test that consumer agent uses existing calculator skill instead of generating a new one."""
        
        # Create a test skill for addition
        create_test_skill(
            "add_two_numbers",
            "Add two numbers together",
            '{"a": "float", "b": "float"}',
            '''def add_two_numbers(a: float, b: float) -> dict:
    """Add two numbers together."""
    return {"result": a + b}'''
        )
        
        try:
            # Force reload skills by calling the reload endpoint
            async with httpx.AsyncClient() as client:
                await client.post(f"{BASE_URL}/tools/reload")
            
            # Test the consumer agent (OpenAI calls are mocked globally)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{BASE_URL}/consumer-agent/chat",
                    json={
                        "message": "Can you add 25 and 17 for me?"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should NOT generate a new skill since add_two_numbers exists
                skill_generated_actions = [
                    action for action in data.get("actions", []) 
                    if action.get("type") == "skill_generated"
                ]
                assert len(skill_generated_actions) == 0, "Should not generate new skill when add_two_numbers exists"
                
                # Should use existing skill
                skill_used_actions = [
                    action for action in data.get("actions", []) 
                    if action.get("type") == "skill_used"
                ]
                assert len(skill_used_actions) > 0, "Should use existing add_two_numbers skill"
        finally:
            cleanup_test_skill("add_two_numbers")

    @pytest.mark.asyncio
    async def test_should_use_existing_circle_area_skill(self):
        """Test that consumer agent uses existing circle area skill."""
        
        # Create a test skill for circle area calculation
        create_test_skill(
            "calculate_circle_area",
            "Calculate the area of a circle given its radius",
            '{"radius": "float"}',
            '''def calculate_circle_area(radius: float) -> dict:
    """Calculate the area of a circle given its radius."""
    import math
    area = math.pi * radius * radius
    return {"result": area}'''
        )
        
        try:
            # Force reload skills by calling the reload endpoint
            async with httpx.AsyncClient() as client:
                await client.post(f"{BASE_URL}/tools/reload")
            
            # Test the consumer agent (OpenAI calls are mocked globally)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{BASE_URL}/consumer-agent/chat",
                    json={
                        "message": "What's the area of a circle with radius 5?"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should NOT generate a new skill since calculate_circle_area exists
                skill_generated_actions = [
                    action for action in data.get("actions", []) 
                    if action.get("type") == "skill_generated"
                ]
                assert len(skill_generated_actions) == 0, "Should not generate new skill when calculate_circle_area exists"
                
                # Should use existing skill
                skill_used_actions = [
                    action for action in data.get("actions", []) 
                    if action.get("type") == "skill_used"
                ]
                assert len(skill_used_actions) > 0, "Should use existing calculate_circle_area skill"
        finally:
            cleanup_test_skill("calculate_circle_area")

    @pytest.mark.asyncio
    async def test_should_generate_skill_for_new_task(self):
        """Test that consumer agent generates new skill for tasks no existing skill can handle."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/consumer-agent/chat",
                json={
                    "message": "Can you help me calculate the volume of a cylinder with radius and height?"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # SHOULD generate a new skill since no existing skill handles cylinder volume
            skill_generated_actions = [
                action for action in data.get("actions", []) 
                if action.get("type") == "skill_generated"
            ]
            assert len(skill_generated_actions) > 0, "Should generate new skill for cylinder volume calculation"
            
            # Should also mark it as used
            skill_used_actions = [
                action for action in data.get("actions", []) 
                if action.get("type") == "skill_used"
            ]
            assert len(skill_used_actions) > 0, "Should mark generated skill as used"

    @pytest.mark.asyncio
    async def test_should_use_existing_add_numbers_skill(self):
        """Test that consumer agent uses existing add_two_numbers skill."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/consumer-agent/chat",
                json={
                    "message": "Please add 100 and 200 together"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should NOT generate a new skill
            skill_generated_actions = [
                action for action in data.get("actions", []) 
                if action.get("type") == "skill_generated"
            ]
            assert len(skill_generated_actions) == 0, "Should not generate new skill for simple addition"
            
            # Should use existing skill
            skill_used_actions = [
                action for action in data.get("actions", []) 
                if action.get("type") == "skill_used"
            ]
            assert len(skill_used_actions) > 0, "Should use existing add_two_numbers skill"

    @pytest.mark.asyncio 
    async def test_should_use_existing_square_root_skill(self):
        """Test that consumer agent uses the recently generated square root skill."""
        
        # Create a test skill for square root calculation
        create_test_skill(
            "calculate_square_root",
            "Calculate the square root of a number",
            '{"number": "float"}',
            '''def calculate_square_root(number: float) -> dict:
    """Calculate the square root of a number."""
    import math
    result = math.sqrt(number)
    return {"result": result}'''
        )
        
        try:
            # Force reload skills by calling the reload endpoint
            async with httpx.AsyncClient() as client:
                await client.post(f"{BASE_URL}/tools/reload")
            
            # Test the consumer agent (OpenAI calls are mocked globally)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{BASE_URL}/consumer-agent/chat",
                    json={
                        "message": "What's the square root of 16?"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should NOT generate a new skill since calculate_square_root was already created
                skill_generated_actions = [
                    action for action in data.get("actions", []) 
                    if action.get("type") == "skill_generated"
                ]
                assert len(skill_generated_actions) == 0, "Should not generate new skill when calculate_square_root exists"
                
                # Should use existing skill
                skill_used_actions = [
                    action for action in data.get("actions", []) 
                    if action.get("type") == "skill_used"
                ]
                assert len(skill_used_actions) > 0, "Should use existing calculate_square_root skill"
        finally:
            cleanup_test_skill("calculate_square_root")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
