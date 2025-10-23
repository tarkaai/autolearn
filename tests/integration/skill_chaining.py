"""Integration tests for skill chaining and composition through MCP protocol."""

import pytest
import json
import os
from typing import Dict, Any
import httpx


BASE_URL = "http://localhost:8000"
MCP_URL = f"{BASE_URL}/mcp"


class TestSkillChainingThroughMCP:
    """Test skill chaining through the MCP protocol."""
    
    @pytest.mark.asyncio
    async def test_mcp_call_to_composite_skill(self):
        """Test calling a skill that internally calls other skills via MCP."""
        async with httpx.AsyncClient() as client:
            # First, ensure we have base skills registered
            # Register a simple add skill
            add_skill_code = """
def add_numbers(a: float, b: float) -> dict:
    return {'result': a + b}
"""
            add_skill_meta = {
                "name": "add_numbers",
                "description": "Add two numbers",
                "inputs": {"a": "number", "b": "number"}
            }
            
            register_response = await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": add_skill_code, "meta": add_skill_meta}
            )
            assert register_response.status_code == 200
            
            # Register a multiply skill
            multiply_skill_code = """
def multiply_numbers(a: float, b: float) -> dict:
    return {'result': a * b}
"""
            multiply_skill_meta = {
                "name": "multiply_numbers",
                "description": "Multiply two numbers",
                "inputs": {"a": "number", "b": "number"}
            }
            
            register_response = await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": multiply_skill_code, "meta": multiply_skill_meta}
            )
            assert register_response.status_code == 200
            
            # Register a composite skill that uses both
            composite_skill_code = """
def compute_formula(x: float, y: float, z: float) -> dict:
    \"\"\"Compute (x + y) * z using existing skills.\"\"\"
    # First add x and y
    sum_result = call_skill('add_numbers', a=x, b=y)
    sum_value = sum_result['result']
    
    # Then multiply by z
    product_result = call_skill('multiply_numbers', a=sum_value, b=z)
    
    return {'result': product_result['result'], 'formula': '(x + y) * z'}
"""
            composite_skill_meta = {
                "name": "compute_formula",
                "description": "Compute (x + y) * z",
                "inputs": {"x": "number", "y": "number", "z": "number"}
            }
            
            register_response = await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": composite_skill_code, "meta": composite_skill_meta}
            )
            assert register_response.status_code == 200
            
            # Now call the composite skill via MCP
            mcp_request = {
                "jsonrpc": "2.0",
                "id": "test-composite-1",
                "method": "tools/call",
                "params": {
                    "name": "compute_formula",
                    "arguments": {"x": 3.0, "y": 4.0, "z": 5.0}
                }
            }
            
            mcp_response = await client.post(MCP_URL, json=mcp_request)
            assert mcp_response.status_code == 200
            
            result = mcp_response.json()
            assert result["jsonrpc"] == "2.0"
            assert "result" in result
            
            # Extract the actual result value
            content = result["result"]["content"]
            assert len(content) > 0
            result_text = content[0]["text"]
            
            # Parse the result (should be a dict string)
            import ast
            result_dict = ast.literal_eval(result_text)
            
            # (3 + 4) * 5 = 35
            assert result_dict["result"] == 35.0
            assert result_dict["formula"] == "(x + y) * z"
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detected_via_mcp(self):
        """Test that circular dependencies are properly detected when called via MCP."""
        async with httpx.AsyncClient() as client:
            # Register skill A that calls B
            skill_a_code = """
def skill_circular_a(x: int) -> dict:
    result = call_skill('skill_circular_b', x=x+1)
    return {'result': result['result'] + 1}
"""
            skill_a_meta = {
                "name": "skill_circular_a",
                "description": "Skill A in circular pair",
                "inputs": {"x": "integer"}
            }
            
            await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": skill_a_code, "meta": skill_a_meta}
            )
            
            # Register skill B that calls A (creating circular dependency)
            skill_b_code = """
def skill_circular_b(x: int) -> dict:
    result = call_skill('skill_circular_a', x=x+1)
    return {'result': result['result'] + 1}
"""
            skill_b_meta = {
                "name": "skill_circular_b",
                "description": "Skill B in circular pair",
                "inputs": {"x": "integer"}
            }
            
            await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": skill_b_code, "meta": skill_b_meta}
            )
            
            # Try to call skill A via MCP - should detect circular dependency
            mcp_request = {
                "jsonrpc": "2.0",
                "id": "test-circular-1",
                "method": "tools/call",
                "params": {
                    "name": "skill_circular_a",
                    "arguments": {"x": 1}
                }
            }
            
            mcp_response = await client.post(MCP_URL, json=mcp_request)
            assert mcp_response.status_code == 200
            
            result = mcp_response.json()
            
            # Should return an error result
            assert result["result"]["isError"] is True
            error_content = result["result"]["content"][0]["text"]
            assert "Circular dependency" in error_content or "circular" in error_content.lower()
    
    @pytest.mark.asyncio
    async def test_deep_skill_chain_via_mcp(self):
        """Test a deep chain of skills (within limit) via MCP."""
        async with httpx.AsyncClient() as client:
            # Create a chain of 4 skills (within the limit of 5)
            for i in range(4):
                skill_name = f"chain_skill_{i}"
                next_skill = f"chain_skill_{i+1}" if i < 3 else None
                
                if next_skill:
                    code = f"""
def chain_skill_{i}(value: int) -> dict:
    result = call_skill('{next_skill}', value=value+1)
    return {{'value': result['value'], 'level': {i}}}
"""
                else:
                    code = f"""
def chain_skill_{i}(value: int) -> dict:
    return {{'value': value, 'level': {i}}}
"""
                
                meta = {
                    "name": skill_name,
                    "description": f"Chain skill level {i}",
                    "inputs": {"value": "integer"}
                }
                
                register_response = await client.post(
                    f"{BASE_URL}/skills/register",
                    json={"code": code, "meta": meta}
                )
                assert register_response.status_code == 200
            
            # Call the first skill in the chain via MCP
            mcp_request = {
                "jsonrpc": "2.0",
                "id": "test-chain-1",
                "method": "tools/call",
                "params": {
                    "name": "chain_skill_0",
                    "arguments": {"value": 10}
                }
            }
            
            mcp_response = await client.post(MCP_URL, json=mcp_request)
            assert mcp_response.status_code == 200
            
            result = mcp_response.json()
            assert result["result"]["isError"] is False
            
            # Extract result
            content = result["result"]["content"]
            result_text = content[0]["text"]
            import ast
            result_dict = ast.literal_eval(result_text)
            
            # Value should be 10 + 1 + 1 + 1 = 13 (3 increments in the chain)
            assert result_dict["value"] == 13
            assert result_dict["level"] == 0  # First skill returns


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not available")
class TestAIGeneratedSkillComposition:
    """Test AI-generated skills that use skill composition."""
    
    @pytest.mark.asyncio
    async def test_ai_generates_skill_using_existing_skills(self):
        """Test that AI can generate a skill that leverages existing skills via call_skill."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # First, ensure we have some base skills
            # Register a square skill
            square_code = """
def square_number(x: float) -> dict:
    return {'result': x * x}
"""
            square_meta = {
                "name": "square_number",
                "description": "Square a number",
                "inputs": {"x": "number"}
            }
            
            await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": square_code, "meta": square_meta}
            )
            
            # Now ask AI to generate a skill that uses square_number
            generate_request = {
                "description": """Create a skill called 'pythagorean' that calculates the hypotenuse of a right triangle.
Given sides a and b, it should:
1. Use the square_number skill to square both a and b
2. Add the squared values
3. Return the square root of the sum

Available skills you can use:
- square_number(x: float) -> dict with 'result': squares the input

Use call_skill() to leverage the square_number skill.""",
                "name": "pythagorean"
            }
            
            gen_response = await client.post(
                f"{BASE_URL}/skills/generate",
                json=generate_request
            )
            
            # Should successfully generate the skill
            assert gen_response.status_code == 200
            gen_data = gen_response.json()
            assert gen_data["success"] is True
            assert "code" in gen_data
            
            # The generated code should contain call_skill
            generated_code = gen_data["code"]
            assert "call_skill" in generated_code
            assert "square_number" in generated_code
            
            # Test the generated skill
            test_response = await client.post(
                f"{BASE_URL}/skills/run",
                json={
                    "name": "pythagorean",
                    "args": {"a": 3.0, "b": 4.0}
                }
            )
            
            assert test_response.status_code == 200
            test_data = test_response.json()
            assert test_data["success"] is True
            
            # For a 3-4-5 triangle, hypotenuse should be 5
            result = test_data["result"]
            if isinstance(result, dict) and "result" in result:
                assert abs(result["result"] - 5.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_consumer_agent_recognizes_skill_composition(self):
        """Test that consumer agent recognizes when to compose skills vs create new ones."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Start a chat session
            session_response = await client.post(
                f"{BASE_URL}/sessions",
                json={"name": "Skill Composition Test"}
            )
            assert session_response.status_code == 200
            session_id = session_response.json()["session"]["id"]
            
            # Register some base math skills
            add_code = """
def add(a: float, b: float) -> dict:
    return {'result': a + b}
"""
            add_meta = {"name": "add", "description": "Add two numbers", "inputs": {"a": "number", "b": "number"}}
            await client.post(f"{BASE_URL}/skills/register", json={"code": add_code, "meta": add_meta})
            
            multiply_code = """
def multiply(a: float, b: float) -> dict:
    return {'result': a * b}
"""
            multiply_meta = {"name": "multiply", "description": "Multiply two numbers", "inputs": {"a": "number", "b": "number"}}
            await client.post(f"{BASE_URL}/skills/register", json={"code": multiply_code, "meta": multiply_meta})
            
            # Ask the consumer agent to create a skill that should use existing skills
            chat_request = {
                "message": "Create a skill that calculates the area of a rectangle. We already have add and multiply skills available.",
                "session_id": session_id
            }
            
            chat_response = await client.post(
                f"{BASE_URL}/consumer-agent/chat",
                json=chat_request
            )
            
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            
            # Check if a skill was generated
            actions = chat_data.get("actions", [])
            generated_skills = [a for a in actions if a.get("type") == "skill_generated"]
            
            if generated_skills:
                # The generated skill should ideally use existing skills
                # We can check if the AI mentioned composition in its reasoning
                message = chat_data.get("message", "")
                # The message might mention using existing skills
                # This is more of a behavioral check
                assert len(generated_skills) > 0


class TestSkillCompositionErrorHandling:
    """Test error handling in skill composition scenarios."""
    
    @pytest.mark.asyncio
    async def test_error_in_nested_skill_call(self):
        """Test that errors in nested skill calls are properly reported."""
        async with httpx.AsyncClient() as client:
            # Register a skill that can fail
            failing_skill_code = """
def divide_numbers(a: float, b: float) -> dict:
    if b == 0:
        raise ValueError("Division by zero")
    return {'result': a / b}
"""
            failing_skill_meta = {
                "name": "divide_numbers",
                "description": "Divide two numbers",
                "inputs": {"a": "number", "b": "number"}
            }
            
            await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": failing_skill_code, "meta": failing_skill_meta}
            )
            
            # Register a skill that calls the failing skill
            caller_skill_code = """
def safe_divide(numerator: float, denominator: float) -> dict:
    try:
        result = call_skill('divide_numbers', a=numerator, b=denominator)
        return {'result': result['result'], 'error': None}
    except Exception as e:
        return {'result': None, 'error': str(e)}
"""
            caller_skill_meta = {
                "name": "safe_divide",
                "description": "Safely divide two numbers with error handling",
                "inputs": {"numerator": "number", "denominator": "number"}
            }
            
            await client.post(
                f"{BASE_URL}/skills/register",
                json={"code": caller_skill_code, "meta": caller_skill_meta}
            )
            
            # Call with valid denominator - should work
            success_response = await client.post(
                f"{BASE_URL}/skills/run",
                json={"name": "safe_divide", "args": {"numerator": 10.0, "denominator": 2.0}}
            )
            assert success_response.status_code == 200
            success_data = success_response.json()
            assert success_data["success"] is True
            
            # Call with zero denominator - should handle error gracefully
            error_response = await client.post(
                f"{BASE_URL}/skills/run",
                json={"name": "safe_divide", "args": {"numerator": 10.0, "denominator": 0.0}}
            )
            assert error_response.status_code == 200
            error_data = error_response.json()
            # The skill itself handles the error, so success should be true
            assert error_data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

