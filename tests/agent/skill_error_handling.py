#!/usr/bin/env python3
"""Test improved skill error handling and parameter mapping."""

import asyncio
import os
import sys
import json
from typing import Dict, Any
sys.path.append('/Users/dan/Projects/autolearn')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from backend.consumer_agent import ConsumerAgent
from backend.openai_client import OpenAIClient, OpenAIConfig


async def test_fibonacci_error_handling():
    """Test how the consumer agent handles skill parameter mismatches."""
    
    print("Testing Consumer Agent Error Handling and Recovery...")
    
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
    
    # Test case that triggers the fibonacci parameter mismatch
    print(f"\n{'='*80}")
    print(f"Test: 'calculate the fibonacci sequence to 10'")
    print(f"Expected: Should detect parameter mismatch and suggest fix")
    print('='*80)
    
    try:
        response = await agent.chat(session_id, "calculate the fibonacci sequence to 10")
        
        print(f"\n📝 Agent Response:")
        print(response['message'])
        
        print(f"\n🔧 Actions Taken:")
        for action in response['actions']:
            action_type = action.get('type')
            if action_type == 'skill_used':
                skill_name = action.get('skill_name')
                result = action.get('result')
                raw_result = action.get('raw_result')
                print(f"  ✅ Used skill: {skill_name}")
                print(f"     Result: {result}")
                if raw_result and 'error' in str(raw_result):
                    print(f"     ⚠️  Error in execution: {raw_result}")
            elif action_type == 'skill_improvement_suggested':
                current_skill = action.get('current_skill')
                improvements = action.get('improvements')
                print(f"  💡 Suggested improving: {current_skill}")
                print(f"     Improvements: {improvements}")
            elif action_type == 'skill_generated':
                skill_name = action.get('skill_name')
                print(f"  🆕 Created skill: {skill_name}")
        
        # Analyze the error handling quality
        print(f"\n🔍 Error Handling Analysis:")
        
        # Check if any skill execution failed
        failed_executions = [
            action for action in response['actions'] 
            if action.get('type') == 'skill_used' and 
               (action.get('raw_result', {}).get('error') or 'error' in str(action.get('result', '')))
        ]
        
        if failed_executions:
            print("  ❌ Skill execution failed")
            for failed in failed_executions:
                error_msg = failed.get('raw_result', {}).get('error', str(failed.get('result', '')))
                print(f"     Error: {error_msg}")
                
                # Check if it's a parameter mismatch
                if 'unexpected keyword argument' in error_msg:
                    print("  🎯 IDENTIFIED: Parameter mismatch error")
                    print("     SUGGESTION: Agent should detect this and map parameters correctly")
                    
        # Check if agent suggested improvements
        improvements = [
            action for action in response['actions'] 
            if action.get('type') == 'skill_improvement_suggested'
        ]
        
        if improvements:
            print("  ✅ Agent suggested skill improvements")
        else:
            print("  ❌ Agent did not suggest improvements for failed skill")
            
        # Check if agent tried to generate a new skill instead of fixing the parameter issue
        new_skills = [
            action for action in response['actions'] 
            if action.get('type') == 'skill_generated'
        ]
        
        if new_skills:
            print("  ⚠️  Agent generated new skill instead of fixing parameter mismatch")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def print_improvement_suggestions():
    """Print concrete suggestions for improving the consumer agent."""
    
    print(f"\n{'='*80}")
    print("🚀 IMPROVEMENT SUGGESTIONS")
    print('='*80)
    
    suggestions = [
        {
            "issue": "Parameter Mismatch Detection",
            "problem": "Agent calls calculate_fibonacci_sequence(terms=10) but function expects n_terms",
            "solution": "Add parameter introspection to map user intent to correct parameter names",
            "implementation": """
            1. Parse skill metadata to understand parameter names
            2. Use AI to map user intent ('terms', 'count', 'number') to correct param ('n_terms')
            3. Attempt parameter correction before failing
            """
        },
        {
            "issue": "Error Analysis and Recovery",
            "problem": "Generic error handling doesn't identify fixable issues",
            "solution": "Implement intelligent error analysis with recovery strategies",
            "implementation": """
            1. Parse error messages for common patterns (parameter mismatch, type errors)
            2. For parameter errors: suggest corrections and retry
            3. For type errors: attempt type conversion and retry
            4. Only suggest new skill creation as last resort
            """
        },
        {
            "issue": "User Communication",
            "problem": "User gets confusing technical error without helpful guidance",
            "solution": "Provide clear, actionable feedback to users",
            "implementation": """
            1. Translate technical errors to user-friendly language
            2. Explain what went wrong and what the agent is doing to fix it
            3. Show the corrected call attempt: 'I'll try with n_terms instead of terms'
            """
        },
        {
            "issue": "Skill Improvement vs New Skill",
            "problem": "Agent suggests creating new skill instead of fixing parameter issue",
            "solution": "Prioritize fixing existing skills over creating new ones",
            "implementation": """
            1. First: Try parameter mapping and correction
            2. Second: Suggest skill improvement if logic needs enhancement
            3. Last: Create new skill only if no existing skill can handle the request
            """
        }
    ]
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['issue']}")
        print(f"   Problem: {suggestion['problem']}")
        print(f"   Solution: {suggestion['solution']}")
        print(f"   Implementation:")
        for line in suggestion['implementation'].strip().split('\n'):
            print(f"     {line.strip()}")


async def main():
    """Run the error handling test and show improvement suggestions."""
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable is required")
        sys.exit(1)
        
    await test_fibonacci_error_handling()
    print_improvement_suggestions()


if __name__ == "__main__":
    asyncio.run(main())
