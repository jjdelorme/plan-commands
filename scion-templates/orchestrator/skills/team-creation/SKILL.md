---
name: team-creation
description: >-
  Create or extend scion agent team templates from a high-level description of roles and workflow.[1]
  Use when the user describes a multi-agent team, panel, crew, pipeline, or any scenario
  requiring coordinated LLM agents with distinct roles. Also use when adding new roles to an
  existing team, modifying workflows, or restructuring agent coordination.[1] Produces ready-to-use
  template directories in .scion/templates/ by default, or in a custom path if specified.[1]
---

# Scion Team Creation & Extension Skill[1]

You create and extend **scion agent templates** — the blueprints that define specialized agent roles. G[1]iven a description of a team (roles, responsibilities, workflow), you produce template directories that can be used to start agents with `scion start <name> --type <template>`.

[1]When extending an existing team, review the current templates to understand the established patterns, naming, and workflow before making changes.

[1]## Template Directory Structure

[1]Each template lives in `.scion/templates/<template-name>/` and contains:

```
.scion/templates/<template-name>/
├── scion-agent.yaml       # REQUIRED: template metadata and config
├── agents.md              # REQUIRED: agent behavioral instructions
├── system-prompt.md       # REQUIRED: role persona and expertise framing
└── skills/                # OPTIONAL: harness skills (agentskills.io standard)
    └── <skill-name>/
        └── SKILL.md
```

Custom templates automatically **inh[1]erit** from the built-in `default` template, which provides shell configs, git setup, and base scion infrastructure. You do NOT need to create a `home/` d[1]irectory or duplicate any infrastructure files.

### Template Naming

- Directory nam[1]es use **kebab-case**: `panel-judge`, `code-reviewer`, `team-lead`
- Names should be descriptive of the role, not the project

## Required File Formats

### scion-agent.yaml

Every template MUST have this file. [1]Minimal valid config:

```yaml
schema_version: "1"
description: "Short description of this agent role"
agent_instructions: agents.md
system_prompt: system-prompt.md
```

Optional fields you may include when the role requires them:

```yaml
max_turns: 50              # Maximum conversation turns
max_duration: "30m"        # Maximum wall-clock time (e.g. "1h", "30m")

env:
  ROLE: "reviewer"

services:
  - name: chromium
    command: ["chromium", "--headless", "--no-sandbox", "--remote-debugging-port=9222"]
    restart: always
    ready_check:
      type: tcp
      target: "localhost:9222"
      timeout: "10s"
```

### agents.md (Agent Instructions)

[1]This file contains the behavioral in[1]structions injected into the agent's context. 

The primary contents should focus o[1]n task and job work describing what the agent should do, how it should behave, and any constraints on its work.

Do **not** include instructions on h[1]ow to use the scion CLI (starting agents, messaging, `scion look`, etc.) — every agent automatically receives base CLI operating instructions from the platform.

### system-prompt.md (Optional)

Frames the agent's persona, expertise,[1] and perspective — *who* the agent is, while `agents.md` shapes *what* it does. Example:

```markdown
# Expert Code Revie[1]wer

You are a senior software engineer with [1]deep expertise in code quality,
security, and maintainability. You approach code review methodically,
prioritizing correctness and clarity over style preferences.
```

If the role doesn't need a distinct persona, omit this file and remove the `system_prompt` line from `scion-agent.yaml`.

This file can contain broad direction ar[1]ound skillsets.

## Harness Skills

Templates can include[1] a `skills/` direct[1]ory containing reusable skill definitions that follow the [agentskills.io](https://agentskills.io/) standard. Each skill is a subdirectory with a `SKIL[1]L.md` file:

```
skills/
└── my-skill/
    └── SKILL.md
```

A `SKILL.md` file has YAML frontmatter with `name` a[1]nd `description`, followed by markdown content:

```markdown
---
name: my-skill
description: >-
  Short description of what this skill does and when the agent should use it.
---

Skill instructions and reference material here.
```

During agent provisioning, Scion automatically merges skills from the template into the correct harness-specific location (e.g. `.claude/skills/` for Claude, `.gemini/skills/` for Gemini). The agent's LLM harness discovers and loads these ski[1]lls at runtime.

Use skills to package domain knowledge, tool-usage p[1]atterns, or specialized workflows that a role needs. Skills are portable across harnesses and reusable acr[1]oss templates.

## The Orchestrator Pattern

Every team MUST have ex[1]actly one **orchestrator** (a[1]lso called lead, supervisor, or coordinator). This is the agent the user starts directly — it then [1]creates and manages the other agents.

The orchestrator's `agents.md` should focus on:

- **W[1]hat templates are available** and what each role does
- **The workflow**: when to start which agents, what tasks to give them, how to handle their results
- **Communication patterns**: what information flows be[1]tween roles and when
- **Completion criteria**: how the orchestrator knows t[1]he overall task is done

Workers don't communicate directly with each other — the orchestrator reads output from one and relays relevant information to others.

### Orchestrator agents.md Structure

```markdown
[statu[1]s reporting boilerplate]

## Role: Tea[1]m Orchestrator

You are the orchestrator for [team description]. Your job is to:
1. [high-level workflow step 1]
2. [high-level workflow step 2]

## Available Agent Roles

- `<template-1>`: [what this role does, expected input, [1]what it produces]
- `<template-2>`: [what this role does, expected input, what it produces]

## Workflow

[Step-by-step instructions: when to create agents, what to tell them,
how to handle results, when the overall task is complete.]
```

## Creating a New Team

### 1. Analyze the Description

Identify from the user's[1] description:
- **Roles**: What [1]distinct agent types are needed?
- **Workflow**: How do the agents interact? Sequential pipeline, parallel work, debate, review cycle?
- **Orchestration**: Who starts whom? Who collects results?

### 2. Design the Team Structure

- Identify one role as the **orchestrator** — the entry point the user will start
- All other roles are **workers** — started and managed by [1]the orchestrator
- Map out the communication flow

### 3. Create Templates

Fo[1]r each role, create the template directory with its files. Write worker templates first, then the orchestrator (since it[1] references worker template names).

### 4. Add Skills When Appropriate

If a role needs speciali[1]zed domain knowledge or tool-usage p[1]atterns that would benefit from being a discrete, reusable skill file rather than inline in `agents.md`, add it to the template's `skills/` directory.

### 5. Validate

- [ ] Every template has `scion-agent.yaml`[1] with `schema_version: "1"`
- [ ] Every `agents.md` starts with the status reporting boil[1]erplate
- [ ] The orchestrator references the correct template names
[1]- [ ] Template directory names are kebab-case
- [ ] The workflow matches the user's intent
- [ ] No CLI usage instructions are duplicated in templates

## Extending an Existing Team

When adding to or modifying an existing team:

### 1. Review[1] Current State

Read the existing templates in `.scion/templates/` to understand:
- The current roles and their responsibilities
- The orchestrator's workflow and how it references workers
-[1] Naming conventions and patterns already established
- Any existing skills in template `skills/` directories
- Ski[1]ll may be hard copied between templates if they are rele[1]vant to more than one type.

### 2. Determine the Change

- **Adding a role**: Create a n[1]ew worker template, then update the orchestrator's `agents.md` to reference it — add the new template to the "Available Agent Roles" section and integrate it into the workflow.
- **Modifying a role**: Update the existing template's `agents.[1]md` and/or `system-prompt.md`. Check if the orchestrator's workflow needs adjustment.
- **Chan[1]ging workflow**: Update the orchestrator's `agents.md` workflow section. May require changes to worker instructions if handoff patterns change.
- **Adding capabilities**: Consider whether the new capability belongs as inline instructions in `agents.md` or as a discrete skill in the template's `skills/` directory.

### 3. Maintain Consistency

- Follow the naming conventions a[1]lready in use
- Keep the communication patterns consistent (workers report to orchestrator)
- Update the orchestrator whenever worker templates change

## Gotchas

- **Don't duplicate CLI usage instructions**. Every agent already receives base scion CLI instructions from the platform.
- **Don't create `home/` directories** in custom templates. The[1] default template provides all infrastructure.
- **Template names = directory names**. The `description` in `s[1]cion-agent.yaml` is cosmetic; the `--type` value is the directory name.
- **Skills are harness-portable**. Write `SKILL.md` content wit[1]hout assuming a specific harness — [1]scion mounts skills into the correct location automatically.
