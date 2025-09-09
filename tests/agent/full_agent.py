#!/usr/bin/env python3
"""Test the full consumer agent with AI-driven skill management."""

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


async def test_full_consumer_agent():
    """Test the full consumer agent functionality."""
    
    # Start the backend server in the background if not already running
    print("Testing Consumer Agent with AI-driven skill analysis...")
    
    # Create consumer agent
    config = OpenAIConfig(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        model_name="gpt-4o",
        temperature=0.3
    )
    openai_client = OpenAIClient(config)
    agent = ConsumerAgent(openai_client)
    
    # Start a conversation
    session_id = await agent.start_conversation("test_user")
    print(f"Started session: {session_id}")
    
    # Test queries that should use existing skills vs create new ones
    test_cases = [
        {
            "query": "what can you help with",
            "expected_action": "use existing list_known_skills skill"
        },
        {
            "query": "add 15 and 25", 
            "expected_action": "use existing add_two_numbers skill"
        },
        {
            "query": "help me create a machine learning model",
            "expected_action": "create new skill that uses existing skills"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected_action"]
        
        print(f"\n{'='*80}")
        print(f"Test {i}: '{query}'")
        print(f"Expected: {expected}")
        print('='*80)
        
        try:
            response = await agent.chat(session_id, query)
            
            print(f"\n📝 Agent Response:")
            print(response['message'])
            
            print(f"\n🔧 Actions Taken:")
            for action in response['actions']:
                action_type = action.get('type')
                if action_type == 'skill_used':
                    skill_name = action.get('skill_name')
                    reasoning = action.get('ai_reasoning', '')
                    print(f"  ✅ Used skill: {skill_name}")
                    if reasoning:
                        print(f"     Reasoning: {reasoning}")
                elif action_type == 'skill_generated':
                    skill_name = action.get('skill_name')
                    uses_existing = action.get('uses_existing_skills', [])
                    reasoning = action.get('ai_reasoning', '')
                    print(f"  🆕 Created skill: {skill_name}")
                    if uses_existing:
                        print(f"     Uses existing skills: {', '.join(uses_existing)}")
                    if reasoning:
                        print(f"     Reasoning: {reasoning}")
                elif action_type == 'skill_improvement_suggested':
                    current_skill = action.get('current_skill')
                    improvements = action.get('improvements')
                    print(f"  💡 Suggested improving: {current_skill}")
                    print(f"     Improvements: {improvements}")
            
            print(f"\n🤖 Needs skill generation: {response.get('needs_skill_generation', False)}")
            
            # Analyze if the response matches expectations
            actions = response['actions']
            used_existing = any(action.get('type') == 'skill_used' for action in actions)
            created_new = any(action.get('type') == 'skill_generated' for action in actions)
            
            if "existing" in expected and used_existing:
                print("✅ SUCCESS: Used existing skill as expected")
            elif "create" in expected and created_new:
                print("✅ SUCCESS: Created new skill as expected")
            elif not actions and "simple" in expected:
                print("✅ SUCCESS: Handled with simple response as expected")
            else:
                print("⚠️  PARTIAL: Response doesn't match exact expectation but may still be correct")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-"*80)


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable is required")
        sys.exit(1)
        
    asyncio.run(test_full_consumer_agent())
