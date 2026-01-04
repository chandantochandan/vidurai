#!/bin/bash
# Pre-flight check for Vidurai VS Code Extension
# Run this before manual testing in VS Code

set -e

echo "🚀 Vidurai Extension Pre-flight Check"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

echo "📁 Checking project structure..."
if [ -f "package.json" ] && [ -f "tsconfig.json" ]; then
    check_pass "Project files exist"
else
    check_fail "Missing package.json or tsconfig.json"
    exit 1
fi

echo ""
echo "🔨 Checking compiled output..."
if [ -d "out" ] && [ -f "out/extension.js" ]; then
    check_pass "Extension compiled (out/extension.js exists)"
else
    check_fail "Extension not compiled. Run: npm run compile"
    exit 1
fi

# Check all required output files
REQUIRED_FILES=("extension.js" "pythonBridge.js" "installer.js" "statusBar.js" "utils.js")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "out/$file" ]; then
        check_pass "out/$file exists"
    else
        check_fail "Missing out/$file"
    fi
done

echo ""
echo "🐍 Checking Python bridge..."
if [ -f "python-bridge/bridge.py" ]; then
    check_pass "Python bridge exists"
else
    check_fail "python-bridge/bridge.py not found"
    exit 1
fi

if [ -d "python-bridge/.venv" ]; then
    check_pass "Python virtual environment exists"
else
    check_warn "Python venv not found (may use system Python)"
fi

echo ""
echo "📦 Checking Python dependencies..."
if [ -x "python-bridge/.venv/bin/python" ]; then
    PYTHON_CMD="python-bridge/.venv/bin/python"
    check_pass "Using venv Python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    check_warn "Using system Python (python3)"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    check_warn "Using system Python (python)"
else
    check_fail "Python not found"
    exit 1
fi

# Check Vidurai module
if $PYTHON_CMD -c "import vidurai" 2>/dev/null; then
    VERSION=$($PYTHON_CMD -c "import vidurai; print(vidurai.__version__)" 2>/dev/null || echo "unknown")
    check_pass "Vidurai installed (version: $VERSION)"
else
    check_fail "Vidurai module not found. Install: pip install vidurai==1.6.1"
    exit 1
fi

echo ""
echo "🔗 Testing bridge communication..."
if node test-bridge.js 2>&1 | grep -q "Bridge test PASSED"; then
    check_pass "Bridge communication working"
else
    check_fail "Bridge communication failed"
    echo "       Run manually: node test-bridge.js"
    exit 1
fi

echo ""
echo "📋 Checking VS Code configuration..."
if [ -f ".vscode/launch.json" ]; then
    check_pass "Debug configuration exists"
else
    check_warn "No .vscode/launch.json (F5 won't work)"
fi

# Check package.json has required fields
if grep -q '"activationEvents"' package.json; then
    check_pass "Activation events configured"
else
    check_fail "Missing activationEvents in package.json"
fi

if grep -q '"main": "./out/extension.js"' package.json; then
    check_pass "Main entry point configured"
else
    check_fail "Main entry point not set correctly"
fi

# Check commands are registered
COMMANDS=("vidurai.copyContext" "vidurai.restartBridge" "vidurai.showLogs")
for cmd in "${COMMANDS[@]}"; do
    if grep -q "\"$cmd\"" package.json; then
        check_pass "Command $cmd registered"
    else
        check_fail "Command $cmd not registered in package.json"
    fi
done

echo ""
echo "======================================"
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! ($PASS_COUNT/$PASS_COUNT)${NC}"
    echo ""
    echo "Ready to test in VS Code:"
    echo "  1. Run: code ."
    echo "  2. Press F5 to launch Extension Development Host"
    echo "  3. Follow TESTING.md for test procedures"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $FAIL_COUNT check(s) failed${NC}"
    echo ""
    echo "Fix the issues above before testing."
    exit 1
fi
