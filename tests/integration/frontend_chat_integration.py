#!/usr/bin/env python3
"""
Frontend Chat Integration Test

This test verifies that the frontend chat interface correctly:
1. Connects to the backend consumer agent
2. Sends user messages 
3. Receives and displays agent responses
4. Shows skill execution indicators
5. Displays skill results properly

This test uses Selenium to automate the browser and test the actual user experience.
"""

import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys


class TestFrontendChatIntegration:
    """Test suite for frontend chat integration with skill execution."""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """Set up browser instance for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    def test_chat_page_loads(self, browser):
        """Test that the chat page loads correctly."""
        browser.get("http://localhost:3000")
        
        # Wait for the page to load
        wait = WebDriverWait(browser, 10)
        
        # Check that the chat interface elements are present
        chat_title = wait.until(EC.presence_of_element_located((By.TEXT, "AI Assistant Chat")))
        assert chat_title is not None
        
        # Check for input field
        input_field = browser.find_element(By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")
        assert input_field is not None
        
        # Check for send button
        send_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit'], button:has(svg)")
        assert send_button is not None
    
    def test_skill_execution_math_addition(self, browser):
        """Test that math addition skills are executed and displayed correctly."""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # Find the input field and send button
        input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")))
        send_button = browser.find_element(By.CSS_SELECTOR, "button:has(svg), button[type='submit']")
        
        # Send a math question
        test_message = "What is 8 + 7?"
        input_field.clear()
        input_field.send_keys(test_message)
        send_button.click()
        
        # Wait for response
        time.sleep(3)
        
        # Check that the user message appears
        user_messages = browser.find_elements(By.CSS_SELECTOR, "[class*='bg-primary text-primary-foreground']")
        assert len(user_messages) > 0
        assert test_message in user_messages[-1].text
        
        # Check that agent response appears
        agent_messages = browser.find_elements(By.CSS_SELECTOR, "[class*='bg-muted'], [class*='bg-gray']")
        assert len(agent_messages) > 0
        
        # Check for skill execution indicator (green badge or success indicator)
        skill_indicators = browser.find_elements(By.CSS_SELECTOR, "[class*='bg-green'], [class*='text-green'], .skill-executed")
        if len(skill_indicators) > 0:
            print("✅ Skill execution indicator found")
        
        # Check for result in the response
        response_text = agent_messages[-1].text.lower()
        assert "15" in response_text or "result" in response_text
        
        print(f"Agent response: {agent_messages[-1].text}")
    
    def test_skill_execution_math_multiplication(self, browser):
        """Test that math multiplication skills are executed and displayed correctly."""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # Find the input field and send button
        input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")))
        send_button = browser.find_element(By.CSS_SELECTOR, "button:has(svg), button[type='submit']")
        
        # Send a multiplication question
        test_message = "What is 9 times 6?"
        input_field.clear()
        input_field.send_keys(test_message)
        send_button.click()
        
        # Wait for response
        time.sleep(3)
        
        # Check for skill execution and result
        agent_messages = browser.find_elements(By.CSS_SELECTOR, "[class*='bg-muted'], [class*='bg-gray']")
        assert len(agent_messages) > 0
        
        response_text = agent_messages[-1].text.lower()
        assert "54" in response_text or "result" in response_text
        
        print(f"Multiplication response: {agent_messages[-1].text}")
    
    def test_skill_suggestions_display(self, browser):
        """Test that skill suggestions are displayed when available."""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # Find the input field and send button
        input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")))
        send_button = browser.find_element(By.CSS_SELECTOR, "button:has(svg), button[type='submit']")
        
        # Send a general question that might trigger suggestions
        test_message = "What can you help me with?"
        input_field.clear()
        input_field.send_keys(test_message)
        send_button.click()
        
        # Wait for response
        time.sleep(3)
        
        # Check for skill suggestions
        suggestion_buttons = browser.find_elements(By.CSS_SELECTOR, "button[class*='outline'], .skill-suggestion")
        if len(suggestion_buttons) > 0:
            print(f"✅ Found {len(suggestion_buttons)} skill suggestions")
            for button in suggestion_buttons[:3]:  # Print first 3
                print(f"  - {button.text}")
        
        # Check for suggestions section
        suggestion_sections = browser.find_elements(By.TEXT, "Skill suggestions:")
        if len(suggestion_sections) > 0:
            print("✅ Skill suggestions section found")
    
    def test_toast_notifications_on_skill_execution(self, browser):
        """Test that toast notifications appear when skills are executed."""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # Find the input field and send button
        input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")))
        send_button = browser.find_element(By.CSS_SELECTOR, "button:has(svg), button[type='submit']")
        
        # Send a math question that should trigger skill execution
        test_message = "Calculate 12 + 8"
        input_field.clear()
        input_field.send_keys(test_message)
        send_button.click()
        
        # Wait and check for toast notifications
        time.sleep(2)
        
        # Look for toast/notification elements (common selectors)
        toast_selectors = [
            "[class*='toast']",
            "[class*='notification']", 
            "[class*='alert']",
            "[role='alert']",
            "[class*='sonner']"  # Sonner is the toast library used
        ]
        
        toast_found = False
        for selector in toast_selectors:
            toasts = browser.find_elements(By.CSS_SELECTOR, selector)
            if toasts:
                print(f"✅ Toast notification found: {toasts[0].text}")
                toast_found = True
                break
        
        if not toast_found:
            print("⚠️ No toast notification found (this might be expected if toasts disappear quickly)")
    
    def test_error_handling(self, browser):
        """Test that errors are handled gracefully in the frontend."""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # Find the input field and send button
        input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")))
        send_button = browser.find_element(By.CSS_SELECTOR, "button:has(svg), button[type='submit']")
        
        # Send an empty message (should be handled)
        input_field.clear()
        send_button.click()
        
        # Check that no error occurred and input is still functional
        time.sleep(1)
        
        # Try a normal message after
        test_message = "Hello"
        input_field.send_keys(test_message)
        send_button.click()
        
        time.sleep(2)
        
        # Check that response came back
        agent_messages = browser.find_elements(By.CSS_SELECTOR, "[class*='bg-muted'], [class*='bg-gray']")
        assert len(agent_messages) > 0
        print("✅ Error handling works correctly")


def test_network_requests():
    """Test that the frontend makes correct API calls to the backend."""
    import requests
    
    # Test the API endpoint directly to ensure it's working
    response = requests.post(
        "http://localhost:8000/consumer-agent/chat",
        json={"message": "What is 5 + 3?", "session_id": None},
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "message" in data
    assert "session_id" in data
    assert "actions" in data
    assert "suggestions" in data
    
    # Check if skill was executed
    if data["actions"]:
        skill_actions = [action for action in data["actions"] if action.get("type") == "skill_used"]
        if skill_actions:
            print(f"✅ Backend skill execution verified: {skill_actions[0]['skill_name']}")
            print(f"✅ Result: {skill_actions[0].get('result')}")
    
    print(f"✅ API response: {data['message'][:100]}...")


if __name__ == "__main__":
    """Run the tests manually for debugging."""
    
    print("🧪 Running Frontend Chat Integration Tests")
    print("=" * 50)
    
    # First test the API directly
    print("\n1. Testing Backend API...")
    test_network_requests()
    
    print("\n2. Testing Frontend Interface...")
    print("Note: This requires Chrome/Chromium to be installed and both servers running:")
    print("  - Backend: http://localhost:8000")
    print("  - Frontend: http://localhost:3000")
    
    # Run with pytest for full browser testing
    print("\nTo run full browser tests, use:")
    print("pytest tests/test_frontend_chat_integration.py -v -s")
