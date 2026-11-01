#!/usr/bin/env bash
# ==============================================================================
# deploy-opencode.sh
#
# Deterministically converts and installs the Antigravity agents and skills in
# this repository into an opencode configuration directory.
#
# Usage:
#   ./deploy-opencode.sh                     # Deploy to ~/.config/opencode (global)
#   ./deploy-opencode.sh --project /path     # Deploy to /path/.opencode (project)
#   ./deploy-opencode.sh --target /path      # Deploy to a custom opencode config dir
#   ./deploy-opencode.sh --model provider/id # Set explicit model (e.g. google/gemini-2.5-pro)
#   ./deploy-opencode.sh --dry-run           # Preview converted output without writing
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
MODEL_OVERRIDE=""
DRY_RUN=false

print_usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deterministically convert and deploy agents & skills for opencode.

Options:
  -t, --target DIR      Target opencode config directory (default: ~/.config/opencode)
  -p, --project DIR     Target project root (installs into DIR/.opencode)
  -m, --model MODEL     Optional model in provider/model-id format (default: inherit session model)
  -n, --dry-run         Validate and show actions without writing files
  -h, --help            Show this help message and exit
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_DIR="$2"
            shift 2
            ;;
        -p|--project)
            TARGET_DIR="${2%/}/.opencode"
            shift 2
            ;;
        -m|--model)
            MODEL_OVERRIDE="$2"
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
            echo -e "${RED}Unknown option: $1${NC}" >&2
            print_usage
            exit 1
            ;;
    esac
done

echo -e "${BOLD}${BLUE}=== Deploying to opencode ===${NC}"
echo -e "Source: ${BOLD}$SCRIPT_DIR${NC}"
echo -e "Target: ${BOLD}$TARGET_DIR${NC}"
if [[ -n "$MODEL_OVERRIDE" ]]; then
    echo -e "Model:  ${BOLD}$MODEL_OVERRIDE${NC}"
else
    echo -e "Model:  ${BOLD}(inherit active session model)${NC}"
fi
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}(Dry Run mode active - no files will be written)${NC}"
fi
echo ""

python3 - "$SCRIPT_DIR" "$TARGET_DIR" "$MODEL_OVERRIDE" "$DRY_RUN" <<'PYEOF'
import os
import re
import shutil
import sys
from pathlib import Path

script_dir = Path(sys.argv[1]).resolve()
target_dir = Path(sys.argv[2]).expanduser().resolve()
model_override = sys.argv[3].strip()
dry_run = sys.argv[4].lower() == "true"

agents_src = script_dir / "agents"
skills_src = script_dir / "skills"

agents_dst = target_dir / "agents"
skills_dst = target_dir / "skills"

# Tool name replacements for prompt bodies and skills
TOOL_REPLACEMENTS = [
    (r"\brun_command\b", "bash"),
    (r"\bview_file\b", "read"),
    (r"\bwrite_to_file\b", "write"),
    (r"\breplace_file_content\b", "edit"),
    (r"\bgrep_search\b", "grep"),
    (r"\bfind_by_name\b", "glob"),
    (r"\blist_dir\b", "read"),
    (r"\bask_question\b", "question"),
    (r"\binvoke_subagent\b", "task"),
    (r"\bdefine_subagent\b", "task"),
    (r"\bstart_subagent\b", "task"),
]

# Scoped edit permissions per agent role in opencode format
# Note: opencode evaluates the LAST matching rule, so broad '*' goes first and narrow globs last.
AGENT_EDIT_PERMISSIONS = {
    "architect": [
        ("*", "deny"),
        ("plans/**", "allow"),
    ],
    "product_owner": [
        ("*", "deny"),
        ("plans/**", "allow"),
    ],
    "auditor": [
        ("*", "deny"),
        ("plans/audit/**", "allow"),
    ],
    "reverse_engineer": [
        ("*", "deny"),
        ("okf/**", "allow"),
    ],
    "engineer": "allow",
}


def parse_frontmatter(text: str):
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("Missing YAML frontmatter delimiter '---'")
    fm_text, body = match.group(1), match.group(2)

    meta = {}
    tools = []
    in_tools = False
    for line in fm_text.splitlines():
        if re.match(r"^\s*-\s+", line) and in_tools:
            tools.append(re.sub(r"^\s*-\s+", "", line).strip())
            continue
        if ":" in line and not line.startswith(" "):
            in_tools = False
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if key == "tools":
                in_tools = True
            else:
                meta[key] = val
    meta["tools"] = tools
    return meta, body


def rewrite_body(body: str) -> str:
    out = body
    for pattern, repl in TOOL_REPLACEMENTS:
        out = re.sub(pattern, repl, out)
    return out


def build_opencode_agent_md(agent_name: str, meta: dict, body: str) -> str:
    description = meta.get("description", "")
    max_turns = meta.get("max_turns", "")
    main_agent = meta.get("mainAgent", "").lower() == "true"
    sub_agent = meta.get("subagent", "").lower() == "true"

    if main_agent and sub_agent:
        mode = "all"
    elif sub_agent:
        mode = "subagent"
    else:
        mode = "primary"

    lines = ["---"]
    # Quote description safely for YAML
    escaped_desc = description.replace("\\", "\\\\").replace('"', '\\"')
    lines.append(f'description: "{escaped_desc}"')
    lines.append(f"mode: {mode}")

    if model_override:
        lines.append(f"model: {model_override}")

    if max_turns.isdigit():
        lines.append(f"steps: {max_turns}")

    # Build permission block
    edit_perm = AGENT_EDIT_PERMISSIONS.get(agent_name, "allow")
    lines.append("permission:")
    if isinstance(edit_perm, list):
        lines.append("  edit:")
        for glob_pat, action in edit_perm:
            lines.append(f'    "{glob_pat}": {action}')
    else:
        lines.append(f"  edit: {edit_perm}")

    if agent_name == "reverse_engineer":
        lines.append("  task: allow")

    lines.append("---")
    converted_body = rewrite_body(body)
    return "\n".join(lines) + "\n" + converted_body


# 1. Convert Agents: agents/<name>/agent.md -> <target>/agents/<name>.md
if not dry_run:
    agents_dst.mkdir(parents=True, exist_ok=True)

for agent_dir in sorted(agents_src.iterdir()):
    agent_file = agent_dir / "agent.md"
    if not agent_dir.is_dir() or not agent_file.is_file():
        continue

    agent_name = agent_dir.name
    raw = agent_file.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    converted = build_opencode_agent_md(agent_name, meta, body)

    dest_file = agents_dst / f"{agent_name}.md"
    if not dry_run:
        dest_file.write_text(converted, encoding="utf-8")
    print(f"  -> \033[0;32mAgent:\033[0m {agent_name} -> {dest_file}")

# 2. Copy Skills directly: skills/<name>/ -> <target>/skills/<name>/
if not dry_run:
    skills_dst.mkdir(parents=True, exist_ok=True)

for skill_dir in sorted(skills_src.iterdir()):
    if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").is_file():
        continue

    skill_name = skill_dir.name
    dest_skill_dir = skills_dst / skill_name

    if not dry_run:
        if dest_skill_dir.exists() or dest_skill_dir.is_symlink():
            if dest_skill_dir.is_symlink() or dest_skill_dir.is_file():
                dest_skill_dir.unlink()
            else:
                shutil.rmtree(dest_skill_dir)
        shutil.copytree(skill_dir, dest_skill_dir)

    print(f"  -> \033[0;32mSkill:\033[0m {skill_name} -> {dest_skill_dir}/SKILL.md")
PYEOF

echo ""
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Dry run completed. No files were modified.${NC}"
else
    echo -e "${GREEN}${BOLD}✔ Successfully converted and deployed to $TARGET_DIR!${NC}"
    echo -e "${YELLOW}Note: Quit and restart opencode for the newly deployed agents and skills to take effect.${NC}"
fi
