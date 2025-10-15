#!/bin/bash
# Verification script for type checking implementation
# This script validates the complete PEP 561 type checking setup

set -e  # Exit on error

echo "=========================================="
echo "Type Checking Implementation Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

# Helper function for test results
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

# Test 1: Check py.typed marker file
echo "Test 1: Checking py.typed marker file..."
if [ -f "slack_mcp/py.typed" ]; then
    pass "py.typed marker file exists"
else
    fail "py.typed marker file not found"
fi
echo ""

# Test 2: Check types.py module
echo "Test 2: Checking types.py module..."
if [ -f "slack_mcp/types.py" ]; then
    pass "types.py module exists"

    # Check for __all__ export
    if grep -q "__all__" slack_mcp/types.py; then
        pass "types.py has __all__ export"
    else
        fail "types.py missing __all__ export"
    fi

    # Check for key type definitions
    if grep -q "SlackEventPayload" slack_mcp/types.py; then
        pass "types.py contains SlackEventPayload"
    else
        fail "types.py missing SlackEventPayload"
    fi

    if grep -q "EventHandlerProtocol" slack_mcp/types.py; then
        pass "types.py contains EventHandlerProtocol"
    else
        fail "types.py missing EventHandlerProtocol"
    fi
else
    fail "types.py module not found"
fi
echo ""

# Test 3: Check pyproject.toml configuration
echo "Test 3: Checking pyproject.toml configuration..."
if grep -q "py.typed" pyproject.toml; then
    pass "pyproject.toml includes py.typed in artifacts"
else
    fail "pyproject.toml missing py.typed in artifacts"
fi
echo ""

# Test 4: Check __init__.py exports
echo "Test 4: Checking package exports..."
if grep -q "from slack_mcp import types" slack_mcp/__init__.py; then
    pass "__init__.py exports types module"
else
    fail "__init__.py missing types export"
fi

if grep -q "from slack_mcp.events import SlackEvent" slack_mcp/__init__.py; then
    pass "__init__.py exports SlackEvent"
else
    fail "__init__.py missing SlackEvent export"
fi
echo ""

# Test 5: Check CI workflow
echo "Test 5: Checking CI workflow..."
if [ -f ".github/workflows/type-check.yml" ]; then
    pass "Type checking workflow exists"

    # Validate YAML syntax
    if command -v python3 &> /dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('.github/workflows/type-check.yml'))" 2>/dev/null; then
            pass "Workflow YAML syntax is valid"
        else
            fail "Workflow YAML syntax is invalid"
        fi
    else
        warn "Python3 not available, skipping YAML validation"
    fi
else
    fail "Type checking workflow not found"
fi
echo ""

# Test 6: Run MyPy type checking
echo "Test 6: Running MyPy type checking..."
if command -v uv &> /dev/null; then
    echo "Checking types.py..."
    if uv run mypy slack_mcp/types.py --show-error-codes 2>&1 | grep -q "Success"; then
        pass "types.py passes MyPy"
    else
        fail "types.py has MyPy errors"
    fi

    echo "Checking __init__.py..."
    if uv run mypy slack_mcp/__init__.py --show-error-codes 2>&1 | grep -q "Success"; then
        pass "__init__.py passes MyPy"
    else
        fail "__init__.py has MyPy errors"
    fi

    echo "Checking events.py..."
    if uv run mypy slack_mcp/events.py --show-error-codes 2>&1 | grep -q "Success"; then
        pass "events.py passes MyPy"
    else
        fail "events.py has MyPy errors"
    fi
else
    warn "uv not available, skipping MyPy checks"
fi
echo ""

# Test 7: Test type imports
echo "Test 7: Testing type imports..."
if command -v uv &> /dev/null; then
    if uv run python -c "from slack_mcp import types; assert len(types.__all__) > 0" 2>/dev/null; then
        pass "Types module imports successfully"
    else
        fail "Failed to import types module"
    fi

    if uv run python -c "from slack_mcp import SlackEvent; assert len(SlackEvent) > 0" 2>/dev/null; then
        pass "SlackEvent imports successfully"
    else
        fail "Failed to import SlackEvent"
    fi

    # Test type guards
    if uv run python -c "from slack_mcp import types; assert types.is_slack_channel_id('C1234567890')" 2>/dev/null; then
        pass "Type guards work correctly"
    else
        fail "Type guards not working"
    fi
else
    warn "uv not available, skipping import tests"
fi
echo ""

# Test 8: Check documentation
echo "Test 8: Checking documentation..."
if [ -f "docs/contents/development/type-checking.mdx" ]; then
    pass "Type checking documentation exists"
else
    fail "Type checking documentation not found"
fi

if [ -f "docs/contents/development/ci-cd/type-checking-workflow.mdx" ]; then
    pass "Workflow documentation exists"
else
    fail "Workflow documentation not found"
fi

if [ -f "TYPE_CHECKING_GUIDE.md" ]; then
    pass "Quick reference guide exists"
else
    fail "Quick reference guide not found"
fi
echo ""

# Test 9: Check examples
echo "Test 9: Checking examples..."
if [ -f "examples/type_checking/type_checking_example.py" ]; then
    pass "Type checking example exists"

    if command -v uv &> /dev/null; then
        if uv run mypy examples/type_checking/type_checking_example.py 2>&1 | grep -q "Success"; then
            pass "Example passes MyPy"
        else
            fail "Example has MyPy errors"
        fi
    fi
else
    fail "Type checking example not found"
fi

if [ -f "examples/type_checking/README.md" ]; then
    pass "Examples README exists"
else
    fail "Examples README not found"
fi
echo ""

# Test 10: Build package and verify distribution
echo "Test 10: Verifying package distribution..."
if command -v uv &> /dev/null; then
    echo "Building package..."
    if uv build --sdist --wheel > /dev/null 2>&1; then
        pass "Package builds successfully"

        # Check sdist
        if tar -tzf dist/*.tar.gz 2>/dev/null | grep -q "slack_mcp/py.typed"; then
            pass "py.typed included in source distribution"
        else
            fail "py.typed not in source distribution"
        fi

        if tar -tzf dist/*.tar.gz 2>/dev/null | grep -q "slack_mcp/types.py"; then
            pass "types.py included in source distribution"
        else
            fail "types.py not in source distribution"
        fi

        # Check wheel
        if unzip -l dist/*.whl 2>/dev/null | grep -q "slack_mcp/py.typed"; then
            pass "py.typed included in wheel"
        else
            fail "py.typed not in wheel"
        fi

        if unzip -l dist/*.whl 2>/dev/null | grep -q "slack_mcp/types.py"; then
            pass "types.py included in wheel"
        else
            fail "types.py not in wheel"
        fi

        # Cleanup
        rm -rf dist/ build/ 2>/dev/null
    else
        fail "Package build failed"
    fi
else
    warn "uv not available, skipping package build test"
fi
echo ""

# Summary
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Type checking implementation is complete.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Please review the errors above.${NC}"
    exit 1
fi
