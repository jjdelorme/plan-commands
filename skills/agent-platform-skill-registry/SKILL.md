---
name: agent-platform-skill-registry
metadata:
  category: AiAndMachineLearning
description: >
  Interact with the Gemini Enterprise Agent Platform Skill Registry to create,
  update, install, and search for available skills. Use this skill to enable
  agents to register functionality or discover and install capabilities.
---

# Agent Platform Skill Registry

This skill provides a **zero-dependency** CLI (`scripts/skill_registry_ops.py`) for interacting with the **Skill Registry** on the Gemini Enterprise Agent Platform (`aiplatform.googleapis.com/v1beta1`).

## Key Features (Zero Friction)
- **Zero External Python Dependencies**: Uses Python standard library (`urllib.request`, `zipfile`) + `gcloud auth print-access-token` (with optional fallback to `google-auth` if installed). No `pip install` or `.venv` required.
- **Auto-Resolved Project & Region**: Automatically resolves `--project` and `--location` from `GCP_PROJECT_ID` / `GOOGLE_CLOUD_PROJECT` or `gcloud config get-value project` (defaulting region to `us-central1`).
- **Auto-Inferred Metadata & Upsert**: `upload --folder <dir>` automatically parses `name`, `# Title`, and `description` from `SKILL.md`, excludes `.venv`/`__pycache__`/`.git`, upserts (`PATCH`) if the skill already exists (`409`), and polls the Long-Running Operation (LRO) until `"done": true`.
- **Context-Safe Output**: `get` and `list` summarize `zippedFilesystem` instead of dumping megabytes of raw base64 to stdout.

---

## CLI Quick Reference (All Operations)

Set `SCRIPT="scripts/skill_registry_ops.py"` from this skill's directory (or `SCRIPT="$HOME/.gemini/config/plugins/plan-commands/skills/agent-platform-skill-registry/scripts/skill_registry_ops.py"`):

```bash
# 1. Upload or Upsert a Skill Folder (auto-reads SKILL.md & waits for LRO completion)
python3 "$SCRIPT" upload --folder "/path/to/skill-folder"

# (Optional explicit overrides on upload/update)
python3 "$SCRIPT" upload \
  --folder "/path/to/skill-folder" \
  --skill-id "my-skill" \
  --display-name "My Skill" \
  --description "What the skill does."

# 2. Install a Skill from the Registry onto This Machine
# Installs to ~/.gemini/skills/<skill-id> (--scope user, default) or ./.agents/skills/<skill-id> (--scope workspace)
python3 "$SCRIPT" install --skill-id "repo-stats" --scope user

# 3. Search Skills Semantically
python3 "$SCRIPT" search --query "repository complexity" --top-k 5

# 4. List All Skills in Registry
python3 "$SCRIPT" list

# 5. Get Skill Details (summarizes zip; use --extract-to DIR to unpack)
python3 "$SCRIPT" get --skill-id "repo-stats"

# 6. List / Get Skill Revisions
python3 "$SCRIPT" list-revision --skill-id "repo-stats"
python3 "$SCRIPT" get-revision --skill-id "repo-stats" --revision-id "1"

# 7. Delete a Skill (waits for LRO completion)
python3 "$SCRIPT" delete --skill-id "my-skill"

# 8. Monitor an LRO Manually (only needed if --no-wait was used)
python3 "$SCRIPT" monitor --operation-id "projects/.../locations/us-central1/skills/.../operations/..."
```

---

## Bootstrapping onto a Brand-New Machine (1-Liner)

On any new machine with `gcloud` and `python3` installed (before this skill exists locally), run this 1-liner to download and install `agent-platform-skill-registry` from the Skill Registry into `~/.gemini/skills/agent-platform-skill-registry`:

```bash
curl -sS -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/$(gcloud config get-value project)/locations/us-central1/skills/agent-platform-skill-registry" \
  | python3 -c 'import sys,json,base64,io,zipfile,os; d=os.path.expanduser("~/.gemini/skills/agent-platform-skill-registry"); os.makedirs(d,exist_ok=True); zipfile.ZipFile(io.BytesIO(base64.b64decode(json.load(sys.stdin)["zippedFilesystem"]))).extractall(d); print("Installed to", d)'
```

---

## Detailed Reference Guides

- **Skill Discovery**: [query-skills.md](references/query-skills.md)
- **Skill Lifecycle (Upload, Update, Install, Delete)**: [manage-skills.md](references/manage-skills.md)
- **Monitor Operations**: [monitor-operations.md](references/monitor-operations.md)
- **Generate Skill**: [generate-skill.md](references/generate-skill.md)
