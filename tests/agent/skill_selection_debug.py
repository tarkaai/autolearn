#!/usr/bin/env python3
"""
Debug why the consumer agent isn't selecting the fibonacci skill.
"""

import asyncio
import json
import subprocess
import time
import sys
from backend.consumer_agent import ConsumerAgent

async def debug_skill_selection():
    """Debug the skill selection process."""
    
    # Start the backend server
    print("🚀 Starting backend server...")
    server_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app:app", "--port", "8000"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    
    try:
        # Initialize consumer agent
        agent = ConsumerAgent()
        session_id = await agent.start_conversation("debug_user")
        
        # Check what tools are available
        from backend.consumer_agent import MCPClient
        async with MCPClient(agent.mcp_server_url) as mcp:
            available_tools = await mcp.list_tools()
            
        print(f"\n🔍 Available tools: {len(available_tools)}")
        for tool in available_tools:
            if "fibonacci" in tool['name'].lower():
                print(f"  📋 {tool['name']}: {tool.get('description', 'No description')}")
                if 'inputSchema' in tool:
                    params = tool['inputSchema'].get('properties', {})
                    print(f"     Parameters: {list(params.keys())}")
        
        # Test the analysis process
        user_message = "Calculate fibonacci sequence for 5 terms and multiply by 2"
        print(f"\n🧪 Testing message: '{user_message}'")
        
        # Get the skill analysis
        async with MCPClient(agent.mcp_server_url) as mcp:
            analysis = await agent._analyze_skill_requirements(user_message, available_tools, {})
            
        print(f"\n📊 Analysis result:")
        print(f"  Needs skill: {analysis.get('needs_skill', False)}")
        print(f"  Reasoning: {analysis.get('reasoning', 'No reasoning')}")
        
        if 'relevant_skills' in analysis:
            print(f"  Relevant skills: {analysis['relevant_skills']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up server
        print("\n🛑 Stopping backend server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    success = asyncio.run(debug_skill_selection())
    sys.exit(0 if success else 1)
