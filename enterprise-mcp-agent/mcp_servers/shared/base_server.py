"""Base MCP server class with shared functionality."""

import json
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


class BaseMCPServer:
    """Base class for all MCP servers in the enterprise system."""

    def __init__(self, name: str, data_dir: str) -> None:
        self.name = name
        self.data_dir = Path(data_dir)
        self.mcp = FastMCP(name)
        self._cache: dict[str, Any] = {}

    def load_data(self, filename: str) -> Any:
        """Load JSON data from the data directory, caching in memory."""
        if filename in self._cache:
            return self._cache[filename]

        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._cache[filename] = data
        return data

    def run(self, **kwargs: Any) -> None:
        """Start the MCP server."""
        self.mcp.run(**kwargs)
