"""Test consumer agent's ability to execute existing skills vs generating new ones."""

import pytest
import httpx
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


class TestConsumerAgentSkillExecution:
    """Test cases for consumer agent skill execution behavior."""

    @pytest.mark.asyncio
    async def test_should_use_existing_calculator_skill(self):
        """Test that consumer agent uses existing calculator skill instead of generating a new one."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/consumer-agent/chat",
                json={
                    "message": "Can you calculate 25 + 17 for me?"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should NOT generate a new skill since calculator exists
            skill_generated_actions = [
                action for action in data.get("actions", []) 
                if action.get("type") == "skill_generated"
            ]
            assert len(skill_generated_actions) == 0, "Should not generate new skill when calculator exists"
            
            # Should use existing skill
            skill_used_actions = [
                action for action in data.get("actions", []) 
                if action.get("type") == "skill_used"
            ]
            assert len(skill_used_actions) > 0, "Should use existing calculator skill"
            
            # Should not need skill generation 
            assert data.get("needs_skill_generation") == False
            
            # Response should include the calculation result
            message = data.get("message", "").lower()
            assert "42" in message or "result" in message, "Should include calculation result in response"

    @pytest.mark.asyncio
    async def test_should_use_existing_circle_area_skill(self):
        """Test that consumer agent uses existing circle area skill."""
        
        async with httpx.AsyncClient() as client:
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
            
            # Check that the correct skill was used
            used_skill_names = [action.get("skill_name") for action in skill_used_actions]
            assert "calculate_circle_area" in used_skill_names, "Should use calculate_circle_area skill"

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
        
        async with httpx.AsyncClient() as client:
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


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
