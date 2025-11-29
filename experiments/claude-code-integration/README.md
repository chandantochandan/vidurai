# Vidurai + Claude Code Integration Test

## Overview
Proof-of-concept showing Vidurai can reduce token usage in Claude Code conversations.

## Setup
```bash
cd ~/vidurai/experiments/claude-code-integration
pip install vidurai
```

## Run Test
```bash
cd ~/vidurai/experiments/claude-code-integration
source ~/vidurai/.venv/bin/activate
python test_claude_code_integration.py
```

## Expected Results
- Token reduction: 36.6%+ (based on Vidurai v1.5.1 benchmarks)
- Cost savings calculation
- Context relevance scoring

## Next Steps
If successful, build VS Code extension that:
1. Intercepts Claude Code API calls
2. Routes conversations through Vidurai
3. Returns optimized context
4. Displays savings in real-time

## Files
- `claude_code_vidurai_wrapper.py` - Main wrapper class integrating Vidurai with Claude Code
- `test_claude_code_integration.py` - Test script simulating a typical coding session
- `README.md` - This file
