"""
Security Manager - Manages local pairing for Vidurai daemon.

Implements WP-05 explicit secure local pairing.
"""

import os
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("vidurai.ipc.security")

class SecurityManager:
    def __init__(self):
        self.vidurai_dir = Path.home() / ".vidurai"
        self.vidurai_dir.mkdir(exist_ok=True, mode=0o700)
        
        self.auth_file = self.vidurai_dir / "auth.json"
        
        self.current_challenge = None
        self.challenge_expiry = None
        self.valid_tokens = set()
        
        self._load_tokens()
        
    def _load_tokens(self):
        """Load persistent tokens from auth.json"""
        if self.auth_file.exists():
            try:
                # Enforce secure permissions
                if os.name != 'nt':
                    perms = oct(self.auth_file.stat().st_mode)[-3:]
                    if perms != '600':
                        logger.warning(f"Fixing permissions on {self.auth_file}")
                        self.auth_file.chmod(0o600)
                        
                with open(self.auth_file, 'r') as f:
                    data = json.load(f)
                    self.valid_tokens = set(data.get("tokens", []))
            except Exception as e:
                logger.error(f"Failed to load auth tokens: {e}")
                self.valid_tokens = set()
                
    def _save_tokens(self):
        """Save persistent tokens to auth.json securely"""
        try:
            with open(self.auth_file, 'w') as f:
                json.dump({"tokens": list(self.valid_tokens)}, f)
            if os.name != 'nt':
                self.auth_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to save auth tokens: {e}")

    def generate_pairing_challenge(self) -> str:
        """Generate a short-lived pairing code"""
        self.current_challenge = uuid.uuid4().hex[:6].upper()
        self.challenge_expiry = datetime.now() + timedelta(minutes=5)
        
        # Write to pairing.json so the CLI can display it
        pairing_file = self.vidurai_dir / "pairing.json"
        try:
            with open(pairing_file, 'w') as f:
                json.dump({
                    "code": self.current_challenge,
                    "expiry": self.challenge_expiry.timestamp()
                }, f)
            if os.name != 'nt':
                pairing_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to write pairing file: {e}")
            
        logger.info(f"Generated new pairing challenge (expires in 5m)")
        return self.current_challenge
        
    def verify_pairing(self, code: str) -> str:
        """Verify code and return a persistent token if valid"""
        if not self.current_challenge or not self.challenge_expiry:
            raise ValueError("No active pairing session")
            
        if datetime.now() > self.challenge_expiry:
            self.current_challenge = None
            raise ValueError("Pairing challenge expired")
            
        if code.strip().upper() != self.current_challenge:
            raise ValueError("Invalid pairing code")
            
        # Success! Generate token and clear challenge to prevent replay
        self.current_challenge = None
        self.challenge_expiry = None
        
        # Cleanup pairing.json
        pairing_file = self.vidurai_dir / "pairing.json"
        if pairing_file.exists():
            try:
                pairing_file.unlink()
            except:
                pass
                
        new_token = f"vk_{uuid.uuid4().hex}{uuid.uuid4().hex}"
        self.valid_tokens.add(new_token)
        self._save_tokens()
        
        return new_token
        
    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        if token in self.valid_tokens:
            self.valid_tokens.remove(token)
            self._save_tokens()
            return True
        return False
        
    def is_valid_token(self, token: str) -> bool:
        """Check if token is authorized"""
        return token in self.valid_tokens

# Global singleton
security_manager = SecurityManager()
