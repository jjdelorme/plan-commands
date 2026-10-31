#!/usr/bin/env bash
# ==============================================================================
# deploy.sh
# 
# Validates and installs the Antigravity plugin locally via `agy plugin`
# (or copies the plugin bundle into ~/.gemini/config/plugins/plan-commands).
#
# Usage:
#   ./deploy.sh                  # Validate and install plugin via agy plugin CLI
#   ./deploy.sh --target /path   # Deploy plugin bundle to a custom plugins directory
#   ./deploy.sh --dry-run        # Validate and show what would be deployed without writing
# ==============================================================================

set -euo pipefail

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="plan-commands"
TARGET_DIR="${GEMINI_CONFIG_DIR:-$HOME/.gemini/config}"
CUSTOM_TARGET=false
DRY_RUN=false

print_usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Validate and install the $PLUGIN_NAME Antigravity plugin.

Options:
  -t, --target DIR    Target config directory (default: ~/.gemini/config or \$GEMINI_CONFIG_DIR)
  -n, --dry-run       Validate and show actions without installing files
  -h, --help          Show this help message and exit

EOF
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_DIR="$2"
            CUSTOM_TARGET=true
            shift 2
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}" >&2
            print_usage
            exit 1
            ;;
    esac
done

echo -e "${BOLD}${BLUE}=== Deploying Antigravity Plugin: $PLUGIN_NAME ===${NC}"
echo -e "Source: ${BOLD}$SCRIPT_DIR${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}(Dry Run mode active - no files will be written)${NC}"
fi
echo ""

# Check manifest and component directories
if [[ ! -f "$SCRIPT_DIR/plugin.json" ]]; then
    echo -e "${RED}Error: plugin.json manifest not found at $SCRIPT_DIR/plugin.json${NC}" >&2
    exit 1
fi

if [[ ! -d "$SCRIPT_DIR/skills" ]]; then
    echo -e "${RED}Error: skills directory not found at $SCRIPT_DIR/skills${NC}" >&2
    exit 1
fi

if [[ ! -d "$SCRIPT_DIR/agents" ]]; then
    echo -e "${RED}Error: agents directory not found at $SCRIPT_DIR/agents${NC}" >&2
    exit 1
fi

# 1. Validate plugin if agy CLI is available
if command -v agy >/dev/null 2>&1; then
    echo -e "${BOLD}1. Validating plugin with 'agy plugin validate --strict'...${NC}"
    agy plugin validate --strict "$SCRIPT_DIR"
    echo ""
fi

# 2. Install via agy CLI (unless custom --target or --dry-run)
if command -v agy >/dev/null 2>&1 && [[ "$CUSTOM_TARGET" == false ]] && [[ "$DRY_RUN" == false ]]; then
    echo -e "${BOLD}2. Installing plugin via 'agy plugin install'...${NC}"
    agy plugin install "$SCRIPT_DIR"
    echo ""
    echo -e "${GREEN}${BOLD}✔ Successfully installed $PLUGIN_NAME plugin!${NC}"
    exit 0
fi

# Fallback / Custom target / Dry-run copy into <TARGET_DIR>/plugins/plan-commands
DEST_PLUGIN_DIR="$TARGET_DIR/plugins/$PLUGIN_NAME"
echo -e "${BOLD}2. Staging plugin bundle to ${DEST_PLUGIN_DIR}...${NC}"

if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$DEST_PLUGIN_DIR"
    cp "$SCRIPT_DIR/plugin.json" "$DEST_PLUGIN_DIR/"
    [[ -f "$SCRIPT_DIR/README.md" ]] && cp "$SCRIPT_DIR/README.md" "$DEST_PLUGIN_DIR/"
    [[ -d "$SCRIPT_DIR/assets" ]] && cp -R "$SCRIPT_DIR/assets" "$DEST_PLUGIN_DIR/"
    cp -R "$SCRIPT_DIR/skills" "$DEST_PLUGIN_DIR/"
    cp -R "$SCRIPT_DIR/agents" "$DEST_PLUGIN_DIR/"
fi

for skill_path in "$SCRIPT_DIR/skills"/*; do
    if [[ -d "$skill_path" ]]; then
        echo -e "  -> ${GREEN}Skill:${NC} $(basename "$skill_path")"
    fi
done

for agent_path in "$SCRIPT_DIR/agents"/*; do
    if [[ -d "$agent_path" ]]; then
        echo -e "  -> ${GREEN}Agent:${NC} $(basename "$agent_path")"
    fi
done

echo ""
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Dry run completed. No files were modified.${NC}"
else
    echo -e "${GREEN}${BOLD}✔ Successfully deployed $PLUGIN_NAME plugin to $DEST_PLUGIN_DIR!${NC}"
fi
