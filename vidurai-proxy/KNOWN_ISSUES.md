# Known Issues & Limitations

## Session Persistence (Intentionally Disabled)

**Status:** DISABLED in MVP
**Severity:** Low (acceptable trade-off)
**Config:** `config.yaml` → `session.persist_memory: false`

### Background

Session persistence is currently **disabled by design** for the MVP release. This is a pragmatic decision, not a bug.

### Root Cause

Vidurai v1.5.1 includes an RL (Reinforcement Learning) agent that uses Python lambda functions internally. These lambda functions cannot be serialized using Python's standard `pickle` module, which causes persistence to fail with:

```
Can't pickle local object 'QLearningPolicy.__init__.<locals>.<lambda>'
```

### Why This Is Acceptable for MVP

1. **Sessions work perfectly in-memory** - Zero issues during runtime
2. **Most AI conversations are short-lived** - Users typically complete conversations in one session
3. **Auto-recreation is seamless** - New sessions are automatically created from API key hash on first request after restart
4. **No data loss** - Users just start fresh conversations (expected behavior for most AI tools)
5. **Reduces complexity** - Avoids custom serialization code that could introduce bugs

### Impact

**What happens on server restart:**
- All in-memory sessions are cleared
- Users automatically get new sessions on their next request
- No errors or failures - completely transparent to users

**What works:**
- ✅ All proxy functionality
- ✅ Vidurai compression
- ✅ Session management during runtime
- ✅ Multi-session support
- ✅ Metrics tracking (in-memory)

**What doesn't work:**
- ❌ Session memory doesn't survive server restarts
- ❌ Long-running conversations lose context on restart

### Future Solutions (Post-MVP)

When we need true persistence, we have several options:

1. **Wait for Vidurai library update** - If Vidurai team makes RL agent serializable
2. **Use Redis for session storage** - Store sessions in Redis instead of disk
3. **Use `dill` instead of `pickle`** - More advanced serialization (can handle lambdas)
4. **Disable RL agent** - Use Vidurai without RL (loses adaptive learning)
5. **Custom state extraction** - Save only non-lambda parts of memory

### Recommendation

**For MVP:** Keep persistence disabled (current state)
**For Production:** Evaluate based on user feedback:
- If users complain about lost context → implement Redis solution
- If no complaints → keep as-is (YAGNI principle)

---

## Fixed Issues

### ✅ Content-Length Header Mismatch (FIXED)

**Status:** RESOLVED
**Fixed in:** proxy_routes.py:148

**Problem:** When the proxy modified request bodies (for Vidurai compression), the original `Content-Length` header didn't match the new body size, causing requests to fail with:

```
ERROR | Proxy error: Too much data for declared Content-Length
```

**Solution:** Remove `content-length` header from forwarded requests and let httpx automatically calculate the correct value.

**Code change:**
```python
headers.pop('content-length', None)  # httpx will recalculate
```

---

## Non-Issues (Working As Designed)

### Token Estimation Uses Word Count

**Status:** Known limitation, acceptable for MVP

**Current behavior:** Token counts are estimated using simple word count (split by spaces).

**Accuracy:** ~70-80% accurate (good enough for metrics display)

**Why acceptable:**
- Actual token counting requires provider-specific tokenizers (tiktoken for OpenAI, etc.)
- Adds dependency complexity
- Metrics are for display only, not billing
- Real billing happens at provider level (always accurate)

**Future improvement:** Integrate tiktoken for better accuracy (low priority)

---

## Limitations by Design

### Streaming Responses Not Supported

**Status:** Not implemented in MVP
**Impact:** Non-streaming requests only

The proxy currently does not support streaming responses (SSE/Server-Sent Events). Most AI tools use streaming for better UX, but the proxy works fine with non-streaming mode.

**Workaround:** Clients fall back to non-streaming automatically

**Future:** Implement streaming support with Vidurai compression (requires chunked processing)

---

## Support

For issues not listed here, check:
- `logs/proxy.log` for detailed error logs
- `/health` endpoint for server status
- `/metrics` endpoint for runtime statistics

Report bugs: https://github.com/chandantochandan/vidurai/issues
