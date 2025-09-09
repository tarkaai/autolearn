#!/usr/bin/env python3
"""Test the improved AI-driven skill analysis system."""

import asyncio
import os
import sys
import json
sys.path.append('/Users/dan/Projects/autolearn')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from backend.consumer_agent import ConsumerAgent
from backend.openai_client import OpenAIClient, OpenAIConfig


async def test_ai_skill_analysis():
    """Test the AI skill analysis system."""
    
    # Mock available tools for testing
    mock_tools = [
        {
            "name": "list_known_skills",
            "description": "Returns a list of skills that this assistant is capable of performing",
            "function": {
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "name": "add_two_numbers", 
            "description": "Adds two numbers and returns the sum",
            "function": {
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            }
        },
        {
            "name": "calculator",
            "description": "A simple calculator that can add, subtract, multiply, and divide",
            "function": {
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "operation": {"type": "string"},
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["operation", "a", "b"]
                }
            }
        }
    ]
    
    # Create consumer agent
    config = OpenAIConfig(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        model_name="gpt-4o",
        temperature=0.1
    )
    openai_client = OpenAIClient(config)
    agent = ConsumerAgent(openai_client)
    
    # Test queries
    test_queries = [
        "what can you help with",
        "add 5 and 3",
        "help me solve complex algebraic equations",
        "create a skill to analyze stock market trends",
        "what's 10 * 7"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: '{query}'")
        print('='*60)
        
        try:
            # Test the AI analysis directly
            analysis = await agent._analyze_skill_requirements(query, mock_tools)
            print(f"AI Analysis: {json.dumps(analysis, indent=2)}")
            
            # Determine expected action
            expected_action = analysis.get("action", "unknown")
            print(f"Recommended Action: {expected_action}")
            
            if expected_action == "execute":
                skill_info = analysis.get("skill_to_execute", {})
                print(f"Skill to execute: {skill_info.get('name')} with params: {skill_info.get('parameters', {})}")
            elif expected_action == "improve":
                improve_info = analysis.get("skill_to_improve", {})
                print(f"Skill to improve: {improve_info.get('current_name')}")
                print(f"Improvements: {improve_info.get('improvements')}")
            elif expected_action == "create":
                create_info = analysis.get("new_skill", {})
                print(f"New skill: {create_info.get('name')}")
                print(f"Description: {create_info.get('description')}")
                print(f"Uses existing: {create_info.get('uses_existing_skills', [])}")
                
        except Exception as e:
            print(f"❌ Error testing '{query}': {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable is required")
        sys.exit(1)
        
    asyncio.run(test_ai_skill_analysis())
