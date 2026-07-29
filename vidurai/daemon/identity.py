import os
import uuid
import hashlib
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger("vidurai.identity")

NAMESPACE_VIDURAI = uuid.UUID('f0000000-0000-0000-0000-000000000000')

def resolve_project_identity(project_path: str) -> Dict[str, Any]:
    """
    Resolve authoritative Git identity for a project path.
    
    Returns:
        Dict with keys:
            ambiguous (bool): True if identity could not be resolved
            project_uuid (str, optional): Authoritative stable UUID
            remote_fingerprint (str, optional): Hash of remotes or root commit
            branch (str, optional): Current branch
            commit (str, optional): Current commit
            detached (bool, optional): Whether HEAD is detached
            error (str, optional): Reason for ambiguity
    """
    if not project_path:
        return {"ambiguous": True, "error": "No project path provided"}
        
    try:
        if not os.path.isdir(project_path):
            return {"ambiguous": True, "error": f"Path is not a directory: {project_path}"}
            
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], 
            cwd=project_path, text=True, stderr=subprocess.STDOUT
        ).strip()
        
    except subprocess.CalledProcessError:
        return {"ambiguous": True, "error": "Not a git repository"}
        
    try:
        # Use root commits as the deterministic canonical repository anchor
        # This survives remote URL changes, local renames, and doesn't silently join unrelated repositories
        # because git commit hashes include timestamps, authors, and tree content.
        root_commits_out = subprocess.check_output(
            ["git", "rev-list", "--max-parents=0", "HEAD"], 
            cwd=project_path, text=True, stderr=subprocess.STDOUT
        ).strip()
        
        valid_commits = sorted([c for c in root_commits_out.split('\n') if c])
        if not valid_commits:
            return {"ambiguous": True, "error": "No commits found in repository"}
            
        fingerprint = hashlib.sha256(",".join(valid_commits).encode()).hexdigest()
                
        # Get branch and commit
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            cwd=project_path, text=True, stderr=subprocess.STDOUT
        ).strip()
        
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd=project_path, text=True, stderr=subprocess.STDOUT
        ).strip()
        
        detached = (branch == "HEAD")
        
        # Generate stable UUID from fingerprint
        project_uuid = str(uuid.uuid5(NAMESPACE_VIDURAI, fingerprint))
        
        return {
            "ambiguous": False,
            "project_uuid": project_uuid,
            "remote_fingerprint": fingerprint,
            "branch": branch,
            "commit": commit,
            "detached": detached
        }
    except subprocess.CalledProcessError as e:
        return {"ambiguous": True, "error": f"Git command failed: {e.output}"}
