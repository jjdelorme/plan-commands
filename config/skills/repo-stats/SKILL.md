---
name: repo-stats
description: >-
  Analyzes any repository's scope, file and line counts, subsystem/language breakdown,
  AST and branch complexity hotspots, and 0..5 Complexity Factor. Use this skill when
  the user asks to measure repo size, LOC, complexity, code-to-test ratio, or wants
  a visual HTML dashboard of repository statistics.
---

# Repository Scope & Complexity Analyzer (`repo-stats`)

This skill provides a deterministic, zero-dependency Python 3 analyzer ([repo_stats.py](./scripts/repo_stats.py)) paired with a `{{placeholder}}` HTML dashboard template ([report_template.html](./resources/report_template.html)).

## Architecture

- **Analysis Engine**: [scripts/repo_stats.py](./scripts/repo_stats.py) computes file/line counts, strips comments across 35+ extensions, runs Python AST cyclomatic complexity + multi-language branch density analysis, and calculates the **0..5 Complexity Factor**.
- **HTML Template**: [resources/report_template.html](./resources/report_template.html) defines the zero-dependency dark-mode UI, KPI grid, `0..5` Complexity Factor breakdown, scale legend, and tables using deterministic `{{placeholder}}` substitution.
- **Deterministic First**: Always generate HTML reports by running `repo_stats.py --html <path>` rather than hand-writing HTML from scratch. If the user asks for custom visual sections, copy [report_template.html](./resources/report_template.html), add the custom section, and pass `--template <custom_template.html>`.

## Usage Steps

Run `scripts/repo_stats.py` from this skill's directory:

1. **Terminal Summary Only**:
   ```bash
   python3 scripts/repo_stats.py /path/to/repo
   ```

2. **Generate Standalone HTML Report**:
   ```bash
   python3 scripts/repo_stats.py /path/to/repo --html /tmp/repo_report.html
   ```

3. **Generate HTML Dashboard & Serve Locally**:
   When the user asks to view the report in a browser, run with `--serve` (as a background daemon task):
   ```bash
   python3 scripts/repo_stats.py /path/to/repo --html /tmp/index.html --serve --port 8765
   ```
   *(If port `8765` is busy, `--serve` automatically increments to the next available port.)*

## Verification

- Verify that `repo_stats.py` exits with code `0` and outputs the `COMPLEXITY FACTOR (0..5)` summary.
- Confirm that no unresolved `{{...}}` placeholders remain in the generated HTML file.
- Keep the target repository's working tree clean by writing generated HTML files to `/tmp` or the conversation's scratch directory unless the user asks to commit the report.
