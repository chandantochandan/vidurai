import json
import logging
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional
import os

logger = logging.getLogger("vidurai.mcp.permissions")

class Permission(str, Enum):
    READ_ONLY = "read-only"
    SENSITIVE_READ = "sensitive-read"
    MEMORY_MUTATION = "memory-mutation"
    EVIDENCE_MUTATION = "evidence-mutation"
    ADMIN = "admin"

class PermissionManager:
    """Manages MCP client permissions and auditing"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if not config_dir:
            self.config_dir = Path(os.path.expanduser("~/.vidurai"))
        else:
            self.config_dir = config_dir
            
        self.permissions_file = self.config_dir / "mcp_permissions.json"
        self.audit_file = self.config_dir / "mcp_audit.jsonl"
        self._grants: Dict[str, List[str]] = {}
        self._load()
        
    def _load(self):
        if self.permissions_file.exists():
            try:
                with open(self.permissions_file, "r") as f:
                    self._grants = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load permissions: {e}")
                self._grants = {}

    def _save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.permissions_file, "w") as f:
            json.dump(self._grants, f, indent=2)

    def grant(self, client_id: str, permission: Permission):
        """Grant a specific permission to a client."""
        if client_id not in self._grants:
            self._grants[client_id] = []
        if permission.value not in self._grants[client_id]:
            self._grants[client_id].append(permission.value)
        self._save()
        logger.info(f"Granted {permission.value} to {client_id}")

    def revoke(self, client_id: str, permission: Optional[Permission] = None):
        """Revoke a permission or all permissions from a client."""
        if client_id in self._grants:
            if permission:
                if permission.value in self._grants[client_id]:
                    self._grants[client_id].remove(permission.value)
            else:
                self._grants[client_id] = []
            self._save()
            logger.info(f"Revoked {'all' if not permission else permission.value} from {client_id}")

    def has_permission(self, client_id: str, permission: Permission) -> bool:
        """Check if client has a permission."""
        if client_id not in self._grants:
            return False
        # Admin implies all
        if Permission.ADMIN.value in self._grants[client_id]:
            return True
        return permission.value in self._grants[client_id]

    def audit(self, client_id: str, operation: str, project_scope: str, permission: str, outcome: str, reason: str = ""):
        """Record an audit trail."""
        import time
        record = {
            "timestamp": time.time(),
            "client_id": client_id,
            "operation": operation,
            "project_scope": project_scope,
            "permission": permission,
            "outcome": outcome,
            "reason": reason
        }
        try:
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
