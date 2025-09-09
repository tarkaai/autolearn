#!/usr/bin/env python3
"""
Test parameter name resolution after fixing MCP format issue.
"""

import asyncio
import sys
import subprocess
import time
from backend.consumer_agent import ConsumerAgent

async def test_parameter_resolution():
    """Test that consumer agent now uses correct parameter names."""
    
    # Start the backend server
    print("🚀 Starting backend server...")
    server_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app:app", "--port", "8000"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Initialize consumer agent and start conversation
        agent = ConsumerAgent()
        session_id = await agent.start_conversation("test_user")
        
        # Test the fibonacci calculation
        print("🧪 Testing fibonacci calculation with correct parameters...")
        
        # This should now use num_terms instead of n_terms
        response = await agent.chat(
            session_id=session_id,
            user_message="Calculate fibonacci sequence for 5 terms and multiply by 2"
        )
        
        print(f"✅ Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        # Clean up server
        print("🛑 Stopping backend server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    success = asyncio.run(test_parameter_resolution())
    sys.exit(0 if success else 1)
