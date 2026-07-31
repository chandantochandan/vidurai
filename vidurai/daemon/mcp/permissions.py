import json
import logging
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional
import os
import secrets

logger = logging.getLogger("vidurai.mcp.permissions")

class Permission(str, Enum):
    READ_ONLY = "read-only"
    SENSITIVE_READ = "sensitive-read"
    MEMORY_MUTATION = "memory-mutation"
    EVIDENCE_MUTATION = "evidence-mutation"
    ADMIN = "admin"

class ClientAuthenticator:
    """Manages MCP client credentials securely"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(os.path.expanduser("~/.vidurai"))
        self.credentials_file = self.config_dir / "mcp_credentials.json"
        self._creds: Dict[str, str] = {}
        self._load()
        
    def _load(self):
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, "r") as f:
                    self._creds = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load credentials: {e}")
                self._creds = {}

    def _save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.credentials_file, "w") as f:
            json.dump(self._creds, f, indent=2)
        try:
            os.chmod(self.credentials_file, 0o600)
        except OSError:
            pass

    def generate_credential(self, client_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._creds[client_id] = token
        self._save()
        return token
        
    def verify(self, client_id: str, token: str) -> bool:
        if not client_id or not token:
            return False
        stored = self._creds.get(client_id, "")
        if not stored:
            return False
        return secrets.compare_digest(stored, token)
        
    def revoke(self, client_id: str) -> bool:
        if client_id in self._creds:
            del self._creds[client_id]
            self._save()
            return True
        return False

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
