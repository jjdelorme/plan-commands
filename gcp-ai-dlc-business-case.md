# AI Software Factories: Landscape, Gaps, and the Google Cloud Play

Prepared 2026-09-29. All vendor facts were pulled from vendor pages on this date. Native web search was unavailable, so figures come from direct page fetches, supplemented by web searches run through the Antigravity CLI in headless mode. Every claim surfaced by that search was re-verified against the vendor's own page before inclusion; several URLs it produced did not exist and were discarded. Anything not verifiable is marked as such.

## 1. Executive summary

The AI development lifecycle loop (triage, spec, build, verify, self-improve, human gates, multiplayer) has become a commodity. Every serious player now ships the same shape: an isolated cloud sandbox per task, a pull request as the output artifact, intake from Slack, Jira, Linear and GitHub events, scheduled automations, and $20 / $100 / $200 seat tiers with usage overage. There are at least two dozen credible vendors and the tail is already dying. Charlie Labs shuts down October 5, Terragon is gone, Bloop (Vibe Kanban) folded in April, Sweep pivoted, Codegen was absorbed by ClickUp, Ona was absorbed by OpenAI, and Cursor was acquired by SpaceX.

Three things are still missing from the factories themselves: a closed loop from production outcomes back into the factory (observability vendors Datadog and Sentry now ship incident-to-fix agents, but none is wired into a factory's spec, skills or evals), verifiable provenance for agent-produced change, and a durable, shareable spec and traceability artifact. All three are infrastructure problems, not harness problems, and Google Cloud already owns most of the pieces (SPIFFE-based Agent Identity, MCP-aware Agent Gateway, SLSA L3 Cloud Build and Binary Authorization, Cloud Observability, Developer Connect lineage, a 7-day durable Agent Runtime, and the open-source Agent Executor).

Recommendation: Google Cloud should not build harness number one thousand and one. It should build the **Verified Delivery substrate** that any harness (Antigravity, Claude Code, Codex, Droid, OpenHands, Kiro) runs through to ship to production on Google Cloud. The wedge product is a signed, policy-enforced **Verified Change attestation** that binds spec, agent identity, sandbox, test evidence and reviewer, and that Binary Authorization can require at deploy time. Around it: a fleet control plane for coding agents, a production-to-agent feedback loop, and an open factory definition format. Price it on sandbox-hours, inference, and Gemini Enterprise seats, with a verified-change meter as the long-term unit.

Sizing: enterprise spend on AI coding tools was $4.0B in 2025, up from $550M in 2024 (Menlo Ventures). A bottom-up seat-plus-compute model puts the factory market at $25B to $50B annual run rate by 2030, of which the substrate layer (compute, verification, governance, observability) is 30% to 40%. That is a $8B to $20B serviceable market for a cloud provider, before pull-through on GKE, BigQuery and inference.

## 2. The landscape

### 2.1 Market map

| Tier | Players | What they own | Public scale signals |
|---|---|---|---|
| Frontier-lab factories | Anthropic Claude Code (cloud sessions, Routines, self-hosted runners), OpenAI Codex (cloud, CLI, Symphony, Ona), Google Antigravity + Jules | Model plus harness plus distribution | Codex bundled in every ChatGPT tier; Claude Code self-hosted runners in beta since Aug 2026 |
| Independent factories | Cognition Devin, Factory (Droids), Augment (Cosmos), Warp Factories, Replit, Lovable | Orchestration control plane, intake integrations, own cheaper models | Cognition $1B+ run rate, $48B valuation (Sep 2026); Factory $5B (Sep 2026); Lovable $13.3B (Aug 2026) |
| Source-host and IDE incumbents | GitHub Agent HQ + Copilot coding agent, Cursor (SpaceX), Zed Delta, JetBrains Junie, AWS Kiro, Sourcegraph Amp | Where the code and developers already are | Cursor $2B ARR headline (Mar 2026), 64%+ of Fortune 500; GitHub 180M developers, 1.4B commits/month; Copilot on usage-based credits since Jun 2026 |
| Open orchestrators | OpenHands (MIT, 89k stars), Kiro Crew (Apache), Gas Town (MIT), OpenAI Symphony (Apache, 27.5k stars), Vibe Kanban (community), GitHub Spec Kit (139k stars) | Reference patterns, no business model | Bloop shut down "couldn't find a business model" |
| Verification and review | Cursor Bugbot, CodeRabbit, Greptile, Graphite (now routing to Cursor), Qodo, Codacy, Augment Verifier, Macroscope, Ellipsis | The gate before merge | CodeRabbit $24 to $72 per dev per month plus $0.40 per agent-minute |
| Provenance and context | Entire (checkpoints, agent blame, $60M seed, ex-GitHub CEO), Sourcegraph (context layer), Tessl (skill registry and evals) | The thin layer nobody else covers | Entire CLI is MIT |
| Sandbox compute | E2B, Daytona (now closed), Modal, Runloop, Morph, Fly Sprites, Vercel Sandbox, Cloudflare Sandbox, AWS AgentCore | The metered unit under every factory | E2B and Daytona both $0.0504 per vCPU-hour; AgentCore $0.0895; Vercel $0.128 active CPU |

### 2.2 Players worth knowing that are easy to miss

- **Zed Delta** (public beta Sep 16, 2026). Not an agent product. It is a multiplayer environment built on DeltaDB, a CRDT layer over Git that records fine-grained deltas between commits and embeds conflict-free worktrees. The unit of work is a thread (agent conversation plus checkout) instead of a branch and PR. Comments anchor to deltas, not lines. Zed disabled PRs on its own repo and reports 33 people landed 570 changes to main without them. Positioning is explicit: "a quest to replace GitHub.com." Roadmap: cloud runners, web client, sandboxing. No native verification yet; agents trigger existing CI. Free in beta, then shares Zed's $10 Pro and $30 Business plans. Open-source status of Delta and DeltaDB could not be verified. This is the only player attacking the PR primitive itself, and it is the most direct answer to the multi-collaborator problem.
- **Entire.** Ties every agent session to commits with checkpoints, adds `entire blame` and `entire why`, and attributes subagent work for Claude Code and Droid. This is the provenance layer as a startup, and it shows the demand exists.
- **Augment Cosmos.** Pivoted from IDE assistant to "an always-on software delivery system from spec to verification" with role templates (PR Author, Deep Reviewer, Verifier that emits runtime evidence, Incident Investigator). Their own study: PRs per developer 16.6 to 45.5, median merge 11.2h to 3.1h, 14-day revert rate 1.9% to 0.4%.
- **OpenAI Symphony.** An Apache-2.0 Elixir reference implementation that watches Linear and spawns Codex runs. Combined with Ona's VPC-deployable environments, OpenAI now has both an orchestration pattern and enterprise compute.
- **Kiro Crew.** Amazon's Apache-2.0 multi-agent workspace, reportedly used by 39,000 Amazon builders, orchestrating any ACP harness. Kiro itself is spec-driven with automated-reasoning checks and property-based tests, and cloud sessions went GA Sep 3, 2026.
- **Warp Factories.** "Factories as code" in `factory.yaml`: agents, runners, repos, automations, scorers. Closed control plane, open worker and SDK, priced per agent run. The seven-layer "factory stack" post is the clearest published architecture, and the format is the lock-in attempt.
- **Macroscope, Ellipsis, Tessl.** Three small companies that all rebranded toward "software factory" in 2026. Ellipsis now sells cloud sandboxes for Claude Code and Codex to factories. Tessl sells a scanned skill registry with evals.
- **Poolside.** Open-weight coding model plus fully air-gapped on-prem offering for government. The only fully disconnected inference option besides OpenHands.
- **Agent Client Protocol (ACP).** Zed and JetBrains' Apache-2.0 protocol, now with 40 listed agents (Claude, Codex, Gemini CLI, Copilot, Cursor, Junie, Kiro, Droid, OpenHands) and clients including Zed, JetBrains, Devin Desktop, Neovim, Kiro Crew. This is the de facto client-side interop layer and Google should be on it.

### 2.3 What has converged

- Sandbox per task, PR as output, intake from chat and tracker, cron and webhook automations.
- $20 / $100 / $200 individual tiers, seat plus usage for teams, credits for overage.
- Model-agnostic harness plus a cheaper in-house model as the margin lever (Cognition SWE-2 "60% lower cost", Factory Router "63% cheaper", Poolside Laguna).
- Bring-your-own-compute for execution (Cursor machine pools, Amp runners, Augment daemons, Anthropic self-hosted runners, Factory Private air-gapped), while the control plane and usually inference stay with the vendor.
- Verification means an AI review bot plus existing CI plus a human reading the diff. Runtime evidence (screenshots, recordings, Playwright runs) is the newest addition.

### 2.4 What is still missing

1. **Closed loop from production.** Outcome metrics are emerging (Factory Agent Effectiveness, Cognition FrontierCode, Augment's revert-rate study, GitHub PR metrics). Incident-to-fix exists at the observability layer: Datadog Bits Code generates fixes and tests from Error Tracking and APM, Sentry Seer drafts PRs from stack traces and reviews PRs against production error data, and Harness ships Autofix workers. What no one does is feed those outcomes back into the factory's spec, skills, evals and routing automatically, or link them to the change's provenance.
2. **Provenance.** No attestation standard says which model, prompt, context, sandbox and verification produced a change. SLSA, in-toto and Sigstore have zero agent content. The OpenSSF AI/ML working group explicitly has no AI bill of materials or agent-code attestation effort. Entire is a $60M seed startup filling the gap.
3. **Spec and traceability artifact.** Kiro and Spec Kit produce spec files, Warp has `factory.yaml`, Antigravity has artifacts with no documented storage or sharing. Nobody offers spec-to-release traceability or release-centric planning, and nobody can merge conflicting intent the way Git merges text.
4. **Fleet governance.** Enterprises have three to five harnesses in use today. There is no neutral control plane that gives an administrator one view of every running coding agent, its identity, budget, egress and blast radius across harnesses.
5. **Independence.** Cursor is owned by SpaceX, Ona by OpenAI, Graphite by Cursor. Cognition keeps the "brain" in its own cloud with no BYO model keys. Buyers who need neutrality, data residency and model choice are underserved.

### 2.5 Current mindshare, September 2026

Who is setting the agenda right now, regardless of size. Sorted by category. "Latest move" is the most recent dated event found; "signal" is the strongest verified evidence of mindshare.

| Player | Category | Latest move | Signal | Why it matters to Google Cloud |
|---|---|---|---|---|
| Cognition (Devin, Devin Desktop) | Factory control plane + harness | SWE-2 model Sep 10; $1B run rate Sep 25 | $48B valuation Sep 8; Goldman, Nubank, Mercedes | Sets the enterprise bar. Brain stays in Cognition cloud, no BYO model keys, so neutrality is open |
| Factory (Droids) | Factory control plane | Factory Private air-gapped Sep 18; $200M at $5B Sep 15 | Nvidia, Adobe, EY, Adyen; "hundreds of thousands" daily devs | Model-agnostic and VPC-first. Natural tenant for Agent Runtime |
| Anthropic Claude Code | Harness | Routines, Projects, self-hosted runners Aug 6 | Most-listed harness across every factory surveyed; ACP registered | Self-hosted runners cannot route inference via Vertex today |
| OpenAI Codex + Symphony + Ona | Harness + reference orchestrator + VPC environments | Ona joined OpenAI Jun 11; Symphony 27.5k stars | Bundled in every ChatGPT tier | Vertically integrated stack from model to sandbox |
| GitHub Agent HQ, Copilot coding agent | Source host | Usage-based credits Jun 1; review agent can approve PRs Sep 1 | 180M developers; 1.4B commits/month | Owns the PR and Actions, the two steps before deploy |
| GitLab Duo Agent Platform | Source host | Flows, Orbit context graph, Claude Code and Codex as external agents; GitLab 18.8+ | Premium and Ultimate via pooled credits; self-hosted LLM support | Partner candidate for Vertex-hosted models and GKE |
| Cursor (SpaceX) | Harness | Projects with thousands of subagents Sep 10; self-hosted machine pools Sep 2; acquired Aug 14 | $2B ARR headline; 64%+ of Fortune 500 | Dominant seat, now Grok-centric. Neutrality gap for enterprises |
| Zed Delta | Collaboration and version layer | Public beta Sep 16 | 570 changes landed without PRs; Zed created ACP | Only attack on the PR primitive. Partner for Secure Source Manager |
| Warp Factories | Factory control plane | Factory Benchmarks Sep 3; LLM-judge scoring Sep 18 | Fortune 500 deployments claimed; 800k+ devs claimed | `factory.yaml` is the definition format to embrace, not fight |
| Augment Cosmos | Factory control plane | Verifier expert with runtime evidence; factory study Sep 11 | Revert rate 1.9% to 0.4%; Pure Storage 2,000 engineers | Best published evidence that verification is the ROI |
| AWS Kiro, Kiro Crew, AI-DLC | Spec harness + open orchestrator + methodology | Kiro cloud sessions GA Sep 3; Kiro Crew Aug 4; aidlc-workflows 2.10 | Kiro Crew 4.2k stars, 39k Amazon builders; aidlc-workflows 4.9k stars across 7 harnesses | The hyperscaler play to study. See 2.6 |
| Atlassian Rovo Dev | Tracker and intake | Rovo Dev Standard GA; CLI, Bitbucket, GitHub; credits rolling to Jira tiers | 45% PR cycle time cut claimed | Owns the plan and spec front door in most enterprises |
| Linear agents | Tracker and intake | Agent session API in developer preview; delegate model keeps humans as owners | Default trigger for Symphony, Factory, Codex, Devin | The intake standard. Support it natively |
| Datadog Bits Code | Observability loop | Dev agent generates fixes and tests from Error Tracking, APM, Test Optimization | Five Bits agents; 2,000+ actions in Agent Builder | Direct competitor to the feedback-loop pillar |
| Sentry Seer | Observability loop | Autofix to PR; AI code review against production errors; MCP for Claude Code, Cursor, Warp | $40 per active contributor per month | Same. Cheap and developer-loved |
| Harness AI | Delivery and deploy gate | Autofix and Code Review worker agents; OPA, RBAC, change windows; SLSA L3 demo | 150+ integrations; SOC 2, ISO 27001 | Competes for the deploy-gate position the Verified Change idea depends on |
| OpenHands | Open orchestrator | Agent Canvas runs any ACP agent; Kubernetes self-host | 89k stars, MIT; C3.ai | Neutral control plane that could ship on GKE |
| Cline | Open harness | VPC and air-gapped; BYO Vertex, Bedrock, Azure | 70k stars; Samsung, Salesforce, Visa, Lockheed logos | Already routes inference through Vertex |
| Block goose | Open harness | Hosted under Linux Foundation Agentic AI Foundation | 54.7k stars, Apache-2.0, Rust | Foundation-governed neutral agent |
| OpenSpec and GitHub Spec Kit | Spec layer | OpenSpec propose, apply, archive across 30+ tools; Spec Kit constitution to converge | OpenSpec 70.6k stars; Spec Kit 139k stars | Spec formats with real adoption. A traceability standard should read both |
| Entire | Provenance | Checkpoints, agent blame, subagent attribution | $60M seed Feb 10; ex-GitHub CEO | Validates demand for Verified Change |
| 8090 Software Factory | Regulated-enterprise factory | Series A led by Salesforce Ventures; CMS 18M lines of COBOL, 100k rules traced to source | Chamath Palihapitiya CEO; EY partnership | The audit-trail-first buyer the substrate should serve |
| Cycode | Security for the agentic lifecycle | "Agentic Development Security Platform", ADLC Security, AI-BOM | Gartner SSCS Magic Quadrant leader 2026 | AI bill of materials is already a category. Ties to Wiz |
| Overcut | Factory control plane | "The self-improving software factory", L1 to L4 maturity ladder | SOC 2 Type II; early customers | Shows how crowded the control-plane tier is |
| Tessl | Skill registry and evals | SOC 2 Sep 21; skill scanning and scoring | Cisco, Zillow, JetBrains, ByteDance | Skill supply chain for the Skill Registry to learn from |

Unverified after direct checks: Snyk Evo (page 404), ByteDance TRAE SOLO (site now shows TraeCode and TraeWork with no maker named), 8090's funding amount (counter unrendered), Overcut's YC batch, and Gartner's "AI software engineering platforms" category (all Gartner pages 403).

### 2.6 The AWS play: AI-DLC, Kiro, Kiro Crew

AWS is running the closest thing to the strategy this report recommends, and it is worth studying as both threat and template. It has three layers.

- **Methodology.** The AI-Driven Development Life Cycle, published July 31, 2025 by Raja SP on the AWS DevOps blog. Three phases: Inception, Construction, Operations. Sprints become "bolts" measured in hours or days, epics become units of work, and the team rituals are Mob Elaboration and Mob Construction. The governing rule is "AI proposes, humans decide." AI persists plans and design artifacts in the repository so context carries across sessions.
- **Open, harness-neutral tooling.** The `awslabs/aidlc-workflows` repository (MIT-0, 4.9k stars, version 2.10) turns the method into "adaptive workflow steering rules" for Claude Code, Kiro CLI and IDE, Codex CLI, Cursor, OpenCode and GitHub Copilot. It encodes 5 phases and 33 stages, 14 agents including two reviewers, 11 workflow profiles, human approval gates, "source-bound review evidence," and a 106-event audit trail with persistent state and learned rules. One core, many harnesses.
- **Product.** Kiro with EARS-style requirements, design and task specs and automated-reasoning checks; Kiro cloud sessions GA September 3; Kiro Crew, the Apache-2.0 multi-agent workspace that orchestrates any ACP harness and came out of an internal tool used by tens of thousands of Amazon builders; and Bedrock AgentCore underneath at $0.0895 per vCPU-hour for runtime.

What AWS has that Google lacks: a named methodology, a bridge from methodology to executable workflow that runs in competitors' harnesses, and an open orchestrator with an internal adoption story. What AWS lacks that Google has: per-agent cryptographic identity in IAM, an MCP-aware policy gateway, native deploy-time attestation enforcement, and DORA, which is the most cited research on AI-assisted delivery and is already Google's.

Implication for the recommendation: add a fifth deliverable to section 4. Publish a Google method for the agentic lifecycle grounded in DORA's capabilities model, and ship it as an open workflow pack that runs in Antigravity, Claude Code, Codex and Cursor, with Verified Change attestation and the spec-to-release traceability artifact built into its gates. AWS proved the harness-neutral workflow pack gets adopted. Google's version should be the one that produces a signed, deployable evidence trail.


## 3. Where Google Cloud stands today

Strong, GA and underused for this purpose:

- **Agent Identity (GA):** SPIFFE-based per-agent X.509 identity, 24-hour rotated certs, an IAM principal per agent, tokens cryptographically bound to certs. No competitor has per-agent cryptographic identity in IAM.
- **Agent Gateway (GA):** ingress and egress for all HTTP traffic including MCP and A2A, parses MCP for per-tool policy, deny-by-default, plain-language semantic policies, Model Armor. Docs already list Cursor, Claude Code and Gemini CLI as clients.
- **Agent Runtime (GA):** sessions up to 7 days, Memory Bank, sandboxes with VPC-SC and CMEK, BYOC containers, LangGraph and A2A support. Agent Executor (open source) adds event-log durable execution with snapshotting and trajectory branching.
- **Supply chain:** Cloud Build SLSA level 3 provenance, Binary Authorization attestations, Artifact Analysis SBOM and VEX, Wiz AI bill of materials in development tools.
- **Lineage and telemetry:** Developer Connect, App Hub source-commit lineage, Cloud Observability with OpenTelemetry GenAI conventions, Gemini Cloud Assist investigations that already point to "a specific line of code," DORA research.
- **Internal proof:** Google's own CISO post describes Mantis, a multi-agent SDLC guardrail with Strategist, Research and Critic agents, a reproduction sandbox, and a reflection agent writing to a global knowledge store. Core skills are open-sourced.
- **Cost position:** deferred service tier at 50% inference discount, hard project spend caps, and TPU economics for the cheap steps of a factory.

Gaps, stated plainly:

- Three unconnected coding-agent products. Jules is consumer-only and GitHub-only. Code Assist has its own quotas and a preview review agent. Antigravity is in Gemini Enterprise. None references the others.
- Antigravity agents run on the developer's host. The hosted harness (Managed Agents API) is preview and barred from production use. There is no admin view of an organization's running coding agents.
- Enterprise Antigravity is Google-models-only and lacks FedRAMP, SOC 2 and ISO 42001, while consumer tiers get Claude.
- No production-telemetry feedback into any coding agent. Cloud Assist hands off to human support only.
- Binary Authorization and SLSA docs have no agent attestation. Artifacts have no storage, sharing or export story. Skill Registry (preview) is not wired to Antigravity, and there is no private plugin marketplace or admin allowlist.
- Cloud Workstations, Cloud Build and Cloud Deploy have no agent-aware features, so a factory today must be hand-assembled from Terraform generated by the Agents CLI.

## 4. What Google Cloud should build

Name it whatever the brand allows. The working name here is **Verified Delivery on Gemini Enterprise Agent Platform**. Four components, in priority order.

### 4.1 Verified Change attestation (the wedge)

An in-toto predicate, signed with the agent's SPIFFE identity, produced automatically by any harness running through Agent Runtime or the Gateway. It binds:

- spec or requirement identifier and revision (from a versioned spec artifact),
- agent identity, harness, model and model version, skill and plugin digests,
- sandbox image digest and egress policy in force,
- verification evidence: test results, coverage delta, property-test and browser-run artifacts, review bot findings and their resolution,
- human approvals with identity and scope,
- cost in tokens and sandbox-hours.

Binary Authorization gains a policy: "production deploys require a Verified Change attestation with verification level N for paths matching X." Cloud Deploy `requireApproval` reads it. App Hub lineage displays it. Artifact Analysis stores it beside the SBOM. This is the compliance artifact regulated buyers will need within eighteen months, and it works with any harness, which makes it a substrate play rather than a harness play. Publish the predicate through OpenSSF and the Agentic AI Foundation so it becomes the standard rather than a Google format.

Technical validation: every input already exists as a Google Cloud primitive. Agent Identity supplies the signer. Cloud Build already emits SLSA L3 provenance. Binary Authorization already enforces attestations. The work is a schema, a signer library in the ADK and Agents CLI, and a policy extension.

### 4.2 Factory control plane for coding agents

Extend Agent Registry and Agent Runtime into a fleet control plane for coding agents:

- Any ACP or A2A harness registers as a runnable agent: Antigravity, Claude Code, Codex CLI, Droid, OpenHands, Kiro. Google supplies the sandbox, identity, gateway, budget and audit; the customer picks the harness and model.
- Durable, resumable runs on Agent Executor so a quarter-long migration survives restarts and model upgrades.
- An open factory definition, compatible with Warp's `factory.yaml` and Kiro's spec layout, stored in the repo and applied by the Agents CLI. Do not invent a closed format.
- A single administrator view: every running coding agent, its identity, budget burn, egress, repos touched, and pending human gates. Route human attention by risk, not by diff arrival.
- Private Skill Registry and plugin allowlist wired to Antigravity, Code Assist and third-party harnesses.

Technical validation: Agent Runtime already supports custom containers and 7-day sessions. Agent Gateway already speaks MCP and A2A and already treats Claude Code and Cursor as clients. Agent Executor already does durable execution. What is missing is productization for the coding workload and admin UX.

### 4.3 The production feedback loop

Datadog, Sentry and Harness already turn an incident into a proposed fix. Google's version should differ in two ways: the signal is native to the platform that ran the deploy, and it lands in the factory with the change's spec and attestation attached rather than as a standalone PR. Make Google Cloud the place where a factory learns from what it shipped:

- Cloud Assist investigations, Error Reporting and SLO burn alerts emit a structured "regression signal" that references the Verified Change attestations of the deploy window. The signal opens a remediation run in the factory with the original spec, evidence and agent context attached.
- An outcome ledger in BigQuery: per change, the cost, cycle time, review load, revert within 14 days, incident linkage, and DORA metrics. This is the data the evaluator and the self-improvement loop consume.
- Agent Evaluation replays past tickets against new model or skill versions before promotion. The factory itself gets a regression suite.

Technical validation: App Hub and Developer Connect already carry commit lineage. Cloud Assist already localizes faults to lines of code. Agent Evaluation and Observability are GA. The gap is plumbing and a signal schema, not new science.

### 4.4 Unify and open the first-party harness

- Merge Jules, Code Assist agent mode and Antigravity into one enterprise-available harness with one quota, one admin console and one review agent. Ship the hosted Antigravity harness as production-supported on Agent Runtime.
- Open enterprise Antigravity to partner models on Vertex. Buyers who cannot choose models will choose another platform. Neutrality is the story against SpaceX-owned Cursor and OpenAI-owned Ona.
- Adopt ACP for the client surface and A2A for agent-to-agent, and put Antigravity in the ACP registry.
- Get FedRAMP, SOC 2 and ISO 42001 on the enterprise tier. Cognition and Factory are already in process.

## 5. Why Google Cloud wins here and others cannot easily follow

- **Only cloud with per-agent cryptographic identity inside IAM.** AWS AgentCore has identity for tools, Azure has Entra agent identities, but neither binds tokens to SPIFFE certs and enforces through an MCP-aware gateway with deny-by-default. Provenance signed by that identity is defensible.
- **Owns both ends of the loop.** Sandboxed generation on one side, production telemetry with fault localization on the other. GitHub owns the middle (the PR) but not production. Startups own neither end.
- **Deploy-time enforcement point.** Binary Authorization and Cloud Deploy sit exactly where "safe to ship" is decided. A startup's factory can claim verification; only the deployment platform can require it.
- **Cost of the cheap steps.** Triage, test generation, review and eval are volume workloads. Deferred tier at half price plus TPU inference make the substrate cheaper to run than a vendor renting GPUs.
- **Internal proof at scale.** Mantis and the SDLC guardrails Google runs on itself are the reference customer story, the way Borg was for Kubernetes.
- **Neutrality.** Every major factory now has an owner with a conflicting interest. A cloud that runs any harness with any model inside the customer's perimeter is the safe enterprise choice.

## 6. Market size

Verified anchors:

| Anchor | Figure | Source, date |
|---|---|---|
| Enterprise GenAI spend | $37B in 2025, 3.2x YoY | Menlo Ventures, Dec 2025 |
| Enterprise spend on AI coding | $4.0B in 2025, from $550M in 2024 | Menlo Ventures, Dec 2025 |
| Developers worldwide | 48.4M | SlashData, Q3 2025 |
| Professional devs using AI tools | 75% (from 61% in Q1 2024) | SlashData, Apr 2026 |
| Devs using agents daily | 14.1% | Stack Overflow, 2025 |
| GitHub developers, commits | 180M, 1.4B commits/month | GitHub, Oct 2025 and Jun 2026 |
| US software developers, median pay | 1.9M jobs, $134,040 | BLS, Aug 2026 |
| Cursor recurring revenue | $2B (Bloomberg headline) | Mar 2026 |
| Cognition run rate | $1B+ | Cognition, Sep 2026 |

Gartner forecasts could not be verified (all pages returned 403) and are deliberately excluded.

Three lenses, with assumptions stated:

**Lens 1, tools spend today.** $4.0B in 2025, growing roughly 7x year over year. Even at a decelerating 3x then 2x then 1.5x, that is $36B by 2028. The market is already large enough to matter to a hyperscaler.

**Lens 2, bottom-up seats plus compute by 2030.** Assume 25M professional developers addressable (about half of 48M), 60% on a factory product, blended $1,200 per seat per year (between the $240 and $2,400 tiers observed). Seats: $18B. Compute: assume each active seat drives 40 agent PRs per month (Augment reports 45.5 per developer per month with a factory; Cursor reports cloud agents at 60% of its own merged PRs), 1.5 sandbox-hours per PR including verification, and $0.10 per sandbox-hour fully loaded. That is $72 per seat per month, or $13B. Inference on top at similar scale adds $10B to $20B. Total: $40B to $50B run rate by 2030. The substrate share (compute, verification, governance, observability, excluding seats and inference margin) is 30% to 40%, or $12B to $20B.

**Lens 3, labor share.** US developer wages alone are about $255B per year (1.9M times $134k). Global is several times that. If factories capture 10% of the value of that labor as spend, the ceiling is $100B plus. This is the a16z "three trillion dollar opportunity" framing and should be treated as a ceiling, not a plan.

Serviceable for Google Cloud in the recommended scope: $8B to $20B annual by 2030 in direct substrate revenue, plus pull-through. For reference, Microsoft reported an AI run rate of $37B in April 2026 with GitHub Copilot as a named contributor, so the incumbency threat is concrete.

## 7. Business case

**Revenue lines**

1. Sandbox and runtime compute on Agent Runtime and Cloud Run, metered per vCPU-hour and GiB-hour. Market rate is $0.05 to $0.13 per vCPU-hour, and a factory drives orders of magnitude more sandbox-hours than a chat assistant.
2. Inference, Gemini first-party and partner models through Vertex, including the deferred tier for batch steps.
3. Gemini Enterprise seats, since the unified harness ships inside the subscription.
4. Verified Change metering, a per-attested-change fee at the deploy gate, introduced once the standard is adopted. This is the durable unit because it is tied to value shipped rather than to tokens, which are deflating.
5. Pull-through: GKE, BigQuery for the outcome ledger, Cloud Observability, Secure Source Manager, Wiz.

**Defensive value.** Whoever owns the factory control plane owns where deploys land. GitHub Agent HQ plus Azure, and Kiro plus AgentCore plus Bedrock, are both trying to make that decision default to their cloud. A neutral substrate keeps Google Cloud in the path even when the harness is Claude Code or Codex.

**Cost and time.** Most components are GA. The incremental build is schema and signer (small), control plane UX and ACP/A2A adapters (medium), telemetry signal plumbing and ledger (medium), and harness unification plus compliance (large, mostly organizational). A credible first release of the attestation and control plane fits in two to three quarters. Compliance certifications gate enterprise deals more than engineering does.

**Phasing**

- Quarter 1 and 2: publish the Verified Change predicate with OpenSSF and the Agentic AI Foundation; ship signer in ADK, Agents CLI and Cloud Build; Binary Authorization policy; register Claude Code, Codex and Droid as runnable agents on Agent Runtime; admin fleet view; partner models in enterprise Antigravity.
- Quarter 3 and 4: regression signal from Cloud Assist and Error Reporting into remediation runs; outcome ledger in BigQuery with DORA metrics; factory replay evals; private Skill Registry wired to harnesses; Jules and Code Assist folded into Antigravity enterprise; SOC 2 and ISO 42001.
- Year 2: verified-change metering; spec artifact merge and traceability (RTM) as a first-class registry object; FedRAMP; DeltaDB-style thread-and-delta collaboration either through partnership with Zed or native support in Secure Source Manager.

**Success metrics.** Sandbox-hours per month on Agent Runtime, number of third-party harnesses registered, share of production deploys carrying a Verified Change attestation, revert rate and incident linkage for attested versus unattested changes, and enterprise Antigravity seats active weekly.

**Risks and mitigations**

- GitHub makes provenance native to the PR first. Mitigation: publish the standard openly and enforce at deploy, where GitHub has no presence.
- Harness vendors refuse to run inside the Google control plane. Mitigation: ACP and A2A are already theirs; the gateway already lists them as clients; make the substrate worth more to their customers than lock-in is to them.
- Internal fragmentation persists across Jules, Code Assist and Antigravity. Mitigation: this is the single largest execution risk and needs one owner and one quota.
- Tokens deflate and compute becomes the real margin. Mitigation: this favors the substrate strategy; do not build the business on inference margin.

## 8. What not to do

- Do not ship another proprietary harness as the strategy. The harness is where the thousand startups die.
- Do not invent a closed factory format. Support `factory.yaml`, Kiro specs and Spec Kit, and win on what runs underneath.
- Do not keep enterprise Antigravity Google-models-only. Neutrality is the differentiator against every acquired competitor.
- Do not treat verification as "run the agent's tests." Independent oracles, replay against production traffic, and outcome linkage are the product.

## 9. Sources

Vendor pages fetched 2026-09-29: warp.dev (blog, factory stack, pricing), zed.dev and delta.dev (introducing-delta, introducing-deltadb, delta-public-beta, roadmap, pricing), cursor.com (blog, enterprise, bugbot, joining-spacex), cognition.com and devin.ai (blog, pricing, desktop, docs deployment), factory.com (news, pricing, series-c, factory-private, agent-effectiveness), learn.chatgpt.com (cloud, pricing, changelog), github.blog and docs.github.com (Agent HQ, coding agent, usage-based billing, Octoverse 2025), code.claude.com and claude.com (web, routines, self-hosted, pricing), jules.google (usage limits, changelog), github.com/google-gemini/gemini-cli, openhands.dev, tessl.io, augmentcode.com and docs.augmentcode.com, ampcode.com and sourcegraph.com, junie.jetbrains.com and jetbrains.com/ai, kiro.dev and github.com/kirodotdev/kirocrew, agentclientprotocol.com, entire.io, ona.com, macroscope.com, ellipsis.dev, poolside.ai, magic.dev, replit.com, lovable.dev, charlielabs.ai, github.com/sweepai/sweep, codegen.com, github.com/openai/symphony, github.com/steveyegge/gastown, github.com/github/spec-kit, vibekanban.com, conductor.build, coderabbit.ai, greptile.com, graphite.com, qodo.ai, codacy.com, e2b.dev, daytona.io, modal.com, runloop.ai, cloud.morph.so, blacksmith.sh, northflank.com, fly.io/sprites, vercel.com/docs/sandbox, developers.cloudflare.com/containers, aws.amazon.com/bedrock/agentcore, azure.microsoft.com/products/ai-foundry, slsa.dev, in-toto.io, docs.sigstore.dev, github.com/ossf/ai-ml-security.

Google Cloud pages fetched: introducing-gemini-enterprise-agent-platform, whats-new-in-gemini-enterprise-agent-platform, expanding-google-antigravity-for-enterprise-customers, flexible-billing-and-cost-controls-for-agents, agent-executor blog, next26-day-2-recap, CISO perspectives (internal AI use), what-google-cloud-announced-in-ai-this-month; docs.cloud.google.com for Agent Runtime, code execution sandbox, Agent Identity, Agent Gateway, Agent Registry, Skill Registry, evaluation, observability, autonomous scheduling, Managed Agents, CodeMender, Code Assist, code review agent, quotas, Workstations, Cloud Build, Cloud Deploy, software supply chain security, Developer Connect, Cloud Assist investigations; antigravity.google docs (enterprise, plans, teamwork, sandbox, headless CLI, remote control, plugins, gcli migration); adk.dev; a2a-protocol.org; google.github.io/agents-cli.

Added in the mindshare pass: github.com/awslabs/aidlc-workflows, aws.amazon.com/blogs/devops/ai-driven-development-life-cycle, about.gitlab.com/gitlab-duo/agent-platform, atlassian.com/software/rovo-dev, datadoghq.com/product/bits-ai, sentry.io/product/seer, cline.bot/enterprise, github.com/block/goose, harness.io/products/harness-ai, linear.app/developers/agents, github.com/Fission-AI/OpenSpec, 8090.ai, overcut.ai, cycode.com, dora.dev/research/2025/dora-report.

Market data: menlovc.com (2025 State of Generative AI in the Enterprise), slashdata.co (developer population, 75% adoption post), survey.stackoverflow.co/2025, github.blog Octoverse 2025, bls.gov software developers, microsoft.com/investor FY26 Q3 and Q4, idc.com press releases Sep 2026.

Not verified and excluded: Gartner forecasts (403), Alphabet investor statements on Antigravity or Code Assist, GitHub Copilot paid-user counts, Anthropic and OpenAI coding revenue, Google Cloud Agent Platform unit pricing (page too large to fetch), Blitzy (403), Delta open-source status.
