#!/usr/bin/env python3
"""
Vidurai MCP Server
Provides memory context to AI tools via HTTP-based Model Context Protocol
v2.0 - Phase 2

Architecture:
- HTTP server on port 8765 (default)
- Restricted CORS for security
- Tools: get_project_context, search_memories, get_recent_activity, get_active_project
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List
import argparse
import os

from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.vismriti_memory import VismritiMemory
from vidurai.version import __version__

# Phase 6: Event Bus integration
try:
    from vidurai.core.event_bus import publish_event
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

# Phase 6.6: Proactive Hints integration
try:
    from vidurai.core.episode_builder import EpisodeBuilder
    from vidurai.core.hint_delivery import create_hint_service
    HINTS_AVAILABLE = True
except ImportError:
    HINTS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vidurai.mcp")


class MCPRequestHandler(BaseHTTPRequestHandler):
    """Handle MCP protocol requests"""

    database: MemoryDatabase = None
    allow_all_origins: bool = False

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if self.allow_all_origins:
            return True

        # Allowed origins for security
        allowed_patterns = [
            'http://localhost',
            'http://127.0.0.1',
            'https://chat.openai.com',
            'https://chatgpt.com',
        ]

        if not origin:
            return True  # Allow requests without Origin header

        for pattern in allowed_patterns:
            if origin.startswith(pattern):
                return True

        return False

    def _send_cors_headers(self, origin: str = None):
        """Send CORS headers"""
        if origin and self._is_origin_allowed(origin):
            self.send_header('Access-Control-Allow-Origin', origin)
        elif self.allow_all_origins:
            self.send_header('Access-Control-Allow-Origin', '*')

        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        origin = self.headers.get('Origin')

        if self._is_origin_allowed(origin):
            self.send_response(200)
            self._send_cors_headers(origin)
            self.end_headers()
        else:
            logger.warning(f"Blocked CORS request from: {origin}")
            self.send_response(403)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests (MCP tool invocations)"""
        origin = self.headers.get('Origin')

        if not self._is_origin_allowed(origin):
            logger.warning(f"Blocked POST request from: {origin}")
            self.send_response(403)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body.decode('utf-8'))
            response = self.handle_mcp_request(request)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers(origin)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self.send_error(500, str(e))

    def do_GET(self):
        """Handle GET requests (health check, capabilities)"""
        origin = self.headers.get('Origin')

        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers(origin)
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'version': __version__,
                'server': 'vidurai-mcp'
            }).encode('utf-8'))

        elif self.path == '/capabilities':
            capabilities = {
                'name': 'vidurai',
                'version': __version__,
                'description': 'Persistent AI memory layer with project-level context recall',
                'tools': [
                    {
                        'name': 'get_project_context',
                        'description': 'Get relevant project context from memory for AI prompts',
                        'parameters': {
                            'query': {
                                'type': 'string',
                                'required': False,
                                'description': 'Query to filter relevant memories'
                            },
                            'project': {
                                'type': 'string',
                                'required': True,
                                'description': 'Project path'
                            },
                            'min_salience': {
                                'type': 'string',
                                'default': 'MEDIUM',
                                'description': 'Minimum salience level (CRITICAL, HIGH, MEDIUM, LOW)'
                            }
                        }
                    },
                    {
                        'name': 'search_memories',
                        'description': 'Search through project memories',
                        'parameters': {
                            'query': {
                                'type': 'string',
                                'required': True,
                                'description': 'Search query'
                            },
                            'project': {
                                'type': 'string',
                                'required': True,
                                'description': 'Project path'
                            },
                            'limit': {
                                'type': 'integer',
                                'default': 10,
                                'description': 'Maximum number of results'
                            }
                        }
                    },
                    {
                        'name': 'get_recent_activity',
                        'description': 'Get recent development activity',
                        'parameters': {
                            'project': {
                                'type': 'string',
                                'required': True,
                                'description': 'Project path'
                            },
                            'hours': {
                                'type': 'integer',
                                'default': 24,
                                'description': 'Hours to look back'
                            }
                        }
                    },
                    {
                        'name': 'get_active_project',
                        'description': 'Get currently active VS Code project path',
                        'parameters': {}
                    },
                    {
                        'name': 'get_proactive_hints',
                        'description': 'Get context-aware hints based on development history (Phase 6.6)',
                        'parameters': {
                            'project': {
                                'type': 'string',
                                'required': True,
                                'description': 'Project path'
                            },
                            'max_hints': {
                                'type': 'integer',
                                'default': 5,
                                'description': 'Maximum number of hints to return'
                            },
                            'min_confidence': {
                                'type': 'number',
                                'default': 0.5,
                                'description': 'Minimum confidence threshold (0.0-1.0)'
                            },
                            'hint_types': {
                                'type': 'array',
                                'required': False,
                                'description': 'Specific hint types to include (similar_episode, pattern_warning, success_pattern, file_context)'
                            }
                        }
                    }
                ]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers(origin)
            self.end_headers()
            self.wfile.write(json.dumps(capabilities, indent=2).encode('utf-8'))

        else:
            self.send_error(404, f"Not found: {self.path}")

    def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP tool invocation"""
        tool = request.get('tool')
        params = request.get('params', {})

        logger.info(f"Handling tool: {tool}")

        try:
            if tool == 'get_project_context':
                return self.get_project_context(params)
            elif tool == 'search_memories':
                return self.search_memories(params)
            elif tool == 'get_recent_activity':
                return self.get_recent_activity(params)
            elif tool == 'get_active_project':
                return self.get_active_project(params)
            elif tool == 'get_proactive_hints':
                return self.get_proactive_hints(params)
            else:
                return {
                    'error': f'Unknown tool: {tool}',
                    'available_tools': ['get_project_context', 'search_memories', 'get_recent_activity', 'get_active_project', 'get_proactive_hints']
                }
        except Exception as e:
            logger.exception(f"Error in tool {tool}")
            return {'error': str(e)}

    def get_project_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted project context for AI"""
        project = params.get('project', '.')
        query = params.get('query')
        max_tokens = params.get('max_tokens', 2000)

        try:
            memory = VismritiMemory(project_path=project)
            context = memory.get_context_for_ai(query=query, max_tokens=max_tokens)

            # Phase 6: Publish MCP context event
            if EVENT_BUS_AVAILABLE:
                try:
                    publish_event(
                        "mcp.get_context",
                        source="mcp_server",
                        project_path=project,
                        query=query or "all",
                        max_tokens=max_tokens,
                        context_length=len(context)
                    )
                except Exception:
                    pass  # Silent fail for event publishing

            return {
                'result': context,
                'metadata': {
                    'project': project,
                    'query': query,
                    'max_tokens': max_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error getting project context: {e}")
            return {
                'error': str(e),
                'result': '[No project context available]'
            }

    def search_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search memories"""
        project = params.get('project', '.')
        query = params['query']
        limit = params.get('limit', 10)

        try:
            db = MCPRequestHandler.database
            memories = db.recall_memories(
                project_path=project,
                query=query,
                limit=limit
            )

            # Phase 6: Publish MCP search event
            if EVENT_BUS_AVAILABLE:
                try:
                    publish_event(
                        "mcp.search_memories",
                        source="mcp_server",
                        project_path=project,
                        query=query,
                        memory_count=len(memories),
                        limit=limit
                    )
                except Exception:
                    pass  # Silent fail for event publishing

            return {
                'result': memories,
                'count': len(memories)
            }
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return {'error': str(e), 'result': []}

    def get_recent_activity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent activity"""
        project = params.get('project', '.')
        hours = params.get('hours', 24)

        try:
            db = MCPRequestHandler.database
            memories = db.get_recent_activity(
                project_path=project,
                hours=hours
            )

            return {
                'result': memories,
                'count': len(memories)
            }
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return {'error': str(e), 'result': []}

    def get_active_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get currently active VS Code project path"""
        try:
            # Read from file written by VS Code extension
            active_file = Path.home() / '.vidurai' / 'active-project.txt'

            if active_file.exists():
                project_path = active_file.read_text().strip()

                # Verify path exists
                if Path(project_path).exists():
                    logger.info(f"Active project: {project_path}")
                    return {
                        'result': project_path,
                        'source': 'vscode'
                    }

            # Fallback to current directory
            logger.info("No active project file, using current directory")
            return {
                'result': os.getcwd(),
                'source': 'default'
            }

        except Exception as e:
            logger.error(f"Error reading active project: {e}")
            return {
                'result': '.',
                'source': 'error',
                'error': str(e)
            }

    def get_proactive_hints(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get proactive hints based on development history (Phase 6.6)"""
        if not HINTS_AVAILABLE:
            return {
                'error': 'Proactive hints not available. Install required dependencies.',
                'result': {'hints': [], 'count': 0}
            }

        project = params.get('project', '.')
        max_hints = params.get('max_hints', 5)
        min_confidence = params.get('min_confidence', 0.5)
        hint_types = params.get('hint_types')

        try:
            builder = EpisodeBuilder()
            hint_service = create_hint_service(builder)

            # Get hints
            hints = hint_service.get_hints_for_project(
                project_path=project,
                hint_types=hint_types,
                min_confidence=min_confidence,
                max_hints=max_hints
            )

            # Format for JSON response
            result = hint_service.format_for_mcp(hints)

            # Add statistics
            stats = hint_service.get_statistics()
            result['statistics'] = {
                'total_episodes': stats['engine_stats']['total_episodes'],
                'recurring_patterns': stats['engine_stats']['recurring_patterns'],
                'comodification_patterns': stats['engine_stats']['comodification_patterns']
            }

            logger.info(f"Generated {len(hints)} hints for {project}")
            return {'result': result}

        except Exception as e:
            logger.error(f"Error generating hints: {e}")
            return {
                'error': str(e),
                'result': {'hints': [], 'count': 0}
            }

    def log_message(self, format, *args):
        """Override to use logger"""
        logger.info(f"{self.client_address[0]} - {format % args}")


def start_mcp_server(host: str = 'localhost', port: int = 8765, allow_all_origins: bool = False):
    """Start MCP server"""

    # Initialize database
    try:
        MCPRequestHandler.database = MemoryDatabase()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Set security mode
    MCPRequestHandler.allow_all_origins = allow_all_origins

    if allow_all_origins:
        logger.warning("⚠️  CORS restrictions DISABLED - Development mode only!")
    else:
        logger.info("✓ CORS restrictions enabled (localhost + ChatGPT only)")

    server = HTTPServer((host, port), MCPRequestHandler)

    logger.info("=" * 60)
    logger.info("🧠 Vidurai MCP Server")
    logger.info("=" * 60)
    logger.info(f"Listening on: http://{host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info(f"Capabilities: http://{host}:{port}/capabilities")
    logger.info("=" * 60)
    logger.info("Tools available:")
    logger.info("  • get_project_context - Get AI-ready context")
    logger.info("  • search_memories - Search project memories")
    logger.info("  • get_recent_activity - Get recent dev activity")
    logger.info("  • get_active_project - Get current VS Code project")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down MCP server...")
        server.shutdown()


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description='Vidurai MCP Server - Persistent AI Memory Layer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server (default: localhost:8765)
  python -m vidurai.mcp_server

  # Start on custom port
  python -m vidurai.mcp_server --port 9000

  # Development mode (disable CORS)
  python -m vidurai.mcp_server --allow-all-origins

विस्मृति भी विद्या है — "Forgetting too is knowledge"
जय विदुराई! 🕉️
        """
    )

    parser.add_argument(
        '--host',
        default='localhost',
        help='Host to bind to (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8765,
        help='Port to listen on (default: 8765)'
    )
    parser.add_argument(
        '--allow-all-origins',
        action='store_true',
        help='⚠️  Disable CORS restrictions (development only)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    try:
        start_mcp_server(
            host=args.host,
            port=args.port,
            allow_all_origins=args.allow_all_origins
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
