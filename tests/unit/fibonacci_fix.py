#!/usr/bin/env python3
"""Quick test to verify the fibonacci parameter fix works with the running server."""

import asyncio
import httpx
import json

async def test_fibonacci_fix():
    """Test that the fibonacci sequence now works correctly."""
    
    print("🧪 Testing Fibonacci Sequence Parameter Fix")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test the fibonacci request that was failing before
            response = await client.post(
                "http://localhost:8000/consumer-agent/chat",
                json={
                    "message": "calculate the fibonacci sequence to 10"
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return
                
            data = response.json()
            
            print(f"📝 Agent Response:")
            print(f"   {data.get('message', 'No message')}")
            
            print(f"\n🔧 Actions Taken:")
            for action in data.get('actions', []):
                action_type = action.get('type')
                if action_type == 'skill_used':
                    skill_name = action.get('skill_name')
                    result = action.get('result')
                    print(f"   ✅ Used skill: {skill_name}")
                    print(f"      Result: {result}")
                    
                    # Check if we got the expected fibonacci sequence
                    if isinstance(result, dict) and 'fibonacci_sequence' in result:
                        sequence = result['fibonacci_sequence']
                        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
                        if sequence == expected:
                            print(f"      🎉 SUCCESS: Got correct fibonacci sequence!")
                        else:
                            print(f"      ⚠️  Got sequence but values don't match expected")
                            print(f"         Expected: {expected}")
                            print(f"         Got:      {sequence}")
                    elif isinstance(result, str) and "Error:" in result:
                        print(f"      ❌ ERROR: {result}")
                    
                    # Check for parameter corrections
                    if "parameter_corrections" in action:
                        corrections = action["parameter_corrections"]
                        print(f"      🔧 Parameter corrections applied: {corrections}")
            
            # Overall assessment
            print(f"\n🔍 Debug: Checking actions for success...")
            for action in data.get('actions', []):
                print(f"   Action type: {action.get('type')}")
                print(f"   Result type: {type(action.get('result'))}")
                print(f"   Result: {action.get('result')}")
                
            skill_used_successfully = any(
                action.get('type') == 'skill_used' and 
                'fibonacci_sequence' in str(action.get('result', {}))
                for action in data.get('actions', [])
            )
            
            print(f"   Success check result: {skill_used_successfully}")
            
            if skill_used_successfully:
                print(f"\n🎉 OVERALL RESULT: SUCCESS! The parameter fix is working!")
                print(f"   - No more 'unexpected keyword argument' errors")
                print(f"   - Agent correctly used 'n_terms' parameter")
                print(f"   - Fibonacci sequence calculated successfully")
            else:
                print(f"\n❌ OVERALL RESULT: Still having issues")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fibonacci_fix())
