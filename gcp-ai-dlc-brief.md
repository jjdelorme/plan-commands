# AI Software Factories: The Google Cloud Play

*One-page brief, 2026-09-29. Full analysis, sources and sizing: [gcp-ai-dlc-business-case.md](gcp-ai-dlc-business-case.md).*

## The situation

- **The loop is solved.** Triage, spec, build, verify, human gates. Every vendor ships it the same way: sandbox per task, PR as output, Slack and Jira intake, $20 / $100 / $200 tiers.
- **The market is consolidating fast.** Cursor went to SpaceX, Ona to OpenAI, Graphite to Cursor. Charlie Labs, Terragon and Bloop shut down.
- **The money is real.** Enterprise AI coding spend went from $550M in 2024 to $4.0B in 2025. Cognition passed $1B run rate. Cursor claims $2B.

## Who matters and what they believe

| Player | Their bet |
|---|---|
| **Cognition** (Devin) | Own the whole loop and the model. Brain stays in their cloud. |
| **Factory** (Droids) | Model-agnostic control plane that runs in your VPC, even air-gapped. |
| **Anthropic** Claude Code | The best harness wins. Everyone else becomes a runner for it. |
| **OpenAI** Codex, Symphony, Ona | Vertical stack from model to sandbox, bundled in ChatGPT. |
| **GitHub** Agent HQ | Own the PR. Host every agent where the code already lives. |
| **Cursor** (SpaceX) | Own the developer seat, then fan out to thousands of cloud subagents. |
| **Zed** Delta | The PR is obsolete. Replace GitHub with live, CRDT-based agent threads. |
| **Warp** Factories | Factories as code. The `factory.yaml` format is the lock-in. |
| **AWS** AI-DLC, Kiro, Kiro Crew | Own the method. Ship it as an open workflow pack that runs in rivals' harnesses. |
| **Datadog, Sentry** | Production signal becomes the fix. Incidents open PRs. |
| **Atlassian, Linear** | Own intake. The ticket is the spec. |
| **Entire, 8090, Cycode** | Provenance and audit trail are the product regulated buyers will pay for. |

## What nobody has solved

1. **Proof.** No one can say which model, prompt, sandbox and test evidence produced a change, and prove it at deploy time.
2. **The full loop.** Observability tools propose fixes. None feeds outcomes back into the factory's spec, skills and evals.
3. **Neutral governance.** Enterprises run three to five harnesses. No single control plane covers identity, budget and blast radius across all of them.

## Our strategy: Verified Delivery

**Don't build harness number one thousand and one. Build the ground every harness runs on to reach production.**

1. **Verified Change attestation.** A signed record binding spec, agent identity, sandbox, test evidence and human approval. Binary Authorization requires it at deploy. Publish it as an open standard.
2. **Fleet control plane.** Run any harness, including Claude Code, Codex, Droid and Antigravity, on Agent Runtime with Google identity, gateway, budgets and audit.
3. **Production feedback loop.** Cloud Assist and Error Reporting send regressions back to the factory with the original spec and attestation attached.
4. **Unify our own harness.** Fold Jules and Code Assist into Antigravity. Open enterprise Antigravity to partner models. Get SOC 2 and FedRAMP.
5. **Own the method.** A DORA-grounded lifecycle, shipped as an open workflow pack that emits Verified Change at every gate. AWS proved this pattern gets adopted.

## Why we win

- **Only cloud with cryptographic identity per agent in IAM**, plus an MCP-aware gateway that already lists Claude Code and Cursor as clients.
- **We own both ends.** Sandboxed generation and production telemetry. GitHub owns only the middle.
- **We own the deploy gate.** A startup can claim verification. Only the platform can require it.
- **We can be neutral.** Every major rival now has an owner with a conflicting interest.
- **We have the research.** DORA is the most cited work on AI-assisted delivery.

## Our gaps, honestly

- Three unconnected coding products: Jules, Code Assist and Antigravity.
- Enterprise Antigravity is Google-models-only, runs on the developer's laptop, and lacks SOC 2 and FedRAMP.
- No agent awareness yet in Cloud Build, Cloud Deploy or Binary Authorization.

## The prize

- **$40B to $50B** factory market run rate by 2030.
- **$8B to $20B** serviceable for the substrate layer, before pull-through on GKE, BigQuery and inference.

## First two quarters

- Publish the Verified Change spec with OpenSSF. Ship signers in the ADK, Agents CLI and Cloud Build.
- Register Claude Code, Codex and Droid as runnable agents on Agent Runtime.
- Partner models in enterprise Antigravity.
- Release the open workflow pack.
