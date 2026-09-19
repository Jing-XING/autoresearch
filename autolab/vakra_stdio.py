"""Run the official VAKRA MCP implementation over private child-process stdio.

The upstream CLI installs Unix-only signal handlers. Instantiating its factory
without a shutdown event lets its existing EOF cleanup work on Windows too.
No tool implementations or MCP handlers are replaced.
"""
import argparse
import asyncio
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.runtime.resolve()))
    from environment.m3.python_tools.mcp.config import MCPServerConfig
    from environment.m3.python_tools.mcp.mcp_server import create_server
    config = MCPServerConfig(database_path=str(args.database.resolve()), domain=args.domain,
                             server_type="router", transport="stdio",
                             use_io_wrappers=False, use_pydantic_signatures=True)
    server = create_server(config, shutdown_event=None)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
