# VIDURAI ACTIVE CONTEXT (Session State)

**Current Sprint:** v2.0.0 Release Hardening
**Last Updated:** 2025-11-28

---

## 🚧 Work in Progress (High-Level)

- [x] Move all `test_*.py` files into `tests/` directory.
- [x] Archive PHASE implementation docs under `docs/archive/implementation/`.
- [x] Remove legacy ChatGPT-only extension and unify under Browser extension.
- [x] Dockerize `vidurai-daemon` and `vidurai-proxy` and publish images.
- [x] Synchronize all core components to version `2.0.0`.
- [x] Add shared event schema (Python + TypeScript).
- [ ] Finalize public-facing docs for v2.0.0 (PyPI, GitHub, website).
- [ ] Update VS Code and Browser marketplace listings for v2.0.0.
- [ ] Publish v2.0.0 to PyPI and VS Code Marketplace after docs are in place.

---

## 🧠 Recent Decisions

- The RL-based v1.x design is treated as historical / foundational; SF-V2 is the primary engine going forward.
- All tools (VS Code, Browser, Daemon, Proxy, SDK) must speak the same shared event schema.
- The daemon is the recommended integration point, not ad-hoc in-process usage.
- Docker images are the preferred way to run the Daemon and Proxy.
- Version `2.0.0` is the unified identity across SDK, Daemon, Proxy, and extensions.

---

## ⚠️ Known Blockers / Risks

- PyPI and marketplace descriptions must be fully aligned with the v2.0.0 architecture before release.
- Website (vidurai.ai) still needs to be fully updated to SF-V2 + shared schema + v2.0.0 language.
- Docs must clearly explain migration for any v1.x users.

---

## ⏭️ Next Agent Action

1. Read this file completely.
2. Read `AGENTS.md` and `.cursorrules` to understand the rules.
3. Work on ONE clear task (for example: PyPI README, website section, or metadata).
4. Update this file under:
   - "🚧 Work in Progress"
   - "🧠 Recent Decisions"
   - "⚠️ Known Blockers"
   - "⏭️ Next Agent Action"

This file is the "save game" state for Vidurai. Always leave it in a consistent, truthful state.
