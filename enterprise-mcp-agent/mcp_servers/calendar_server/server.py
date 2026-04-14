"""Calendar MCP Server - provides read-only tools for calendar and meeting data."""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator

DATA_DIR = Path(__file__).resolve().parent / "data"

server = BaseMCPServer(name="calendar", data_dir=str(DATA_DIR))
mcp = server.mcp
error_sim = ErrorSimulator(error_rate=0.0)

# Import and register all tools
from tools.meetings import register_tools as register_meeting_tools
from tools.availability import register_tools as register_availability_tools
from tools.notes import register_tools as register_notes_tools

register_meeting_tools(mcp, server, error_sim)
register_availability_tools(mcp, server, error_sim)
register_notes_tools(mcp, server, error_sim)

if __name__ == "__main__":
    server.run(transport="sse", host="0.0.0.0", port=8003)
