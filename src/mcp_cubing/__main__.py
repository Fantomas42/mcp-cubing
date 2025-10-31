"""Entry point for running the MCP cubing server."""
import asyncio

from mcp_cubing.server import main

if __name__ == '__main__':
    asyncio.run(main())
