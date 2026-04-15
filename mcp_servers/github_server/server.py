"""GitHub MCP Server - provides tools for GitHub repository operations."""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.base_server import BaseMCPServer
from shared.error_simulator import ErrorSimulator

DATA_DIR = Path(__file__).resolve().parent / "data"

server = BaseMCPServer(name="github", data_dir=str(DATA_DIR))
mcp = server.mcp
error_sim = ErrorSimulator(error_rate=0.0)

# Import and register all tools
from tools.pull_requests import register_tools as register_pr_tools
from tools.issues import register_tools as register_issue_tools
from tools.commits import register_tools as register_commit_tools
from tools.ci import register_tools as register_ci_tools
from tools.write_ops import register_tools as register_write_tools

register_pr_tools(mcp, server, error_sim)
register_issue_tools(mcp, server, error_sim)
register_commit_tools(mcp, server, error_sim)
register_ci_tools(mcp, server, error_sim)
register_write_tools(mcp, server, error_sim)

if __name__ == "__main__":
    server.run(transport="sse", host="0.0.0.0", port=8001)
