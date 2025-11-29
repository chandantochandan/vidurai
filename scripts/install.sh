#!/usr/bin/env bash
# Install Vidurai shell integration
# Usage: ./scripts/install.sh

set -euo pipefail

echo "🧠 Installing Vidurai shell integration..."
echo ""

# Detect shell
SHELL_NAME=$(basename "$SHELL")
SHELL_RC=""

case "$SHELL_NAME" in
    bash)
        SHELL_RC="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    fish)
        SHELL_RC="$HOME/.config/fish/config.fish"
        echo "⚠️  Fish shell detected. Manual installation required."
        echo "Add this to your config.fish:"
        echo "  set -gx PATH \$HOME/.vidurai/bin \$PATH"
        echo "  alias vclaude='vidurai-claude'"
        exit 1
        ;;
    *)
        echo "⚠️  Unsupported shell '$SHELL_NAME'"
        echo "Please manually add \$HOME/.vidurai/bin to your PATH"
        exit 1
        ;;
esac

# Copy wrapper script
INSTALL_DIR="$HOME/.vidurai/bin"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/vidurai-claude" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/vidurai-claude"

echo "✓ Installed vidurai-claude to $INSTALL_DIR"

# Add to PATH if not already there
if ! grep -q "$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Vidurai integration (added $(date '+%Y-%m-%d'))" >> "$SHELL_RC"
    echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
    echo "✓ Added to PATH in $SHELL_RC"
else
    echo "✓ PATH already configured in $SHELL_RC"
fi

# Add alias (optional, shorter command)
if ! grep -q "alias vclaude=" "$SHELL_RC" 2>/dev/null; then
    echo "alias vclaude='vidurai-claude'" >> "$SHELL_RC"
    echo "✓ Added 'vclaude' alias"
else
    echo "✓ Alias already configured"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "To activate, run:"
echo "  source $SHELL_RC"
echo ""
echo "Usage:"
echo "  vidurai-claude \"your question\""
echo "  vclaude \"your question\"  (short alias)"
echo ""
echo "Example:"
echo "  vidurai-claude \"What bugs did I fix today?\""
echo "  vclaude \"How does authentication work in this project?\""
echo ""
echo "जय विदुराई! 🕉️"
