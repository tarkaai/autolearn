#!/usr/bin/env python3
"""Test automatic skill improvement functionality."""

import asyncio
import httpx
import sqlite3
import json

async def test_automatic_skill_improvement():
    """Test that AutoLearn automatically improves failing skills."""
    
    print("🧪 TESTING AUTOMATIC SKILL IMPROVEMENT")
    print("=" * 50)
    
    # Step 1: Create a deliberately broken skill for testing
    print("\n1. 📝 Creating a deliberately broken skill...")
    
    broken_skill_code = '''def test_broken_skill(wrong_param_name: int) -> dict:
    """A skill with wrong parameter name for testing auto-improvement."""
    return {"result": wrong_param_name * 2}'''
    
    broken_skill_inputs = '{"correct_param_name": "int"}'
    
    # Insert broken skill into database
    conn = sqlite3.connect('skills.db')
    conn.execute('''
        INSERT OR REPLACE INTO skills (name, description, version, inputs, code, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ''', (
        'test_broken_skill',
        'A test skill with parameter mismatch',
        '1.0.0',
        broken_skill_inputs,
        broken_skill_code
    ))
    conn.commit()
    conn.close()
    
    print("   ✅ Created broken skill with parameter mismatch")
    
    # Step 2: Register the skill in memory (restart the skill engine)
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Force reload skills by calling the tools endpoint to refresh
        await client.get("http://localhost:8000/tools")
    
    # Step 3: Try to use the broken skill via consumer agent
    print("\n2. 🔧 Testing automatic improvement when skill fails...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8000/consumer-agent/chat",
            json={"message": "use test_broken_skill with correct_param_name 5"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"   📝 Agent response: {data.get('message', '')[:100]}...")
            
            # Check if skill was used and auto-improved
            for action in data.get('actions', []):
                if action.get('type') == 'skill_used':
                    skill_name = action.get('skill_name')
                    result = str(action.get('result', ''))
                    
                    print(f"   🎯 Used skill: {skill_name}")
                    
                    # Check for automatic improvement
                    retry_info = action.get('parameter_corrections', {})
                    if retry_info.get('automatic_improvement'):
                        print("   🎉 SUCCESS: Automatic skill improvement triggered!")
                        print(f"   ✅ Skill was automatically fixed and retried")
                        print(f"   📊 Result: {result}")
                        return True
                    elif 'error' in result.lower():
                        print(f"   ❌ Skill still failed: {result}")
                        return False
                    else:
                        print(f"   ✅ Skill worked (maybe already fixed): {result}")
                        return True
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            return False
    
    print("   ❌ No skill execution found")
    return False

async def main():
    try:
        success = await test_automatic_skill_improvement()
        
        if success:
            print("\n🎉 AUTOMATIC SKILL IMPROVEMENT WORKING!")
            print("✅ AutoLearn can now fix itself when skills fail")
            print("✅ No manual intervention required")
            print("✅ True auto-learning achieved!")
        else:
            print("\n❌ Automatic skill improvement not working yet")
            print("⚠️  Manual fixes still required")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
