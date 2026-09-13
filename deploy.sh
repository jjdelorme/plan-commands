#!/usr/bin/env bash
# ==============================================================================
# deploy.sh
# 
# Deploys Swarm skill and subagent definitions into ~/.gemini/config/
#
# Usage:
#   ./deploy.sh                  # Deploy to default ~/.gemini/config/
#   ./deploy.sh --target /path   # Deploy to a custom config directory
#   ./deploy.sh --dry-run        # Show what would be deployed without copying
# ==============================================================================

set -euo pipefail

# Colors for terminal output
RED='\033[0;32m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CONFIG_DIR="$SCRIPT_DIR/config"
TARGET_DIR="${GEMINI_CONFIG_DIR:-$HOME/.gemini/config}"
DRY_RUN=false

print_usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy Swarm skill and subagents from this repository to ~/.gemini/config/

Options:
  -t, --target DIR    Target directory (default: ~/.gemini/config or \$GEMINI_CONFIG_DIR)
  -n, --dry-run       Show actions without copying files
  -h, --help          Show this help message and exit

EOF
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_DIR="$2"
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

echo -e "${BOLD}${BLUE}=== Deploying Swarm Skills & Agents ===${NC}"
echo -e "Source: ${BOLD}$SOURCE_CONFIG_DIR${NC}"
echo -e "Target: ${BOLD}$TARGET_DIR${NC}"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}(Dry Run mode active - no files will be written)${NC}"
fi
echo ""

# Check source directories
if [[ ! -d "$SOURCE_CONFIG_DIR/skills" ]]; then
    echo -e "${RED}Error: Source skills directory not found at $SOURCE_CONFIG_DIR/skills${NC}" >&2
    exit 1
fi

if [[ ! -d "$SOURCE_CONFIG_DIR/agents" ]]; then
    echo -e "${RED}Error: Source agents directory not found at $SOURCE_CONFIG_DIR/agents${NC}" >&2
    exit 1
fi

# 1. Deploy Skills
echo -e "${BOLD}1. Deploying Skills...${NC}"
TARGET_SKILLS_DIR="$TARGET_DIR/skills"
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$TARGET_SKILLS_DIR"
fi

for skill_path in "$SOURCE_CONFIG_DIR/skills"/*; do
    if [[ -d "$skill_path" ]]; then
        skill_name="$(basename "$skill_path")"
        dest_path="$TARGET_SKILLS_DIR/$skill_name"
        echo -e "  -> ${GREEN}Skill:${NC} $skill_name -> $dest_path"
        if [[ "$DRY_RUN" == false ]]; then
            mkdir -p "$dest_path"
            cp -R "$skill_path"/* "$dest_path"/
        fi
    fi
done

echo ""

# 2. Deploy Agents
echo -e "${BOLD}2. Deploying Agents...${NC}"
TARGET_AGENTS_DIR="$TARGET_DIR/agents"
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$TARGET_AGENTS_DIR"
fi

for agent_path in "$SOURCE_CONFIG_DIR/agents"/*; do
    if [[ -d "$agent_path" ]]; then
        agent_name="$(basename "$agent_path")"
        dest_path="$TARGET_AGENTS_DIR/$agent_name"
        echo -e "  -> ${GREEN}Agent:${NC} $agent_name -> $dest_path"
        if [[ "$DRY_RUN" == false ]]; then
            mkdir -p "$dest_path"
            cp -R "$agent_path"/* "$dest_path"/
        fi
    fi
done

echo ""
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Dry run completed. No files were modified.${NC}"
else
    echo -e "${GREEN}${BOLD}✔ Successfully deployed Swarm skills and agents to $TARGET_DIR!${NC}"
fi
