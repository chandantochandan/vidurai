"""
Vidurai Python Bridge
Communicates with VS Code extension via stdin/stdout JSON protocol
"""
import sys
import os
import json
import signal
import logging
from typing import Dict, Any
from pathlib import Path

# Force unbuffered I/O - CRITICAL for subprocess communication
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdin.reconfigure(line_buffering=True)
sys.stdout.reconfigure(line_buffering=True)

from event_processor import EventProcessor
from vidurai_manager import ViduraiManager

# Configure logging to stderr (stdout is for JSON responses only!)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('vidurai-bridge')


class ViduraiBridge:
    """Main bridge process handling stdin/stdout communication"""

    def __init__(self):
        self.event_processor = EventProcessor()
        self.vidurai_manager = ViduraiManager()
        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Vidurai Bridge initialized")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

        # Save current session
        try:
            self.vidurai_manager.save_session()
            logger.info("Session saved successfully")
        except Exception as e:
            logger.error(f"Error saving session: {e}")

        sys.exit(0)

    def _send_response(self, response: Dict[str, Any]):
        """Send JSON response to stdout with immediate flush"""
        json_str = json.dumps(response)
        sys.stdout.write(json_str + '\n')
        sys.stdout.flush()  # Critical: ensure immediate delivery to parent process
        logger.debug(f"Sent response: {response.get('status', 'unknown')}")

    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """Validate event has required fields"""
        event_schemas = {
            'file_edit': ['type', 'file', 'content'],
            'terminal_output': ['type', 'command', 'output', 'exitCode'],
            'diagnostic': ['type', 'file', 'severity', 'message'],
            'recall_context': ['type', 'query'],
            'get_stats': ['type'],
            'ping': ['type'],
            # v2.0: New commands for database queries
            'get_recent_activity': ['type', 'project_path'],
            'recall_memories': ['type', 'project_path'],
            'get_statistics': ['type', 'project_path'],
            'get_context_for_ai': ['type', 'project_path'],
        }

        event_type = event.get('type')
        if event_type not in event_schemas:
            logger.error(f"Unknown event type: {event_type}")
            return False

        required_fields = event_schemas[event_type]
        for field in required_fields:
            if field not in event:
                logger.error(f"Missing required field '{field}' in {event_type}")
                return False

        return True

    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming event from VS Code"""
        event_type = event.get('type')

        try:
            if event_type == 'ping':
                return {'status': 'ok', 'message': 'pong'}

            elif event_type == 'file_edit':
                return self._handle_file_edit(event)

            elif event_type == 'terminal_output':
                return self._handle_terminal_output(event)

            elif event_type == 'diagnostic':
                return self._handle_diagnostic(event)

            elif event_type == 'recall_context':
                return self._handle_recall_context(event)

            elif event_type == 'get_stats':
                return self._handle_get_stats()

            # v2.0: New database query commands
            elif event_type == 'get_recent_activity':
                return self._handle_get_recent_activity(event)

            elif event_type == 'recall_memories':
                return self._handle_recall_memories(event)

            elif event_type == 'get_statistics':
                return self._handle_get_statistics(event)

            elif event_type == 'get_context_for_ai':
                return self._handle_get_context_for_ai(event)

            else:
                return {
                    'status': 'error',
                    'error': f'Unknown event type: {event_type}'
                }

        except Exception as e:
            logger.exception(f"Error processing {event_type}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _handle_file_edit(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file edit event"""
        file_path = event['file']
        content = event['content']

        # Process event (salience classification, secrets detection)
        processed = self.event_processor.process_file_edit(file_path, content)

        if processed.get('contains_secrets'):
            logger.warning(f"Secrets detected in {file_path}, content sanitized")

        # Store in Vidurai
        memory_id = self.vidurai_manager.remember(
            content=processed['gist'],
            metadata={
                'type': 'file_edit',
                'file': file_path,
                'salience': processed['salience'].name
            },
            salience=processed['salience']
        )

        return {
            'status': 'ok',
            'memory_id': memory_id,
            'salience': processed['salience'].name,
            'gist': processed['gist'],
            'secrets_detected': processed.get('contains_secrets', False)
        }

    def _handle_terminal_output(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle terminal output event"""
        command = event['command']
        output = event['output']
        exit_code = event['exitCode']

        # Process event
        processed = self.event_processor.process_terminal_output(
            command, output, exit_code
        )

        # Store in Vidurai
        memory_id = self.vidurai_manager.remember(
            content=processed['gist'],
            metadata={
                'type': 'terminal',
                'command': command,
                'exit_code': exit_code,
                'salience': processed['salience'].name
            },
            salience=processed['salience']
        )

        return {
            'status': 'ok',
            'memory_id': memory_id,
            'salience': processed['salience'].name,
            'gist': processed['gist']
        }

    def _handle_diagnostic(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle diagnostic (error/warning) event"""
        file_path = event['file']
        severity = event['severity']
        message = event['message']

        # Process event
        processed = self.event_processor.process_diagnostic(
            file_path, severity, message
        )

        # Store in Vidurai
        memory_id = self.vidurai_manager.remember(
            content=processed['gist'],
            metadata={
                'type': 'diagnostic',
                'file': file_path,
                'severity': severity,
                'salience': processed['salience'].name
            },
            salience=processed['salience']
        )

        return {
            'status': 'ok',
            'memory_id': memory_id,
            'salience': processed['salience'].name,
            'gist': processed['gist']
        }

    def _handle_recall_context(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Recall relevant memories"""
        query = event['query']
        top_k = event.get('top_k', 10)

        memories = self.vidurai_manager.recall(query, top_k)

        return {
            'status': 'ok',
            'memories': [
                {
                    'gist': mem.gist or mem.verbatim,
                    'verbatim': mem.verbatim,
                    'salience': mem.salience.name,
                    'age_days': mem.age_days(),
                    'metadata': mem.metadata
                }
                for mem in memories
            ],
            'count': len(memories)
        }

    def _handle_get_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        stats = self.vidurai_manager.get_stats()

        return {
            'status': 'ok',
            'stats': stats
        }

    # v2.0: New database query handlers
    def _handle_get_recent_activity(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent memories for a project (v2.0)"""
        try:
            project_path = event['project_path']
            hours = event.get('hours', 24)
            limit = event.get('limit', 20)

            memories = self.vidurai_manager.get_recent_activity(
                project_path=project_path,
                hours=hours,
                limit=limit
            )

            return {
                'status': 'ok',
                'memories': memories,
                'count': len(memories)
            }

        except Exception as e:
            logger.exception(f"Error getting recent activity: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _handle_recall_memories(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Recall memories from database (v2.0)"""
        try:
            project_path = event['project_path']
            query = event.get('query')
            min_salience = event.get('min_salience', 'MEDIUM')
            limit = event.get('limit', 10)

            memories = self.vidurai_manager.recall_from_database(
                project_path=project_path,
                query=query,
                min_salience=min_salience,
                limit=limit
            )

            return {
                'status': 'ok',
                'memories': memories,
                'count': len(memories)
            }

        except Exception as e:
            logger.exception(f"Error recalling memories: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _handle_get_statistics(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get database statistics for a project (v2.0)"""
        try:
            project_path = event['project_path']

            stats = self.vidurai_manager.get_database_statistics(
                project_path=project_path
            )

            return {
                'status': 'ok',
                'statistics': stats
            }

        except Exception as e:
            logger.exception(f"Error getting statistics: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _handle_get_context_for_ai(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted context for AI injection (v2.0 - Claude Code integration)"""
        try:
            project_path = event['project_path']
            query = event.get('query')
            max_tokens = event.get('max_tokens', 2000)

            context = self.vidurai_manager.get_context_for_ai(
                project_path=project_path,
                query=query,
                max_tokens=max_tokens
            )

            return {
                'status': 'ok',
                'context': context
            }

        except Exception as e:
            logger.exception(f"Error getting AI context: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'context': f'[Error: {str(e)}]'
            }

    def run(self):
        """Main loop: read from stdin, process, write to stdout"""
        logger.info("Bridge started, waiting for events...")

        try:
            while self.running:
                # Read line from stdin
                line = sys.stdin.readline()

                if not line:
                    # EOF reached, exit gracefully
                    logger.info("EOF received, shutting down")
                    break

                try:
                    # Parse JSON
                    event = json.loads(line.strip())

                    # Validate event
                    if not self._validate_event(event):
                        response = {
                            'status': 'error',
                            'error': 'Invalid event format'
                        }
                    else:
                        # Process event
                        response = self.process_event(event)

                    # Preserve request ID in response for callback matching
                    if '_id' in event:
                        response['_id'] = event['_id']

                    # Send response
                    self._send_response(response)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        'status': 'error',
                        'error': f'Invalid JSON: {str(e)}'
                    }
                    # Try to preserve _id if event was parsed
                    try:
                        partial_event = json.loads(line.strip())
                        if '_id' in partial_event:
                            error_response['_id'] = partial_event['_id']
                    except:
                        pass
                    self._send_response(error_response)

                except Exception as e:
                    logger.exception("Unexpected error in main loop")
                    error_response = {
                        'status': 'error',
                        'error': str(e)
                    }
                    # Try to preserve _id from event if available
                    try:
                        if 'event' in locals() and '_id' in event:
                            error_response['_id'] = event['_id']
                    except:
                        pass
                    self._send_response(error_response)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        finally:
            # Cleanup
            self.vidurai_manager.save_session()
            logger.info("Bridge stopped")


def main():
    """Entry point"""
    bridge = ViduraiBridge()
    bridge.run()


if __name__ == '__main__':
    main()
