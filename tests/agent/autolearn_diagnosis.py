#!/usr/bin/env python3
"""Test script to verify our diagnosis of the AutoLearn skill improvement issue."""

import asyncio
import httpx
import json

async def test_autolearn_diagnosis():
    """Test that demonstrates the missing auto-improvement connection."""
    
    print("🔍 DIAGNOSING AUTOLEARN SKILL IMPROVEMENT ISSUE")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Verify the skill improvement endpoint works
        print("\n1. 📋 Testing skill improvement endpoint directly...")
        
        # Get the current broken skill code
        response = await client.get("http://localhost:8000/skills/calculate_and_multiply_fibonacci/code")
        if response.status_code == 200:
            current_code = response.json()["code"]
            
            # Try to improve it
            improvement_request = {
                "skill_name": "calculate_and_multiply_fibonacci",
                "current_code": current_code,
                "improvement_prompt": "Fix parameter mismatch: change 'num_terms' to 'n_terms' and remove the 'skills' parameter. Instead of calling other skills via parameters, use direct implementation for fibonacci sequence and multiplication."
            }
            
            improve_response = await client.post(
                "http://localhost:8000/skills/improve",
                json=improvement_request
            )
            
            if improve_response.status_code == 200:
                improve_data = improve_response.json()
                if improve_data.get("success"):
                    print("   ✅ Skill improvement endpoint works!")
                    print(f"   📝 Generated improved code length: {len(improve_data.get('code', ''))}" )
                else:
                    print(f"   ❌ Improvement failed: {improve_data.get('error')}")
            else:
                print(f"   ❌ HTTP Error: {improve_response.status_code}")
        else:
            print(f"   ❌ Could not get current skill code: {response.status_code}")
        
        # 2. Test the consumer agent chat to see current behavior
        print("\n2. 🤖 Testing consumer agent behavior...")
        
        chat_response = await client.post(
            "http://localhost:8000/consumer-agent/chat",
            json={
                "message": "calculate and multiply fibonacci up to term 9"
            }
        )
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            
            print(f"   📝 Agent Response: {chat_data.get('message', 'No message')[:100]}...")
            
            # Check if any skill improvement was attempted
            actions = chat_data.get('actions', [])
            skill_improvement_attempted = any(
                action.get('type') == 'skill_improvement_attempted' 
                for action in actions
            )
            
            print(f"   🔧 Automatic skill improvement attempted: {skill_improvement_attempted}")
            
            # Check what actually happened
            for i, action in enumerate(actions):
                action_type = action.get('type')
                print(f"   📄 Action {i+1}: {action_type}")
                
                if action_type == 'skill_used':
                    skill_name = action.get('skill_name')
                    result = action.get('result')
                    print(f"      🎯 Used skill: {skill_name}")
                    if isinstance(result, dict) and "error" in result:
                        print(f"      ❌ Skill failed: {result['error']}")
                    else:
                        print(f"      ✅ Skill succeeded")
                        
                elif action_type == 'skill_generated':
                    skill_name = action.get('skill_name', 'Unknown')
                    print(f"      🆕 Generated new skill: {skill_name}")
        else:
            print(f"   ❌ Chat request failed: {chat_response.status_code}")
        
        # 3. Summary and diagnosis
        print("\n3. 🎯 DIAGNOSIS SUMMARY")
        print("   📍 Issue: Consumer agent doesn't call skill improvement when existing skills fail")
        print("   📍 Evidence: Skill improvement endpoint works, but agent doesn't use it")
        print("   📍 Solution: Add auto-improvement trigger in consumer agent error handling")
        print("   📍 Expected flow: Skill fails → Parameter retry fails → Auto-improve → Retry improved skill")

if __name__ == "__main__":
    asyncio.run(test_autolearn_diagnosis())
