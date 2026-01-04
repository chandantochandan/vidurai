#!/usr/bin/env python3
"""
Bridge between Ghost Daemon (port 7777) and MCP Server (port 8765)
Allows MCP server to query daemon for active projects
"""

import requests
import logging

logger = logging.getLogger("vidurai.mcp_bridge")

class MCPBridge:
    """Bridge to communicate with existing MCP server"""

    def __init__(self, mcp_url: str = "http://localhost:8765"):
        self.mcp_url = mcp_url
        self.daemon_url = "http://localhost:7777"

    def notify_mcp_of_change(self, event: dict):
        """Notify MCP server when files change"""
        try:
            response = requests.post(
                f"{self.mcp_url}/notify",
                json=event,
                timeout=1
            )
            return response.ok
        except requests.exceptions.RequestException as e:
            logger.debug(f"MCP server not available: {e}")
            return False

    def get_daemon_status(self) -> dict:
        """Check daemon status from MCP server perspective"""
        try:
            response = requests.get(
                f"{self.daemon_url}/health",
                timeout=1
            )
            return response.json() if response.ok else {}
        except:
            return {"status": "offline"}
