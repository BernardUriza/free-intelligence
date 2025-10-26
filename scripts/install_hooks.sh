#!/bin/bash
# Install Git Hooks - Free Intelligence
#
# Installs pre-commit hooks for code quality enforcement
#
# Usage:
#   ./scripts/install_hooks.sh

set -e

echo "🔧 FREE INTELLIGENCE - GIT HOOKS INSTALLER"
echo "=========================================="
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "⚠️  pre-commit not found. Installing..."
    pip3 install pre-commit
    echo ""
fi

# Install hooks
echo "📦 Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg
echo ""

# Show installed hooks
echo "✅ Hooks installed successfully!"
echo ""
echo "📋 Installed hooks:"
echo "   1. Event Validator (UPPER_SNAKE_CASE)"
echo "   2. Mutation Validator (no update/delete)"
echo "   3. LLM Audit Policy (require @require_audit_log)"
echo "   4. LLM Router Policy (no direct API imports)"
echo "   5. Unit Tests (183 tests must pass)"
echo "   6. Commit Message Validator (Conventional Commits)"
echo ""

# Test hooks
echo "🧪 Testing hooks..."
pre-commit run --all-files || {
    echo ""
    echo "⚠️  Some hooks failed. This is normal on first run."
    echo "   Hooks will run automatically on next commit."
    echo ""
}

echo "=========================================="
echo "✅ Git hooks setup complete!"
echo ""
echo "Usage:"
echo "  • Hooks run automatically on 'git commit'"
echo "  • Run manually: pre-commit run --all-files"
echo "  • Skip hooks (emergency): git commit --no-verify"
echo ""
