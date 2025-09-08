#!/usr/bin/env python3
"""
AutoLearn MCP Server - Standalone entry point.

This script runs AutoLearn as a proper MCP server that can be connected to
by MCP clients like Claude Desktop, VS Code with MCP extension, etc.

Usage:
    python mcp_server.py                    # stdio transport (default)
    python mcp_server.py --transport http   # HTTP transport (future)
"""

import asyncio
import logging
import argparse
import sys
import os

# Add the project root to the path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_transport import MCPServer
from backend.skill_engine import SkillEngine
from backend.db import init_db


def setup_logging(level: str = "INFO"):
    """Setup logging for the MCP server."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr  # MCP clients use stdout for protocol, so log to stderr
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AutoLearn MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "http"], 
        default="stdio",
        help="Transport type (default: stdio)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    parser.add_argument(
        "--http-host",
        default="localhost",
        help="HTTP host (for HTTP transport, default: localhost)"
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=8001,
        help="HTTP port (for HTTP transport, default: 8001)"
    )
    return parser.parse_args()


async def main():
    """Main entry point for the MCP server."""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("AutoLearn MCP Server starting...")
    logger.info(f"Transport: {args.transport}")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create skill engine
        logger.info("Creating skill engine...")
        skill_engine = SkillEngine()
        
        # Log available skills
        skills = skill_engine.list_skills()
        logger.info(f"Loaded {len(skills)} skills: {[s.name for s in skills]}")
        
        # Create and run MCP server
        logger.info("Starting MCP server...")
        server = MCPServer(skill_engine=skill_engine, transport_type=args.transport)
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
