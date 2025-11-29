# Vidurai v2.0.0 – Release Checklist

This document tracks the exact steps and artifacts required to publish Vidurai v2.0.0 across all channels.

---

## 1. Artifacts

- **Python SDK (PyPI):**
 - `dist/vidurai-2.0.0-py3-none-any.whl`
 - `dist/vidurai-2.0.0.tar.gz`

- **VS Code Extension:**
 - `dist/vscode/vidurai-2.0.0.vsix`

- **Browser Extension:**
 - `dist/browser/vidurai-browser-2.0.0.zip`

- **Docker Images (local tags):**
 - `vidurai-daemon:2.0.0`
 - `vidurai-proxy:2.0.0`

---

## 2. Pre-Release Checks

- [x] All tests passing locally (`pytest`)
- [x] SDK builds successfully (`python -m build`)
- [x] twine check passes (`twine check dist/*`)
- [x] VS Code extension builds (`npm run compile` in vidurai-vscode-extension)
- [x] Browser extension builds (vanilla JS, no build step)
- [x] Docker images build (`docker build` for daemon and proxy)

---

## 3. PyPI Release (SDK)

1. Ensure TWINE credentials are exported:
 ```bash
 export TWINE_USERNAME="__token__"
 export TWINE_PASSWORD="<your-pypi-token>"
 ```

2. From the repo root:
 ```bash
 ./scripts/release_pypi.sh
 ```

3. Verify on PyPI:
 - Project: https://pypi.org/project/vidurai/

---

## 4. Docker Images (Daemon + Proxy)

1. Log in to Docker:
 ```bash
 docker login
 ```

2. Set registry and namespace if needed:
 ```bash
 export REGISTRY=docker.io
 export NAMESPACE=chandantochandan
 ```

3. From the repo root:
 ```bash
 ./scripts/release_docker.sh
 ```

4. Verify images on Docker Hub (example):
 - `chandantochandan/vidurai-daemon:2.0.0`
 - `chandantochandan/vidurai-proxy:2.0.0`

---

## 5. VS Code Marketplace Release

1. Ensure `vsce` is installed:
 ```bash
 npm install -g @vscode/vsce
 ```

2. Package already built:
 - `dist/vscode/vidurai-2.0.0.vsix`

3. Publish (manual step using your VS Code publisher account):
 ```bash
 cd vidurai-vscode-extension
 vsce publish --packagePath ../dist/vscode/vidurai-2.0.0.vsix
 ```

4. Verify:
 - Extension: `vidurai.vidurai`
 - Version: 2.0.0

---

## 6. Chrome Web Store Release (Browser Extension)

1. Ensure you have a Chrome Web Store developer account.

2. Upload:
 - File: `dist/browser/vidurai-browser-2.0.0.zip`

3. Use the Chrome Developer Dashboard to:
 - Select the Vidurai extension item
 - Upload the new zip
 - Submit for review

4. Verify once live:
 - Version: 2.0.0

---

## 7. Git Tag and GitHub Release

1. Create and push git tag:
 ```bash
 git tag v2.0.0
 git push origin v2.0.0
 ```

2. Create a GitHub release:
 - Tag: `v2.0.0`
 - Title: "Vidurai v2.0.0 – SF-V2 Release"
 - Attach:
 - `dist/vidurai-2.0.0.tar.gz`
 - `dist/vidurai-2.0.0-py3-none-any.whl`
 - `dist/vscode/vidurai-2.0.0.vsix`
 - `dist/browser/vidurai-browser-2.0.0.zip`

---

## 8. Post-Release

- [ ] Update docs.vidurai.ai to mention v2.0.0
- [ ] Update vidurai.ai website copy to highlight SF-V2 and Forgetting Ledger
- [ ] Announce in README and social channels

---

## Quick Reference: Artifact Locations

```
/home/user/vidurai/dist/
├── vidurai-2.0.0-py3-none-any.whl # PyPI
├── vidurai-2.0.0.tar.gz # PyPI
├── vscode/
│ └── vidurai-2.0.0.vsix # VS Code Marketplace
└── browser/
 └── vidurai-browser-2.0.0.zip # Chrome Web Store
```

---

*Generated for Vidurai v2.0.0 release cycle.*
