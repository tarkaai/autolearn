#!/usr/bin/env python3
"""Manual test harness for Milestone 3 LLM chat sessions with real or mock OpenAI API."""

import os
import sys
import json
import time
import requests
from typing import Dict, Any, Optional

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


class AutoLearnTestHarness:
    """Test harness for AutoLearn chat sessions."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id: Optional[str] = None
    
    def test_server_health(self) -> bool:
        """Test if the server is running and healthy."""
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Server health check passed")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Is it running?")
            return False
    
    def test_mcp_spec(self) -> Dict[str, Any]:
        """Test the MCP specification endpoint."""
        try:
            response = requests.get(f"{self.base_url}/mcp")
            if response.status_code == 200:
                mcp_spec = response.json()
                print(f"✅ MCP spec retrieved successfully")
                print(f"   Schema version: {mcp_spec.get('schema_version')}")
                print(f"   Server: {mcp_spec.get('server_info', {}).get('name')}")
                print(f"   Available tools: {len(mcp_spec.get('tools', []))}")
                
                for tool in mcp_spec.get('tools', []):
                    func = tool.get('function', {})
                    print(f"     - {func.get('name')}: {func.get('description')}")
                
                return mcp_spec
            else:
                print(f"❌ MCP spec request failed: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ MCP spec request error: {e}")
            return {}
    
    def create_chat_session(self, name: str = "Test Session") -> Optional[str]:
        """Create a new chat session."""
        try:
            response = requests.post(
                f"{self.base_url}/sessions",
                json={"name": name}
            )
            if response.status_code == 200:
                data = response.json()
                session_id = data["session"]["id"]
                self.session_id = session_id
                print(f"✅ Created chat session: {session_id}")
                print(f"   Name: {name}")
                print(f"   Messages: {len(data['session']['messages'])}")
                return session_id
            else:
                print(f"❌ Failed to create session: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return None
    
    def send_message(self, content: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to the chat session."""
        if session_id is None:
            session_id = self.session_id
        
        if session_id is None:
            print("❌ No session ID available. Create a session first.")
            return {}
        
        try:
            print(f"\n💬 Sending message: '{content}'")
            response = requests.post(
                f"{self.base_url}/sessions/{session_id}/messages",
                json={"role": "user", "content": content}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Message sent successfully")
                
                if data.get("skill_generated"):
                    skill = data["skill_generated"]
                    print(f"🔧 Skill generated: {skill.get('name')} - {skill.get('description')}")
                
                return data
            else:
                print(f"❌ Failed to send message: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Message sending error: {e}")
            return {}
    
    def get_session_history(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the full session history."""
        if session_id is None:
            session_id = self.session_id
        
        if session_id is None:
            print("❌ No session ID available.")
            return {}
        
        try:
            response = requests.get(f"{self.base_url}/sessions/{session_id}")
            if response.status_code == 200:
                session = response.json()
                print(f"\n📜 Session History ({len(session['messages'])} messages):")
                
                for i, msg in enumerate(session["messages"]):
                    role = msg["role"]
                    content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                    print(f"   {i+1}. [{role.upper()}]: {content}")
                    
                    if msg.get("skill_generated"):
                        print(f"      🔧 Generated skill: {msg['skill_generated']}")
                
                return session
            else:
                print(f"❌ Failed to get session: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Session retrieval error: {e}")
            return {}
    
    def test_direct_skill_execution(self, skill_name: str = "echo", args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test direct skill execution."""
        if args is None:
            args = {"payload": "test data"}
        
        try:
            print(f"\n🔧 Testing direct skill execution: {skill_name}")
            response = requests.post(
                f"{self.base_url}/run",
                json={"name": skill_name, "args": args}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Skill executed successfully")
                print(f"   Success: {data.get('success')}")
                print(f"   Result: {data.get('result')}")
                return data
            else:
                print(f"❌ Skill execution failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Skill execution error: {e}")
            return {}
    
    def run_comprehensive_test(self):
        """Run a comprehensive test of all functionality."""
        print("🚀 Starting AutoLearn Milestone 3 Test Harness")
        print("=" * 60)
        
        # 1. Test server health
        if not self.test_server_health():
            print("❌ Server not available. Exiting.")
            return False
        
        # 2. Test MCP spec
        mcp_spec = self.test_mcp_spec()
        if not mcp_spec:
            print("❌ MCP spec not available. Exiting.")
            return False
        
        # 3. Test direct skill execution
        self.test_direct_skill_execution()
        
        # 4. Create chat session
        session_id = self.create_chat_session("Comprehensive Test Session")
        if not session_id:
            print("❌ Could not create session. Exiting.")
            return False
        
        # 5. Test basic chat
        self.send_message("Hello! Can you tell me what skills you have available?")
        time.sleep(1)  # Give the async processing time
        
        # 6. Test tool usage
        self.send_message("Please use the echo skill to repeat back the message 'Hello from AutoLearn!'")
        time.sleep(1)
        
        # 7. Test skill creation (if OpenAI is available)
        openai_available = bool(os.environ.get("OPENAI_API_KEY"))
        if openai_available:
            print("\n🤖 OpenAI API key detected - testing skill generation")
            self.send_message("create a skill that multiplies two numbers together")
            time.sleep(2)  # Skill generation takes longer
        else:
            print("\n⚠️  No OpenAI API key - skipping skill generation test")
        
        # 8. Get final session history
        self.get_session_history()
        
        print("\n" + "=" * 60)
        print("✅ Comprehensive test completed!")
        return True
    
    def run_interactive_mode(self):
        """Run in interactive mode for manual testing."""
        print("🤖 AutoLearn Interactive Test Mode")
        print("Commands: /help, /mcp, /session, /history, /direct <skill> <args>, /quit")
        print("=" * 60)
        
        if not self.test_server_health():
            print("❌ Server not available. Exiting.")
            return
        
        # Create initial session
        session_id = self.create_chat_session("Interactive Test Session")
        if not session_id:
            print("❌ Could not create session. Exiting.")
            return
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() in ["/quit", "/exit", "/q"]:
                    break
                elif user_input.lower() == "/help":
                    print("Available commands:")
                    print("  /mcp - Show MCP specification")
                    print("  /session - Show current session info")
                    print("  /history - Show session message history")
                    print("  /direct <skill> <args> - Execute skill directly")
                    print("  /quit - Exit interactive mode")
                    print("  Or just type a message to send to the chat")
                elif user_input.lower() == "/mcp":
                    self.test_mcp_spec()
                elif user_input.lower() == "/session":
                    print(f"Current session ID: {self.session_id}")
                elif user_input.lower() == "/history":
                    self.get_session_history()
                elif user_input.startswith("/direct"):
                    parts = user_input.split(" ", 2)
                    if len(parts) >= 2:
                        skill_name = parts[1]
                        args = {}
                        if len(parts) == 3:
                            try:
                                args = json.loads(parts[2])
                            except json.JSONDecodeError:
                                args = {"payload": parts[2]}
                        self.test_direct_skill_execution(skill_name, args)
                    else:
                        print("Usage: /direct <skill_name> [<json_args>]")
                elif user_input:
                    self.send_message(user_input)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n👋 Goodbye!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoLearn Milestone 3 Test Harness")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for the server")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--comprehensive", "-c", action="store_true", help="Run comprehensive test suite")
    
    args = parser.parse_args()
    
    harness = AutoLearnTestHarness(args.url)
    
    if args.interactive:
        harness.run_interactive_mode()
    elif args.comprehensive:
        harness.run_comprehensive_test()
    else:
        # Default: run comprehensive test
        harness.run_comprehensive_test()


if __name__ == "__main__":
    main()
