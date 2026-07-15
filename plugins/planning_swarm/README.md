# Planning Swarm Plugin for Google Antigravity (AGY)

An advanced multi-agent planning protocol designed to produce highly validated, well-vetted implementation plans for complex technical tasks, preventing premature convergence.

---

## 🏗️ Architecture & Components

The plugin decomposes the 5-phase planning protocol into an **Orchestrator Skill** and **5 specialized, read-only subagents**:

```text
plugins/planning_swarm/
├── plugin.json         # Plugin Manifest Metadata
├── README.md           # This Documentation
├── skills/
│   └── planning_swarm/
│       └── SKILL.md    # Master Orchestrator Skill
└── agents/
    ├── triage_scout.md       # Phase 1: FAST Repository Investigator
    ├── paradigm_selector.md  # Phase 2 (Tier 1): High-level Paradigm Evaluator
    ├── isolated_planner.md   # Phase 2 (Tier 2): Creative Solution Generator (Concurrently called)
    ├── plan_synthesizer.md   # Phase 3: Trade-off Analyzer and Merger
    └── goldfish_auditor.md   # Phase 4: Stateless 10-Lens Auditor
```

---

## ⚡ The 5-Phase Protocol

1.  **Phase 0: Socratic Pre-flight (Direct Action)**: The orchestrator interrogates the user's premise directly, sets the definition of "Done," and writes it to `done_condition.md`.
2.  **Phase 1: Triage (Delegate)**: `triage_scout` scans the codebase and determines if boundaries are crossed. If simple, it runs the Fast Path (spawns a single planner). If complex, it runs the Swarm Path.
3.  **Phase 2: Two-Tier Swarm (Delegate)**:
    *   *Tier 1 (Paradigm Selection)*: `paradigm_selector` evaluates approaches, selects the winner, and logs rejected choices.
    *   *Tier 2 (Parallel Fan-out)*: Orchestrator spawns 3 `isolated_planner` instances concurrently directly within the active workspace, assigning each a unique architectural lens (e.g. gateway intercept vs code-level routing).
4.  **Phase 3: Synthesizer Merge (Delegate)**: `plan_synthesizer` merges draft plans, generates a detailed Tradeoff Matrix, and outputs a Mermaid interaction flow/diagram representing the state machine.
5.  **Phase 4: Goldfish Stateless Audit (Delegate & Loop)**: Spawns `goldfish_auditor` as a completely fresh session, receiving *only* the synthesized plan, decisions log, and done condition. It applies 10 strict review lenses. If fatal flaws are found, it loops back (budgeted up to 2 retries) to re-synthesize or re-select the paradigm.
6.  **Final Delivery**: Presents the thoroughly vetted plan to the user for explicit signoff before execution.

---

## 🛠️ Installation

Register and install the local plugin via the `agy` CLI utility:

```bash
agy plugin install /path/to/plan-commands/plugins/planning_swarm
```

### Verification

Check that the plugin has been successfully registered and active:

```bash
agy plugin list
```

**Output**:
```json
{
  "imports": [
    {
      "name": "planning_swarm",
      "source": "antigravity",
      "importedAt": "2026-07-15T15:43:25Z",
      "components": [
        "skills",
        "agents"
      ]
    }
  ]
}
```

---

## 🔄 Usage

To trigger the `planning_swarm` protocol:

1.  **Enable the Skill**: Ensure the `planning_swarm` skill is active for your session.
2.  **Initiate Session**: Start an interactive session with `agy` and run:
    ```text
    /planning_swarm Create a plan to modernize our database connector to support connection pooling
    ```
    *Or use natural language*:
    ```text
    Please use the planning_swarm protocol to draft a plan for our OAuth migration.
    ```
3.  **Follow the Swarm**: The orchestrator will automatically run through Phase 0 to Phase 4, spawning subagents and printing state transition details directly in your console.
