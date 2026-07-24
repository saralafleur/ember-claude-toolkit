# Research Team Plugin

Six virtual research agents for Gemini CLI, structured as an orchestration pipeline (`team-research`) that collaborates to perform OSINT, fact-checking, validation, synthesis, and editing of academic papers or technical briefs.

```
Scout  ->  Triage Filter  ->  Cross-Examiner  ->  Synthesis Architect  ->  Red Team Reviewer  ->  Technical Editor
(scrapes)    (structures)       (fact-checks)           (thesis)             (critiques)           (formats)
```

## The Team

| Agent | Role | Input | Output |
|---|---|---|---|
| `scout` | Queries APIs, scrapes documentation, harvests raw data, and monitors external feeds. | High-level research objective / keywords. | Raw text, JSON payloads, uncurated papers, source URLs. |
| `triage-filter` | Deduplicates raw inputs, filters out noise, extracts relevant entities, and maps unstructured text to schema. | Raw outputs from the Scout. | Sanitized, structured key-value datasets and normalized markdown. |
| `cross-examiner` | Interrogates data for logical fallacies, source contradictions, hallucinations, and outdated information. | Structured summaries from the Triage Filter. | Validated assertions, conflict logs, anomaly flags. |
| `synthesis-architect` | Connects disparate data points, identifies latent architectural patterns, maps dependencies, and builds the thesis. | Validated datasets from the Cross-Examiner. | High-density technical briefs, taxonomy structures, and knowledge graphs. |
| `red-team-reviewer` | Attacks the thesis, identifies blind spots, stress-tests assumptions, evaluates risks. | Technical briefs from the Synthesis Architect. | Vulnerability reports, counter-arguments, refinement directives. |
| `technical-editor` | Enforces structural formatting rules, strips conversational noise, optimizes data density for human/LLM consumption. | Approved briefs post-Red Team mitigation. | Production-ready documentation, schema definitions, executive briefs. |

## Integrated Knowledge Loop (The Librarian Integration)

To build on existing knowledge and capture new findings, the research pipeline integrates directly with **The Librarian's** shared knowledge database:
* **Knowledge Retrieval**: During step 0/1, the Scout/Orchestrator queries the Librarian's Table of Contents (`TABLE-OF-CONTENTS.md` in the active library root) to search for global conventions, architectural guidelines, or lessons learned from previous similar research tasks, incorporating them directly into the planning and search phase.
* **Knowledge Capture**: After a final report is compiled by the Technical Editor, the pipeline prompts the user to run the `librarian` in `capture` mode to document the new briefs and knowledge graphs into the shared project library.

## Install

### Option A — as a plugin (recommended)
```bash
gemini extensions link /path/to/research-team-plugin
```

### Option B — plain files
Copy the skills and agents directly to your home directory:
```bash
cp -R skills/* ~/.gemini/config/skills/
cp agents/*.md ~/.gemini/config/agents/
```
