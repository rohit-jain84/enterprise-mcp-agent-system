"""Project Management MCP Server - provides tools for sprint and ticket management."""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator

DATA_DIR = Path(__file__).resolve().parent / "data"

server = BaseMCPServer(name="project-management", data_dir=str(DATA_DIR))
mcp = server.mcp
error_sim = ErrorSimulator(error_rate=0.0)

# Import and register all tools
from tools.sprints import register_tools as register_sprint_tools
from tools.tickets import register_tools as register_ticket_tools
from tools.velocity import register_tools as register_velocity_tools
from tools.backlog import register_tools as register_backlog_tools
from tools.write_ops import register_tools as register_write_tools

register_sprint_tools(mcp, server, error_sim)
register_ticket_tools(mcp, server, error_sim)
register_velocity_tools(mcp, server, error_sim)
register_backlog_tools(mcp, server, error_sim)
register_write_tools(mcp, server, error_sim)

if __name__ == "__main__":
    server.run(transport="sse", host="0.0.0.0", port=8002)
