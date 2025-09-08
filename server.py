#!/usr/bin/env python3
"""
AutoLearn server runner script.

Usage:
    python server.py [--host HOST] [--port PORT]
"""

import sys
import os

# Check if running in virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv', 'bin', 'python')
    if os.path.exists(venv_python):
        print(f"Re-launching with virtual environment Python: {venv_python}")
        os.execl(venv_python, venv_python, *sys.argv)
    else:
        print("WARNING: Not running in a virtual environment and couldn't find .venv/bin/python")
        print("Some dependencies might not be available. Consider activating the virtual environment first.")
        print("Run: source .venv/bin/activate")

import argparse
import logging
import os
from pathlib import Path

try:
    import uvicorn
except ImportError:
    print("ERROR: uvicorn not found. Make sure you're running in the virtual environment.")
    print("Run: source .venv/bin/activate && pip install -r requirements.txt")
    sys.exit(1)


def load_dotenv():
    """Load environment variables from .env file."""
    env_path = Path('.env')
    if env_path.exists():
        print("Loading environment variables from .env file")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                os.environ[key] = value
        return True
    return False


def setup_logging():
    """Set up basic logging configuration."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def check_environment():
    """Check if required environment variables are set."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable is not set.")
        print("OpenAI integration will not work until this is configured.")
        print("Please add your API key to the .env file or set it with:")
        print("export OPENAI_API_KEY=your-api-key")
        print()


def main():
    """Run the AutoLearn server."""
    parser = argparse.ArgumentParser(description="Run the AutoLearn server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind to")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    loaded = load_dotenv()
    if loaded:
        print("Environment variables loaded from .env file")
    
    setup_logging()
    check_environment()
    
    print(f"Starting AutoLearn server at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=True
    )


if __name__ == "__main__":
    main()
