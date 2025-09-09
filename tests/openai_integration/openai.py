#!/usr/bin/env python3
"""Simple test to verify OpenAI integration is working."""

import os
import sys
import pytest
from dotenv import load_dotenv

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv()

from backend.openai_client import create_default_client

def test_openai_integration():
    """Test basic OpenAI integration."""
    print("Testing OpenAI integration...")
    
    # Check if API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        pytest.skip("OPENAI_API_KEY not found in environment")
    
    print(f"✅ OPENAI_API_KEY found: {api_key[:10]}...")
    
    # Create client
    try:
        client = create_default_client()
        print("✅ OpenAI client created successfully")
        print(f"   Model: {client.config.model_name}")
    except Exception as e:
        print(f"❌ Failed to create OpenAI client: {e}")
        pytest.fail(f"Failed to create OpenAI client: {e}")
    
    # Test basic completion
    try:
        response = client.client.chat.completions.create(
            model=client.config.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in a friendly way."}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        assistant_response = response.choices[0].message.content
        print("✅ OpenAI API call successful")
        print(f"   Response: {assistant_response}")
        assert assistant_response is not None, "OpenAI should return a response"
        
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")
        pytest.fail(f"OpenAI API call failed: {e}")

if __name__ == "__main__":
    test_openai_integration()
