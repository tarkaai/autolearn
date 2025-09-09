#!/usr/bin/env python3
"""Test conversation context and memory issues."""

import asyncio
import httpx
import json

async def test_conversation_context():
    """Test that the agent maintains conversation context properly."""
    
    print("🧪 Testing Conversation Context and Memory")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        session_id = None
        
        try:
            # First message: Ask about fibonacci
            print("\n📤 Message 1: 'calculate the fibonacci sequence'")
            response1 = await client.post(
                "http://localhost:8000/consumer-agent/chat",
                json={
                    "message": "calculate the fibonacci sequence",
                    "session_id": session_id
                }
            )
            
            if response1.status_code != 200:
                print(f"❌ Request failed with status {response1.status_code}")
                return
                
            data1 = response1.json()
            session_id = data1.get('session_id')
            
            print(f"📝 Agent Response 1:")
            print(f"   {data1.get('message', 'No message')}")
            
            # Check if agent asked for clarification
            message1 = data1.get('message', '').lower()
            asked_for_terms = any(word in message1 for word in ['how many', 'terms', 'numbers', 'specify'])
            
            print(f"   Asked for number of terms: {'✅' if asked_for_terms else '❌'}")
            
            # Second message: Provide the missing information
            print(f"\n📤 Message 2: 'to 3' (should be interpreted as 3 terms)")
            response2 = await client.post(
                "http://localhost:8000/consumer-agent/chat",
                json={
                    "message": "to 3",
                    "session_id": session_id
                }
            )
            
            if response2.status_code != 200:
                print(f"❌ Request failed with status {response2.status_code}")
                return
                
            data2 = response2.json()
            
            print(f"📝 Agent Response 2:")
            print(f"   {data2.get('message', 'No message')}")
            
            print(f"\n🔧 Actions Taken:")
            for action in data2.get('actions', []):
                action_type = action.get('type')
                if action_type == 'skill_used':
                    skill_name = action.get('skill_name')
                    result = action.get('result')
                    print(f"   ✅ Used skill: {skill_name}")
                    print(f"      Result: {result}")
                elif action_type == 'skill_generated':
                    skill_name = action.get('skill_name')
                    print(f"   🆕 Created skill: {skill_name}")
            
            # Analysis
            print(f"\n🔍 Context Analysis:")
            
            # Check if it used the fibonacci skill correctly
            used_fibonacci = any(
                action.get('type') == 'skill_used' and 
                action.get('skill_name') == 'calculate_fibonacci_sequence'
                for action in data2.get('actions', [])
            )
            
            # Check if it created unnecessary skills
            created_skills = [
                action.get('skill_name') for action in data2.get('actions', [])
                if action.get('type') == 'skill_generated'
            ]
            
            print(f"   Used fibonacci skill: {'✅' if used_fibonacci else '❌'}")
            print(f"   Created unnecessary skills: {created_skills if created_skills else 'None ✅'}")
            
            if used_fibonacci and not created_skills:
                print(f"\n🎉 SUCCESS: Agent maintained context and used correct skill!")
            elif created_skills:
                print(f"\n⚠️  ISSUE: Agent created unnecessary skills instead of using context")
                print(f"   Problem: Agent should have connected 'to 3' with previous fibonacci request")
                print(f"   Solution: Improve conversation context analysis")
            else:
                print(f"\n❌ FAILURE: Agent didn't handle the request properly")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conversation_context())
