# Skill Lifecycle Management

This document covers uploading, updating, installing, and deleting skills in the Skill Registry.

## Upload (or Upsert) Skill
Upload a skill into the Skill Registry using either a folder or a `.zip` package.
- Automatically infers `--skill-id`, `--display-name`, and `--description` from `SKILL.md` if omitted.
- Automatically falls back to `update` (`PATCH`) if the skill already exists (`409 ALREADY_EXISTS`), unless `--no-upsert` is passed.
- Automatically polls the Long-Running Operation (LRO) until completion (`--no-wait` to return immediately).
- Automatically excludes `.venv`, `venv`, `__pycache__`, `.git`, `node_modules`, and `*.pyc` when zipping `--folder`.

```bash
# Simplest 1-line upload/upsert (auto-parses SKILL.md and waits for LRO)
python3 scripts/skill_registry_ops.py upload --folder "/path/to/skill/folder"

# Explicit metadata override
python3 scripts/skill_registry_ops.py upload \
  --skill-id "my-sample-skill" \
  --display-name "My Sample Skill" \
  --description "A test skill uploaded via script." \
  --folder "/path/to/skill/folder"
```

## Install Skill Locally
Download and unpack a skill from the Skill Registry onto the local machine.
- `--skill-id` (Required): Skill ID in the registry.
- `--scope` (`user` or `workspace`, default `user`): Installs to `~/.gemini/skills/<skill-id>` (`user`) or `./.agents/skills/<skill-id>` (`workspace`).
- `--dest` (Optional): Explicit target directory path.

```bash
# Install into ~/.gemini/skills/repo-stats
python3 scripts/skill_registry_ops.py install --skill-id "repo-stats"

# Install into current repo's .agents/skills/repo-stats
python3 scripts/skill_registry_ops.py install --skill-id "repo-stats" --scope workspace
```

## Update Skill
Explicitly update an existing skill's metadata or files (`PATCH`).

```bash
python3 scripts/skill_registry_ops.py update \
  --folder "/path/to/updated/skill/folder"
```

## Delete Skill
Remove a specific skill from the registry and wait for LRO completion.

```bash
python3 scripts/skill_registry_ops.py delete --skill-id "my-skill"
```
