#!/usr/bin/env python3
"""
MCP HTTP endpoint test for AutoLearn server.

Tests the MCP JSON-RPC over HTTP implementation.
"""

import requests
import json
import os
from typing import Dict, Any


class MCPHTTPTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"
    
    def send_mcp_request(self, method: str, params: Dict[str, Any] = None, 
                        request_id: str = "test-1") -> Dict[str, Any]:
        """Send an MCP JSON-RPC request over HTTP."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params:
            message["params"] = params
        
        print(f"🔄 Sending MCP request: {method}")
        print(f"   Request: {json.dumps(message, indent=2)}")
        
        response = requests.post(
            self.mcp_endpoint,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"   Error: {response.text}")
            return {"error": response.text}
    
    def test_initialize(self) -> bool:
        """Test MCP initialization handshake."""
        print("\n🔧 Testing MCP Initialization")
        print("-" * 40)
        
        params = {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "autolearn-test-client",
                "version": "1.0.0"
            }
        }
        
        response = self.send_mcp_request("initialize", params)
        
        if "result" in response:
            result = response["result"]
            print("✅ Initialization successful")
            print(f"   Server: {result.get('serverInfo', {}).get('name', 'unknown')}")
            print(f"   Version: {result.get('serverInfo', {}).get('version', 'unknown')}")
            print(f"   Protocol: {result.get('protocolVersion', 'unknown')}")
            return True
        else:
            print("❌ Initialization failed")
            return False
    
    def test_tools_list(self) -> bool:
        """Test MCP tools/list request."""
        print("\n🛠️  Testing MCP Tools List")
        print("-" * 40)
        
        response = self.send_mcp_request("tools/list")
        
        if "result" in response:
            result = response["result"]
            tools = result.get("tools", [])
            print(f"✅ Tools list successful - {len(tools)} tools available")
            for tool in tools:
                print(f"   - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')}")
            return True
        else:
            print("❌ Tools list failed")
            return False
    
    def test_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Test MCP tools/call request."""
        print(f"\n⚡ Testing MCP Tool Call: {tool_name}")
        print("-" * 40)
        
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        
        response = self.send_mcp_request("tools/call", params)
        
        if "result" in response:
            result = response["result"]
            content = result.get("content", [])
            is_error = result.get("isError", False)
            
            if is_error:
                print("⚠️  Tool execution completed with error")
            else:
                print("✅ Tool execution successful")
            
            for item in content:
                if item.get("type") == "text":
                    print(f"   Result: {item.get('text', 'no text')}")
            
            return not is_error
        else:
            print("❌ Tool call failed")
            return False


def main():
    print("🔍 AutoLearn MCP HTTP Endpoint Test")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ AutoLearn server is running")
        else:
            print("❌ AutoLearn server not responding")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    tester = MCPHTTPTester()
    
    # Test sequence
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Initialize
    total_tests += 1
    if tester.test_initialize():
        tests_passed += 1
    
    # Test 2: List tools
    total_tests += 1
    if tester.test_tools_list():
        tests_passed += 1
    
    # Test 3: Call echo tool (if available)
    total_tests += 1
    if tester.test_tool_call("echo", {"payload": "Hello MCP!"}):
        tests_passed += 1
    
    # Test 4: Call multiply_numbers tool (if available)
    total_tests += 1  
    if tester.test_tool_call("multiply_numbers", {"a": 6, "b": 7}):
        tests_passed += 1
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All MCP HTTP tests passed!")
    else:
        print("⚠️  Some tests failed - check the output above")


if __name__ == "__main__":
    main()
