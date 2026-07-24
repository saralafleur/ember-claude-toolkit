---
name: team-research
description: 'Run a virtual research team (Scout, Triage Filter, Cross-Examiner, Synthesis Architect, Red Team Reviewer, and Technical Editor) to perform structured deep research and OSINT on any topic. Use when: you need to investigate a new system, protocol, codebase dependency, or design pattern; you want fact-checked, structured documentation on a topic; or you want to build on the Librarian''s existing knowledge and capture new findings permanently.'
argument-hint: 'Path to the target research folder (holds the research-brief.md or where it should be created). Optional flags: --librarian-capture'
---

# Team Research

Runs a **virtual research team** over a research objective and produces a compiled, fact-checked, and red-teamed final briefing:

- **`editor-final.md`** — The production-ready final briefing, optimized for human and LLM consumption.
- **`decisions.md`** — A log of all design decisions and clarifications approved during the research run.

This skill is an **orchestration**: you (the main agent) run the phases below and delegate each role to a specialist subagent.

## The Team (First-class agents in `agents/`)

| Agent | Role |
|-------|------|
| `scout` | OSINT & Information Retrieval. Queries APIs, scrapes documentation, harvests raw data/feeds. |
| `triage-filter` | Data Parsing & Extraction. Deduplicates raw inputs, filters out noise, maps unstructured data to schemas. |
| `cross-examiner` | Fact-Checking & Validation. Interrogates data for fallacies, contradictions, hallucinations, and outdated specs. |
| `synthesis-architect` | Thesis Synthesis. Connects data points, identifies architectural patterns, builds the thesis and knowledge graphs. |
| `red-team-reviewer` | Critique & Risk Assessment. Attacks the thesis, identifies blind spots, and defines mitigations. |
| `technical-editor` | Compilation & Formatting. Integrates mitigations, strips noise, and structures for maximum density. |

## Process

### Step 0 — Resolve Target Folder & Research Brief
1. Identify the target folder. If the user provided a path, use it. If not, ask the user: *"Which folder should I work in for this research effort?"*
2. Confirm or create the target directory. If there is a `research-brief.md` in it, load it as the objective.
3. If no `research-brief.md` exists, ask the user for the high-level research objective and create it using the `templates/research-brief.md` template.
4. Derive a date-slugged output subfolder: `<target>/research/<YYYY-MM-DD>-<slug>/`. Create a `supporting/` folder inside it.

### Step 1 — Librarian Integration: Retrieval
1. Read the librarian plugin's config file (usually at `~/.gemini/config/plugins/librarian-plugin/skills/librarian/config/library-locations.json` or relative plugin path) to locate the active `<library-root>`.
2. Check if a library is configured:
   - If the configuration is empty, **proactively prompt the user** in chat: *"No active library detected. Would you like me to initialize a new library root (e.g. `c:/repo/personal/project-library/`)?"* If they say yes, run the Librarian's setup flow to scaffold the library first.
   - If a library root is configured, check if this repository is bound to it and read the library's `TABLE-OF-CONTENTS.md`.
   - Search for topics matching the keywords or slug.
   - If a match is found, load the corresponding `.md` knowledge files from the library and pass them to the **Scout** and **Triage Filter** as seed knowledge.
   - If no library is active or bound, and the user declines setup, proceed with external lookups.

### Step 2 — Scout (Data Harvesting)
1. Invoke the `scout` agent.
2. Give it the research objective, the seed knowledge files retrieved from the Librarian (if any), and the output directory.
3. Scout performs external web searches, documentation lookups, and API queries, writing raw data and source logs to `supporting/scout-raw.md`.

### Step 3 — Triage Filter (Data Parsing & Structuring)
1. Invoke the `triage-filter` agent.
2. Give it the raw outputs in `supporting/scout-raw.md`.
3. Triage Filter parses the data, removes noise, deduplicates, maps structured items, and writes `supporting/triage-structured.md`.

### Step 4 — Cross-Examiner (Fact-Checking & Validation)
1. Invoke the `cross-examiner` agent.
2. Give it `supporting/triage-structured.md`.
3. Cross-Examiner fact-checks assertions against official documentation or live repositories, logs contradictions, and writes `supporting/cross-examiner-validated.md`.

### Step 5 — Synthesis Architect (Thesis Construction)
1. Invoke the `synthesis-architect` agent.
2. Give it the validated dataset from `supporting/cross-examiner-validated.md`.
3. Synthesis Architect connect points, highlights design patterns, maps dependencies, and writes `supporting/synthesis-thesis.md` including a conceptual Mermaid diagram.

### Step 6 — Red Team Reviewer (Stress-Testing)
1. Invoke the `red-team-reviewer` agent.
2. Give it `supporting/synthesis-thesis.md`.
3. Red Team Reviewer stress-tests assumptions, checks for edge cases and security risks, and writes its critique to `supporting/red-team-critique.md`.

### Step 7 — Technical Editor (Final Brief)
1. Invoke the `technical-editor` agent.
2. Give it the thesis (`supporting/synthesis-thesis.md`) and the critique (`supporting/red-team-critique.md`).
3. Technical Editor integrates the mitigations, removes fluff, enforces the final format, and writes the compiled report to `editor-final.md` at the root of the output subfolder.

### Step 8 — Librarian Integration: Capture
1. Prompt the user: *"Would you like to archive this compiled research into the Librarian as durable knowledge?"*
2. If they approve (or if `--librarian-capture` flag was passed):
   - **Trigger-Naming Rule:** Propose a retrieval description that describes *what future tasks will trigger loading this file*, rather than just naming the topic (e.g. "Load when migrating from SQLite to Postgres in serverless Next.js, or debugging connection pools" instead of "SQLite vs Postgres Concurrency").
   - **Taxonomy Pathing:** Map the output file to a classified namespace path in the library using the `<library-root>/knowledge/<domain>/<subdomain>/<topic>.md` structure (e.g. `knowledge/infrastructure/database/sqlite-postgres-concurrency.md`) rather than putting it in a flat folder.
   - Write the entry using the Librarian's archivist formatting, rebuild the global `TABLE-OF-CONTENTS.md`, and log the audit entry in `audit/audit-log.md`.

## Decision Logging

Whenever an agent or the orchestrator raises a question that must be answered by the user, log it in `<output-dir>/decisions.md` (from `templates/decisions.md`) using the standard statuses: `PENDING`, `DECIDED`, `PARKED`, or `SUPERSEDED`.
This prevents re-litigating questions and builds a persistent decision history.
