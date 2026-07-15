# Guide: Using Custom Agents and Subagents in Antigravity (Jetski) CLI

In Antigravity, you can define custom agents to tailor the execution context (prompts, tools, and constraints) for specific tasks. These custom agents can be used in two ways:
1.  **As a Main Agent (Interactive)**: The custom agent replaces the default agent, and you interact with it directly in the chat session.
2.  **As a Subagent (Delegated)**: The primary agent spawns the custom agent to perform a specific sub-task and report back.

---

## 1. Defining a Custom Agent (Markdown Format)

The preferred way to define a custom agent is using a Markdown file (`.md`) with YAML frontmatter.

### File Location
Save your agent definition in one of the following discovery directories:
*   **Workspace-specific**: `_agents/agents/<agent-name>.md` (or inside `_agents/agents/<agent-name>/agent.md`)
*   **User-global**: `~/.gemini/config/agents/<agent-name>.md`

### Example Definition (`refactor-helper.md`)

```markdown
---
name: refactor-helper
description: "Expert at refactoring code for readability, performance, and style guidelines. Invoke this agent when you need to clean up or optimize existing code."
tools:
  - read_file
  - replace_file_content
  - multi_replace_file_content
  - grep_search
mainAgent: true
subagent: true
---

# Persona
You are a senior software engineer specializing in code quality and refactoring. Your goal is to make code cleaner, more maintainable, and conformant to style guides.

# Guidelines
1. Prioritize readability over clever tricks.
2. Keep functions small and focused on a single responsibility.
3. Ensure no regression is introduced by verifying syntax after edits.
```

### Key Frontmatter Configuration
*   **`name`**: The unique identifier for your agent.
*   **`description`**: **Critical for subagents.** The primary agent reads this description to understand what the subagent does and decide when to invoke it.
*   **`tools`**: The list of tools this agent is allowed to use.
*   **`mainAgent`**: Set to `true` if you want to be able to chat with this agent directly.
*   **`subagent`**: Set to `true` if you want other agents to be able to delegate tasks to this agent.

---

## 2. Using a Custom Agent as the Main Agent

If you want to interact with your custom agent directly, you can switch to it via the TUI:
1.  Type `/agents` in the chat input and press **Enter** to open the agent selection panel.
2.  Select your custom agent (e.g., `refactor-helper`) from the list.
3.  The session will switch (or branch) to use the new agent persona.

---

## 3. Using a Custom Agent as a Subagent (Delegation)

When running a standard session (e.g., with the default coding agent), you can delegate specific tasks to your custom agent.

### Prerequisites
*   The custom agent must have `subagent: true` in its configuration.
*   The primary agent must have the `invoke_subagent` tool enabled (this is enabled by default for the standard coding agent).

### How to Trigger Delegation
You do not need to call tools manually. Instead, instruct the main agent in your prompt to use the subagent. 

**Example Prompts:**
*   *"Use the `refactor-helper` subagent to clean up the redundant loops in [main.go](file:///path/to/main.go)."*
*   *"Ask the `refactor-helper` to review the code quality of my changes."*

### How it Works Behind the Scenes
1.  **Discovery**: The main agent checks the list of "Available subagents" injected into its system prompt (derived from the discovered `.md` or `.json` agent files).
2.  **Matching**: The main agent matches your request against the `description` defined in the subagent's frontmatter.
3.  **Invocation**: The main agent calls the `invoke_subagent` tool, passing the subagent's `TypeName` (e.g., `refactor-helper`) and the specific `Prompt` (task) for the subagent.
4.  **Execution**: The subagent runs in a separate, isolated context (or branched workspace) to perform the task.
5.  **Reporting**: Once the subagent finishes, the main agent receives the results and presents them to you.
