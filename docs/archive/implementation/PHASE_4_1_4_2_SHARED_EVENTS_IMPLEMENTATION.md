# Phase 4.1 & 4.2: Shared Event Schema Implementation

**Date:** 2025-11-25
**Version:** Vidurai v2.0.0
**Status:** Planning → Implementation

---

## Overview

This document outlines the implementation of a **unified event schema** across all Vidurai components:
- Python SDK (core library)
- Vidurai Daemon
- VS Code Extension
- Browser Extension

## Current State Analysis

### Existing Event System

| Component | Location | Type System | Notes |
|-----------|----------|-------------|-------|
| SDK | `vidurai/core/event_bus.py` | dataclass | ViduraiEvent with freeform strings |
| SDK | `vidurai/core/forgetting_ledger.py` | dataclass | ForgettingEvent for audit |
| Daemon | Uses SDK event_bus | - | Inherits from SDK |
| VS Code | `fileWatcher.ts` | Plain object | `{type, file, content}` |
| Browser | N/A | - | No structured events |

### Gaps Identified

1. **No shared module** - `vidurai/shared/` does NOT exist
2. **No TypeScript types** - `src/shared/` does NOT exist in extensions
3. **No enums** - Event types/sources/channels are freeform strings
4. **No multi-audience support** - Hints don't target developer/ai/manager audiences
5. **No Pydantic models** - Using dataclass instead of Pydantic
6. **No schema versioning** - No `schema_version` field

---

## Implementation Plan

### Phase 4.1: Python Shared Events Module

**Goal:** Create `vidurai/shared/events.py` with Pydantic models

**Files to Create:**
1. `vidurai/shared/__init__.py` - Module exports
2. `vidurai/shared/events.py` - Event models

**Models to Implement:**
```python
# Enums
EventSource: VSCODE, BROWSER, PROXY, DAEMON, CLI
EventChannel: HUMAN, AI, SYSTEM
EventKind: FILE_EDIT, TERMINAL_COMMAND, DIAGNOSTIC, AI_MESSAGE, AI_RESPONSE,
 ERROR_REPORT, MEMORY_EVENT, HINT_EVENT, METRIC_EVENT, SYSTEM_EVENT

# Base Models
BasePayload: Empty Pydantic model (placeholder)
ViduraiEvent: Main event schema with schema_version

# Specialized Payloads
HintEventPayload: Multi-audience hint support (developer/ai/manager/product/stakeholder)
```

**Coexistence Strategy:**
- New `vidurai/shared/events.py` will coexist with existing `vidurai/core/event_bus.py`
- EventBus will continue to work with its dataclass-based ViduraiEvent
- Migration to new Pydantic models will happen in future phases

### Phase 4.2: TypeScript Shared Event Types

**Goal:** Create `src/shared/events.ts` in both extensions

**Files to Create:**
1. `vidurai-vscode-extension/src/shared/events.ts`
2. `vidurai-browser-extension/src/shared/events.ts` (copy)

**Types to Implement:**
```typescript
EventSource: 'vscode' | 'browser' | 'proxy' | 'daemon' | 'cli'
EventChannel: 'human' | 'ai' | 'system'
EventKind: 'file_edit' | 'terminal_command' | 'diagnostic' | ...

ViduraiEvent<TPayload>: Generic interface with schema_version
FileEditPayload: Payload for file edits
HintEventPayload: Multi-audience hint support
```

**Integration in fileWatcher.ts:**
- Wrap existing `{type, file, content}` in full `ViduraiEvent<FileEditPayload>`
- Add `event_id` (UUID), `timestamp` (ISO), `schema_version`
- Keep bridge protocol unchanged (internal restructure only)

---

## Execution Checklist

### 4.1 Python (SDK)

- [ ] Create `vidurai/shared/__init__.py`
- [ ] Create `vidurai/shared/events.py`
- [ ] Implement EventSource enum
- [ ] Implement EventChannel enum
- [ ] Implement EventKind enum
- [ ] Implement BasePayload (Pydantic)
- [ ] Implement ViduraiEvent (Pydantic)
- [ ] Implement HintEventPayload with multi-audience
- [ ] Add exports to `__init__.py`
- [ ] Run pytest --maxfail=1

### 4.2 TypeScript (VS Code + Browser)

- [ ] Create `src/shared/events.ts` in VS Code ext
- [ ] Implement EventSource type
- [ ] Implement EventChannel type
- [ ] Implement EventKind type
- [ ] Implement ViduraiEvent interface
- [ ] Implement FileEditPayload interface
- [ ] Implement HintEventPayload interface
- [ ] Update fileWatcher.ts to use ViduraiEvent
- [ ] Add uuid generation (crypto.randomUUID or similar)
- [ ] Copy events.ts to browser extension
- [ ] Run npm run compile
- [ ] Fix any TypeScript errors

---

## Schema Design

### ViduraiEvent (Python & TypeScript)

```json
{
 "schema_version": "vidurai-events-v1",
 "event_id": "uuid-string",
 "timestamp": "2025-11-25T10:30:00.000Z",
 "source": "vscode",
 "channel": "human",
 "kind": "file_edit",
 "subtype": "save",
 "project_root": "/home/user/myproject",
 "project_id": "optional-hash",
 "session_id": "optional-session",
 "request_id": "optional-request",
 "payload": { ... }
}
```

### HintEventPayload

```json
{
 "hint_id": "uuid-string",
 "hint_type": "relevant_context",
 "text": "Consider checking auth.py for similar patterns",
 "target": "human",
 "audience": "developer",
 "surface": "vscode",
 "accepted": null,
 "latency_ms": 42
}
```

### Multi-Audience Support

| Audience | Description |
|----------|-------------|
| developer | Technical hints (code, debugging) |
| ai | Context for AI assistants |
| manager | High-level progress summaries |
| product | Feature/requirement insights |
| stakeholder | Business impact summaries |

---

## Dependencies

### Python
- `pydantic` (already in requirements for some features)

### TypeScript
- None new (crypto.randomUUID is native to Node.js 14.17+)

---

## Testing Strategy

### Python
- Run existing pytest suite to ensure no regressions
- New module is additive (no changes to existing code)

### TypeScript
- Run `npm run compile` to verify type safety
- Manual testing of file edit events in VS Code

---

## Files Modified/Created Summary

**Created:**
- `vidurai/shared/__init__.py` (NEW)
- `vidurai/shared/events.py` (NEW)
- `vidurai-vscode-extension/src/shared/events.ts` (NEW)
- `vidurai-browser-extension/src/shared/events.ts` (NEW)

**Modified:**
- `vidurai-vscode-extension/src/fileWatcher.ts` (wrap event in ViduraiEvent)

**Not Modified:**
- `vidurai/core/event_bus.py` (preserved as-is)
- Python bridge protocol (unchanged)
- Any other existing code

---

## Ready for Implementation

All prerequisites checked. Proceeding with implementation.
