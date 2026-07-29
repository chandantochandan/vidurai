import subprocess
import hashlib
import uuid
import os

def get_git_identity(project_path: str):
    if not os.path.exists(os.path.join(project_path, ".git")):
        return {"ambiguous": True, "error": "Not a git repository"}
        
    try:
        # Get remotes
        remote_out = subprocess.check_output(
            ["git", "remote", "-v"], cwd=project_path, text=True, stderr=subprocess.STDOUT
        )
        remotes = []
        for line in remote_out.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    remotes.append(parts[1])
                    
        # Filter unique remotes and sort for determinism
        remotes = sorted(list(set(remotes)))
        
        fingerprint = None
        if remotes:
            # Use hash of remotes as fingerprint
            fingerprint = hashlib.sha256(",".join(remotes).encode()).hexdigest()
        else:
            # No remote? Use hash of the root commit (first commit)
            root_commit = subprocess.check_output(
                ["git", "rev-list", "--max-parents=0", "HEAD"], 
                cwd=project_path, text=True, stderr=subprocess.STDOUT
            ).strip().split('\n')[0]
            if root_commit:
                fingerprint = hashlib.sha256(root_commit.encode()).hexdigest()
            else:
                return {"ambiguous": True, "error": "No remote and no commits"}
                
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
        # Use UUIDv5 with a fixed namespace so the same fingerprint yields the same UUID
        NAMESPACE_VIDURAI = uuid.UUID('f0000000-0000-0000-0000-000000000000')
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
        
if __name__ == "__main__":
    print(get_git_identity("."))
