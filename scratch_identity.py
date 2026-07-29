import re
import urllib.parse

def canonicalise_url(url: str) -> str:
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    
    if url.startswith("git@"):
        # git@github.com:org/repo
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

urls = [
    "git@github.com:chandan/vidurai.git",
    "https://github.com/chandan/vidurai.git",
    "ssh://git@github.com/chandan/vidurai.git",
    "https://user:pass@github.com/chandan/vidurai",
]
for u in urls:
    print(f"{u} -> {canonicalise_url(u)}")
