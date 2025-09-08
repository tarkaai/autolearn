#!/usr/bin/env python3
"""
Focused test for OpenAI function calling integration.
Tests specifically whether the LLM uses available MCP tools.
"""

import requests
import json
import os
from typing import Dict, Any

class FunctionCallingTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        
    def create_test_session(self) -> str:
        """Create a test session for function calling tests."""
        response = requests.post(f"{self.base_url}/sessions", json={
            "name": "Function Calling Test",
            "description": "Testing OpenAI function calling with MCP tools"
        })
        if response.status_code == 200:
            session_data = response.json()
            self.session_id = session_data["id"]
            print(f"✅ Created test session: {self.session_id}")
            return self.session_id
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            return None
    
    def get_mcp_tools(self) -> Dict[str, Any]:
        """Get the MCP specification to see available tools."""
        response = requests.get(f"{self.base_url}/mcp")
        if response.status_code == 200:
            mcp_spec = response.json()
            tools = mcp_spec.get("tools", [])
            print(f"✅ MCP Tools Available: {len(tools)}")
            for tool in tools:
                func = tool.get("function", {})
                print(f"   - {func.get('name')}: {func.get('description')}")
            return mcp_spec
        else:
            print(f"❌ Failed to get MCP spec: {response.status_code}")
            return {}
    
    def send_message_and_analyze(self, message: str, expected_tool: str = None) -> Dict[str, Any]:
        """Send a message and analyze the response for function calling."""
        if not self.session_id:
            print("❌ No session created")
            return {}
            
        # Send the message
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/messages",
            json={"role": "user", "content": message}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to send message: {response.status_code}")
            return {}
        
        # Get the session to see the response
        session_response = requests.get(f"{self.base_url}/sessions/{self.session_id}")
        if session_response.status_code != 200:
            print(f"❌ Failed to get session: {session_response.status_code}")
            return {}
            
        session_data = session_response.json()
        messages = session_data.get("messages", [])
        
        # Find the assistant response
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        if not assistant_messages:
            print("❌ No assistant response found")
            return {}
            
        last_response = assistant_messages[-1]
        content = last_response.get("content", "")
        
        print(f"\n📨 User: {message}")
        print(f"🤖 Assistant: {content[:100]}{'...' if len(content) > 100 else ''}")
        
        # Analyze if function was called
        analysis = {
            "message": message,
            "response": content,
            "expected_tool": expected_tool,
            "used_function": False,
            "is_echo_response": "I received your message" in content,
            "mentions_tools": any(tool in content.lower() for tool in ["echo", "multiply", "skill", "function"]),
        }
        
        # Check for function usage indicators
        if expected_tool and expected_tool.lower() in content.lower():
            analysis["mentions_expected_tool"] = True
        
        # Look for actual function execution results
        if any(phrase in content.lower() for phrase in ["result:", "output:", "executed", "called"]):
            analysis["shows_execution"] = True
        
        return analysis

def main():
    print("🔍 AutoLearn Function Calling Test")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment")
        return
    
    tester = FunctionCallingTester()
    
    # Test 1: Check server health
    try:
        response = requests.get(f"{tester.base_url}/health")
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server not responding")
            return
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return
    
    # Test 2: Get MCP tools
    mcp_spec = tester.get_mcp_tools()
    if not mcp_spec.get("tools"):
        print("❌ No MCP tools available")
        return
    
    # Test 3: Create session
    if not tester.create_test_session():
        return
    
    print("\n🧪 Function Calling Tests")
    print("-" * 30)
    
    # Test cases designed to trigger function calling
    test_cases = [
        {
            "message": "What skills do you have available?",
            "expected_tool": None,
            "description": "Should list available skills/tools"
        },
        {
            "message": "Use the echo skill to repeat 'Hello AutoLearn!'",
            "expected_tool": "echo",
            "description": "Direct request to use echo function"
        },
        {
            "message": "Please call the echo function with the text 'Function calling test'",
            "expected_tool": "echo", 
            "description": "Explicit function call request"
        },
        {
            "message": "Can you demonstrate the multiply_numbers skill by multiplying 7 and 6?",
            "expected_tool": "multiply_numbers",
            "description": "Request to use multiply function"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['description']}")
        result = tester.send_message_and_analyze(
            test_case["message"], 
            test_case["expected_tool"]
        )
        results.append(result)
        
        # Analysis
        if result.get("is_echo_response"):
            print("⚠️  Got echo response - LLM not using functions!")
        elif result.get("used_function"):
            print("✅ Function appears to have been called")
        elif result.get("mentions_tools"):
            print("🤔 Mentions tools but unclear if function was called")
        else:
            print("❌ No function calling detected")
    
    # Summary
    print("\n📊 SUMMARY")
    print("=" * 30)
    echo_responses = sum(1 for r in results if r.get("is_echo_response", False))
    function_calls = sum(1 for r in results if r.get("used_function", False))
    
    print(f"Total tests: {len(results)}")
    print(f"Echo responses: {echo_responses}")
    print(f"Function calls: {function_calls}")
    
    if echo_responses > 0:
        print("🚨 ISSUE: LLM giving echo responses instead of using functions")
        print("   This indicates the function calling integration needs debugging")
    
    if function_calls == 0:
        print("🚨 CRITICAL: No function calling detected in any test")
        print("   The OpenAI function calling setup is not working")
    else:
        print("✅ Function calling appears to be working!")

if __name__ == "__main__":
    main()
