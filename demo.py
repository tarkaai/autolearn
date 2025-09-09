#!/usr/bin/env python3
"""
AutoLearn Milestone 4 Demo Script

This script demonstrates the complete User Mode functionality:
1. Starts the AutoLearn backend server (MCP server + Consumer Agent)
2. Starts the frontend development server
3. Opens the browser to show the user mode interface
4. Provides instructions for testing the auto-learning functionality

Usage: python demo_milestone4.py
"""

import os
import sys
import time
import signal
import subprocess
import webbrowser
import asyncio
import json
from pathlib import Path
from backend.consumer_agent import ConsumerAgent

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(message, color=Colors.OKGREEN):
    print(f"{color}{message}{Colors.ENDC}")

def print_header(message):
    print_colored(f"\n{'='*60}", Colors.HEADER)
    print_colored(f"  {message}", Colors.HEADER)
    print_colored(f"{'='*60}", Colors.HEADER)

def check_requirements():
    """Check if all requirements are met."""
    print_header("CHECKING REQUIREMENTS")
    
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("frontend").exists():
        print_colored("❌ Error: Please run this script from the autolearn project root directory", Colors.FAIL)
        sys.exit(1)
    
    # Check if virtual environment exists
    venv_path = Path(".venv")
    if not venv_path.exists():
        print_colored("❌ Error: Virtual environment not found. Please create one with: python -m venv .venv", Colors.FAIL)
        sys.exit(1)
    
    # Check if frontend dependencies are installed
    if not Path("frontend/node_modules").exists():
        print_colored("❌ Error: Frontend dependencies not installed. Please run: cd frontend && npm install", Colors.FAIL)
        sys.exit(1)
    
    print_colored("✅ All requirements met!", Colors.OKGREEN)

def start_backend():
    """Start the AutoLearn backend server."""
    print_header("STARTING AUTOLEARN BACKEND SERVER")
    
    # Get the virtual environment python path
    if os.name == 'nt':  # Windows
        python_path = Path(".venv/Scripts/python.exe")
    else:  # Unix/Linux/macOS
        python_path = Path(".venv/bin/python")
    
    print_colored("🚀 Starting backend server on http://localhost:8000", Colors.OKBLUE)
    
    # Start the backend server
    backend_process = subprocess.Popen([
        str(python_path), "-m", "uvicorn", "backend.app:app", 
        "--reload", "--port", "8000"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait for server to start
    print_colored("⏳ Waiting for backend to start...", Colors.WARNING)
    time.sleep(3)
    
    return backend_process

def start_frontend():
    """Start the frontend development server."""
    print_header("STARTING FRONTEND DEVELOPMENT SERVER")
    
    print_colored("🚀 Starting frontend server on http://localhost:3000", Colors.OKBLUE)
    
    # Change to frontend directory and start
    frontend_process = subprocess.Popen([
        "npm", "run", "dev"
    ], cwd="frontend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait for frontend to start
    print_colored("⏳ Waiting for frontend to start...", Colors.WARNING)
    time.sleep(5)
    
    return frontend_process

def open_browser():
    """Open the browser to the demo page."""
    print_header("OPENING BROWSER")
    
    urls_to_try = [
        "http://localhost:3000/",
    ]
    
    for url in urls_to_try:
        try:
            print_colored(f"🌐 Opening {url}", Colors.OKCYAN)
            webbrowser.open(url)
            break
        except Exception as e:
            print_colored(f"❌ Failed to open {url}: {e}", Colors.FAIL)

def print_demo_instructions():
    """Print instructions for using the demo."""
    print_header("MILESTONE 4 DEMO INSTRUCTIONS")
    
    instructions = """
🎯 AUTOLEARN DEMO

The demo is now running! Here's how to test the auto-learning functionality:

1. NAVIGATE TO THE APP:
   • Go to http://localhost:3000

2. CHAT WITH THE AI ASSISTANT:
   • Type messages in the chat interface
   • The AI will respond and suggest existing skills
   • Try asking for something complex that doesn't exist yet

3. TEST SKILL GENERATION:
   • Ask: "Help me calculate the fibonacci sequence for number 10"
   • Ask: "Create a function to convert temperature from celsius to fahrenheit"
   • Ask: "Generate a password with specific requirements"

4. OBSERVE AUTO-LEARNING:
   • Watch as the AI identifies when new skills are needed
   • See skills being generated automatically
   • Notice how generated skills appear in the sidebar
   • Try using the same request again - it should use the cached skill

5. EXPLORE FEATURES:
   • Check the "Generated Skills" panel on the right
   • View the "Used Skills" tracking
   • Notice skill suggestions appear as you type

🔧 TECHNICAL DETAILS:
   • Backend: AutoLearn MCP server with Consumer Agent
   • Frontend: User-centric chat interface with skill tracking
   • AI Agent: Uses OpenAI to understand requests and generate skills
   • MCP Protocol: Skills are registered as MCP tools dynamically
   
🚀 MILESTONE 4 SUCCESS CRITERIA:
   ✅ User can manually request new skills
   ✅ AutoLearn generates and crystallizes code
   ✅ Frontend displays skills and code
   ✅ Generated skills execute successfully
   ✅ Consumer Agent connects via MCP protocol
"""
    
    print_colored(instructions, Colors.OKGREEN)

def cleanup_processes(backend_process, frontend_process):
    """Clean up processes on exit."""
    print_colored("\n🛑 Shutting down servers...", Colors.WARNING)
    
    try:
        if backend_process:
            backend_process.terminate()
            backend_process.wait(timeout=5)
    except:
        pass
    
    try:
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
    except:
        pass
    
    print_colored("✅ Demo stopped successfully!", Colors.OKGREEN)

async def demo_consumer_agent():
    """Quick test of the consumer agent functionality."""
    print_header("TESTING CONSUMER AGENT")
    
    try:
        # Create consumer agent
        print_colored("1️⃣ Creating Consumer Agent...", Colors.OKBLUE)
        agent = ConsumerAgent()
        print_colored("✅ Consumer Agent created successfully", Colors.OKGREEN)
        
        # Start conversation session
        print_colored("2️⃣ Starting conversation session...", Colors.OKBLUE)
        session_id = await agent.start_conversation("demo_user")
        print_colored(f"✅ Session started: {session_id}", Colors.OKGREEN)
        
        print_colored("✅ Consumer Agent is ready for MCP integration!", Colors.OKGREEN)
        
    except Exception as e:
        print_colored(f"⚠️ Consumer Agent test: {e}", Colors.WARNING)

def main():
    """Main demo function."""
    print_colored("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║               🚀 AUTOLEARN DEMO                           ║
    ║                                                           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """, Colors.HEADER)
    
    backend_process = None
    frontend_process = None
    
    try:
        # Quick consumer agent test
        asyncio.run(demo_consumer_agent())
        
        # Check requirements
        check_requirements()
        
        # Start servers
        backend_process = start_backend()
        frontend_process = start_frontend()
        
        # Open browser
        open_browser()
        
        # Print instructions
        print_demo_instructions()
        
        print_header("DEMO RUNNING")
        print_colored("✅ Demo is now running!", Colors.OKGREEN)
        print_colored("🌐 Frontend: http://localhost:3000", Colors.OKCYAN)
        print_colored("🔧 Backend: http://localhost:8000", Colors.OKCYAN)
        print_colored("\n💡 Press Ctrl+C to stop the demo", Colors.WARNING)
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print_colored("\n🛑 Demo interrupted by user", Colors.WARNING)
    except Exception as e:
        print_colored(f"\n❌ Demo error: {e}", Colors.FAIL)
    finally:
        cleanup_processes(backend_process, frontend_process)


if __name__ == "__main__":
    main()
