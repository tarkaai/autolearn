#!/usr/bin/env python3
"""
Test runner for AutoLearn project.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py unit              # Run only unit tests
    python run_tests.py integration       # Run only integration tests
    python run_tests.py agent             # Run only agent tests
    python run_tests.py mcp               # Run only MCP tests
    python run_tests.py openai            # Run only OpenAI tests
    python run_tests.py --help            # Show help
"""

import sys
import subprocess
import os
from pathlib import Path


def run_tests(category=None, verbose=False):
    """Run tests for a specific category or all tests."""
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Add category-specific arguments
    if category == "unit":
        cmd.append("tests/unit/")
    elif category == "integration":
        cmd.append("tests/integration/")
    elif category == "agent":
        cmd.append("tests/agent/")
    elif category == "mcp":
        cmd.append("tests/mcp/")
    elif category == "openai":
        cmd.append("tests/openai_integration/")
    elif category is None:
        cmd.append("tests/")
    else:
        print(f"Unknown test category: {category}")
        print("Available categories: unit, integration, agent, mcp, openai")
        return 1
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            return 0
        category = sys.argv[1]
    else:
        category = None
    
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    
    return run_tests(category, verbose)


if __name__ == "__main__":
    sys.exit(main())
