#!/usr/bin/env python3
"""
Debug script to test the consumer agent MCP client functionality.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.consumer_agent import MCPClient, ConsumerAgent

async def test_mcp_client():
    """Test MCP client functionality."""
    print("Testing MCP Client...")
    
    async with MCPClient("http://localhost:8000/mcp") as mcp:
        try:
            print("1. Testing MCP initialization...")
            init_result = await mcp.initialize()
            print(f"   Initialization successful: {init_result}")
            
            print("2. Testing tools list...")
            tools = await mcp.list_tools()
            print(f"   Found {len(tools)} tools:")
            for tool in tools:
                print(f"     - {tool['name']}: {tool.get('description', 'No description')}")
            
            print("3. Testing tool execution...")
            if tools:
                # Try to execute the calculator tool
                calc_tool = next((t for t in tools if t['name'] == 'calculator'), None)
                if calc_tool:
                    result = await mcp.call_tool('calculator', {
                        'operation': 'add',
                        'a': 25,
                        'b': 17
                    })
                    print(f"   Calculator result: {result}")
                else:
                    print("   No calculator tool found")
            
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

async def test_consumer_agent():
    """Test consumer agent functionality."""
    print("\nTesting Consumer Agent...")
    
    agent = ConsumerAgent()
    
    try:
        print("1. Testing conversation start...")
        session_id = await agent.start_conversation("debug_user")
        print(f"   Session started: {session_id}")
        
        print("2. Testing chat...")
        response = await agent.chat(session_id, "Can you calculate 25 + 17 for me?")
        print(f"   Response: {response}")
        
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug function."""
    print("=== Debug Consumer Agent ===")
    
    await test_mcp_client()
    await test_consumer_agent()

if __name__ == "__main__":
    asyncio.run(main())
