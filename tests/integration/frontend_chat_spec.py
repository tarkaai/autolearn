#!/usr/bin/env python3
"""
Frontend Chat Integration Test Specification

This specification outlines how to test the frontend chat functionality
to ensure skills are being executed properly.

Run this test with: python tests/test_frontend_chat_spec.py
"""

import asyncio
import json
import requests
import time
from typing import Dict, Any, List


class FrontendChatTestSpec:
    """Test specification for frontend chat integration."""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.test_results = []
    
    def log_result(self, test_name: str, passed: bool, message: str, details: Dict[str, Any] = None):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message,
            "details": details or {}
        })
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    def test_backend_api_connection(self):
        """Test 1: Verify backend API is accessible and working."""
        test_name = "Backend API Connection"
        
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_result(test_name, True, "Backend API is accessible")
            else:
                self.log_result(test_name, False, f"Backend returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.log_result(test_name, False, f"Cannot connect to backend: {e}")
    
    def test_consumer_agent_chat_endpoint(self):
        """Test 2: Verify consumer agent chat endpoint works."""
        test_name = "Consumer Agent Chat Endpoint"
        
        try:
            payload = {
                "message": "What is 5 + 3?",
                "session_id": None
            }
            
            response = requests.post(
                f"{self.backend_url}/consumer-agent/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["message", "session_id", "actions", "suggestions"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result(test_name, False, f"Missing fields: {missing_fields}")
                    return
                
                # Check if skill was executed
                skill_actions = [action for action in data["actions"] if action.get("type") == "skill_used"]
                
                if skill_actions:
                    skill_name = skill_actions[0].get("skill_name")
                    result = skill_actions[0].get("result")
                    self.log_result(
                        test_name, 
                        True, 
                        f"Skill '{skill_name}' executed successfully",
                        {
                            "skill_name": skill_name,
                            "result": result,
                            "response_length": len(data["message"]),
                            "actions_count": len(data["actions"])
                        }
                    )
                else:
                    self.log_result(test_name, False, "No skills were executed", {"response": data["message"][:100]})
                    
            else:
                self.log_result(test_name, False, f"API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result(test_name, False, f"Request failed: {e}")
        except json.JSONDecodeError as e:
            self.log_result(test_name, False, f"Invalid JSON response: {e}")
    
    def test_multiple_math_operations(self):
        """Test 3: Test multiple math operations to verify skill execution."""
        test_name = "Multiple Math Operations"
        
        test_cases = [
            ("What is 7 + 5?", "add_two_numbers", 12.0),
            ("Calculate 8 * 6", "multiply_numbers", 48.0),
            ("What is 15 plus 25?", "add_two_numbers", 40.0),
        ]
        
        results = []
        
        for question, expected_skill, expected_result in test_cases:
            try:
                response = requests.post(
                    f"{self.backend_url}/consumer-agent/chat",
                    json={"message": question, "session_id": None},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    skill_actions = [action for action in data["actions"] if action.get("type") == "skill_used"]
                    
                    if skill_actions:
                        skill_name = skill_actions[0].get("skill_name")
                        result = skill_actions[0].get("result")
                        
                        skill_correct = expected_skill in skill_name
                        result_correct = abs(float(result) - expected_result) < 0.01
                        
                        results.append({
                            "question": question,
                            "skill_used": skill_name,
                            "result": result,
                            "skill_correct": skill_correct,
                            "result_correct": result_correct,
                            "overall_correct": skill_correct and result_correct
                        })
                    else:
                        results.append({
                            "question": question,
                            "error": "No skill executed"
                        })
                else:
                    results.append({
                        "question": question,
                        "error": f"API error {response.status_code}"
                    })
                    
            except Exception as e:
                results.append({
                    "question": question,
                    "error": str(e)
                })
        
        successful_tests = [r for r in results if r.get("overall_correct", False)]
        success_rate = len(successful_tests) / len(test_cases)
        
        if success_rate >= 0.8:  # 80% success rate
            self.log_result(
                test_name, 
                True, 
                f"{len(successful_tests)}/{len(test_cases)} operations successful",
                {"success_rate": f"{success_rate:.1%}", "results": results}
            )
        else:
            self.log_result(
                test_name, 
                False, 
                f"Only {len(successful_tests)}/{len(test_cases)} operations successful",
                {"success_rate": f"{success_rate:.1%}", "results": results}
            )
    
    def test_frontend_server_accessibility(self):
        """Test 4: Verify frontend server is accessible."""
        test_name = "Frontend Server Accessibility"
        
        try:
            response = requests.get(f"{self.frontend_url}", timeout=5)
            if response.status_code == 200:
                # Check if it contains React/Next.js content
                content = response.text.lower()
                if "react" in content or "next" in content or "ai assistant" in content:
                    self.log_result(test_name, True, "Frontend server is accessible and serving content")
                else:
                    self.log_result(test_name, True, "Frontend server accessible but content unclear")
            else:
                self.log_result(test_name, False, f"Frontend returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.log_result(test_name, False, f"Cannot connect to frontend: {e}")
    
    def test_api_client_configuration(self):
        """Test 5: Verify API client configuration in frontend."""
        test_name = "API Client Configuration"
        
        # Read the API client file to check configuration
        try:
            with open("frontend/src/lib/api-client.ts", "r") as f:
                content = f.read()
            
            # Check for correct backend URL
            if "localhost:8000" in content or "NEXT_PUBLIC_BACKEND_URL" in content:
                self.log_result(test_name, True, "API client configured with correct backend URL")
            else:
                self.log_result(test_name, False, "API client may have incorrect backend URL configuration")
                
        except FileNotFoundError:
            self.log_result(test_name, False, "API client file not found")
        except Exception as e:
            self.log_result(test_name, False, f"Error reading API client file: {e}")
    
    def test_chat_component_structure(self):
        """Test 6: Verify chat component has skill execution features."""
        test_name = "Chat Component Structure"
        
        try:
            with open("frontend/src/components/user-chat.tsx", "r") as f:
                content = f.read()
            
            # Check for skill execution features
            features = {
                "actions_handling": "actions" in content and "skill_used" in content,
                "skill_indicators": "bg-green" in content or "skill" in content.lower(),
                "toast_notifications": "toast" in content.lower(),
                "suggestions_display": "suggestions" in content and "Button" in content
            }
            
            passed_features = sum(features.values())
            total_features = len(features)
            
            if passed_features >= 3:  # At least 3 out of 4 features
                self.log_result(
                    test_name, 
                    True, 
                    f"{passed_features}/{total_features} skill execution features found",
                    features
                )
            else:
                self.log_result(
                    test_name, 
                    False, 
                    f"Only {passed_features}/{total_features} skill execution features found",
                    features
                )
                
        except FileNotFoundError:
            self.log_result(test_name, False, "Chat component file not found")
        except Exception as e:
            self.log_result(test_name, False, f"Error reading chat component: {e}")
    
    def run_all_tests(self):
        """Run all tests and provide a summary."""
        print("🧪 Frontend Chat Integration Test Specification")
        print("=" * 60)
        print("\nTesting frontend chat functionality and skill execution...")
        print("\nPrerequisites:")
        print("  ✓ Backend server running on http://localhost:8000")
        print("  ✓ Frontend server running on http://localhost:3000")
        print("  ✓ OpenAI API key configured")
        print("\nRunning tests...")
        print("-" * 60)
        
        # Run all tests
        self.test_backend_api_connection()
        self.test_consumer_agent_chat_endpoint()
        self.test_multiple_math_operations()
        self.test_frontend_server_accessibility()
        self.test_api_client_configuration()
        self.test_chat_component_structure()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)} ✅")
        print(f"Failed: {len(failed_tests)} ❌")
        print(f"Success Rate: {len(passed_tests)/len(self.test_results):.1%}")
        
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['message']}")
        
        if len(passed_tests) >= len(self.test_results) * 0.8:
            print(f"\n🎉 OVERALL RESULT: PASS")
            print("The frontend chat functionality appears to be working correctly!")
        else:
            print(f"\n⚠️  OVERALL RESULT: NEEDS ATTENTION")
            print("Some issues were found that may affect frontend chat functionality.")
        
        return len(passed_tests) >= len(self.test_results) * 0.8


def manual_test_instructions():
    """Provide manual testing instructions for user verification."""
    print("\n" + "=" * 60)
    print("🔧 MANUAL TESTING INSTRUCTIONS")
    print("=" * 60)
    print("""
To manually verify the frontend chat functionality:

1. 📱 Open Browser:
   • Navigate to http://localhost:3000
   • Verify the chat interface loads

2. 🧮 Test Math Operations:
   • Type: "What is 15 + 25?"
   • Expected: Agent response with result "40"
   • Look for: Green skill execution indicator
   • Check: Success toast notification

3. 🔄 Test Multiple Skills:
   • Type: "Calculate 7 times 8"
   • Type: "What is 12 plus 18?"
   • Verify: Different skills are used (multiply vs add)

4. 🎯 Check Visual Indicators:
   • Look for: Green badges showing executed skills
   • Verify: Skill names and results are displayed
   • Check: Toast notifications appear briefly

5. 💡 Test Suggestions:
   • Type: "What can you help me with?"
   • Look for: Skill suggestion buttons
   • Click: A suggestion button to test interaction

6. 🔍 Developer Console:
   • Open browser dev tools (F12)
   • Check: No JavaScript errors in console
   • Monitor: Network requests to /consumer-agent/chat

Expected Behavior:
✅ Skills execute automatically for math questions
✅ Results display clearly in the chat
✅ Visual indicators show which skills were used
✅ Toast notifications confirm skill execution
✅ No errors in browser console
""")


if __name__ == "__main__":
    # Run the test specification
    test_spec = FrontendChatTestSpec()
    success = test_spec.run_all_tests()
    
    # Provide manual testing instructions
    manual_test_instructions()
    
    # Exit with appropriate code
    exit(0 if success else 1)
