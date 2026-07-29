import os
import uuid
import hashlib
import logging
import subprocess
import urllib.parse
from typing import Dict, Any, Optional

logger = logging.getLogger("vidurai.identity")

NAMESPACE_VIDURAI = uuid.UUID('f0000000-0000-0000-0000-000000000000')

def canonicalise_url(url: str) -> str:
    """Canonicalises git URLs (HTTPS/SSH) to a uniform deterministic string."""
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    
    if url.startswith("git@"):
        url = url[4:]
        url = url.replace(":", "/", 1)
    elif url.startswith("ssh://"):
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]
        url = f"{netloc}{parsed.path}"
    elif url.startswith("http://") or url.startswith("https://"):
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]
        url = f"{netloc}{parsed.path}"
        
    url = url.strip("/")
    return url.lower()

def resolve_project_identity(project_path: str) -> Dict[str, Any]:
    """
    Resolve authoritative Git identity for a project path.
    
    Returns:
        Dict with keys:
            ambiguous (bool): True if identity could not be resolved
            project_uuid (str, optional): Authoritative stable UUID
            remote_fingerprint (str, optional): The canonical anchor
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
            
        subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], 
            cwd=project_path, text=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError:
        return {"ambiguous": True, "error": "Not a git repository"}
        
    try:
        # 1. Check if identity is already persisted
        try:
            stored_uuid = subprocess.check_output(
                ["git", "config", "--local", "vidurai.projectuuid"],
                cwd=project_path, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if stored_uuid:
                # Still get branch and commit
                branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path, text=True).strip()
                commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project_path, text=True).strip()
                return {
                    "ambiguous": False,
                    "project_uuid": stored_uuid,
                    "remote_fingerprint": "persisted_local",
                    "branch": branch,
                    "commit": commit,
                    "detached": (branch == "HEAD")
                }
        except subprocess.CalledProcessError:
            pass # Not configured yet

        # 2. Determine canonical remote
        remote_out = subprocess.check_output(
            ["git", "remote", "-v"], cwd=project_path, text=True, stderr=subprocess.STDOUT
        )
        
        # Parse remotes: dict of name -> canonical_url
        remotes = {}
        for line in remote_out.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    name, url = parts[0], parts[1]
                    remotes[name] = canonicalise_url(url)
                    
        selected_url = None
        
        if remotes:
            # a. currently tracked upstream remote
            try:
                upstream = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "@{u}"],
                    cwd=project_path, text=True, stderr=subprocess.DEVNULL
                ).strip()
                upstream_remote = upstream.split('/')[0] if '/' in upstream else None
                if upstream_remote in remotes:
                    selected_url = remotes[upstream_remote]
            except subprocess.CalledProcessError:
                pass
                
            # b. origin
            if not selected_url and "origin" in remotes:
                selected_url = remotes["origin"]
                
            # c. only available canonical fetch remote
            if not selected_url:
                unique_urls = list(set(remotes.values()))
                if len(unique_urls) == 1:
                    selected_url = unique_urls[0]
                else:
                    return {"ambiguous": True, "error": "Multiple remotes and no upstream/origin"}
                    
            project_uuid = str(uuid.uuid5(NAMESPACE_VIDURAI, selected_url))
            fingerprint = selected_url
        else:
            # 3. No-remote fallback: generate random UUID for local repo
            project_uuid = str(uuid.uuid4())
            fingerprint = "local_only"

        # 4. Persist identity to avoid future changes
        subprocess.check_call(
            ["git", "config", "--local", "vidurai.projectuuid", project_uuid],
            cwd=project_path
        )
        
        # Get branch and commit
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path, text=True).strip()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project_path, text=True).strip()
        
        return {
            "ambiguous": False,
            "project_uuid": project_uuid,
            "remote_fingerprint": fingerprint,
            "branch": branch,
            "commit": commit,
            "detached": (branch == "HEAD")
        }
    except subprocess.CalledProcessError as e:
        return {"ambiguous": True, "error": f"Git command failed: {e.output}"}
