#!/usr/bin/env python3
"""Test script to verify that we don't create unnecessary skills."""

import asyncio
import os
import sys
sys.path.append('/Users/dan/Projects/autolearn')

from backend.consumer_agent import ConsumerAgent
from backend.openai_client import OpenAIClient, OpenAIConfig


async def test_skill_prevention():
    """Test that 'what can you help with' uses existing list_known_skills skill."""
    
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
    
    # Test the problematic query
    test_queries = [
        "what can you help with",
        "what can you help me with?",
        "what are your capabilities",
        "list your skills",
        "show me what you can do"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing query: '{query}'")
        print('='*50)
        
        response = await agent.chat(session_id, query)
        
        print(f"Message: {response['message']}")
        print(f"Actions: {response['actions']}")
        print(f"Needs skill generation: {response['needs_skill_generation']}")
        
        # Check if it used the list_known_skills skill
        used_list_skill = any(
            action.get('skill_name') == 'list_known_skills' 
            for action in response['actions']
        )
        
        created_new_skill = any(
            action.get('type') == 'skill_generated'
            for action in response['actions']
        )
        
        print(f"Used list_known_skills: {used_list_skill}")
        print(f"Created new skill: {created_new_skill}")
        
        if used_list_skill:
            print("✅ SUCCESS: Used existing list_known_skills skill")
        elif created_new_skill:
            print("❌ FAILURE: Created unnecessary new skill")
        else:
            print("⚠️  WARNING: Didn't use existing skill or create new one")


if __name__ == "__main__":
    asyncio.run(test_skill_prevention())
