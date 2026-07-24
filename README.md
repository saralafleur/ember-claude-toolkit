# Syntropy: Virtual Consulting, Software Delivery, & Knowledge Capitalization Suite

Syntropy is an agentic orchestration suite that automates software delivery pipelines and capitalizes execution memory recursively into a shared project knowledge base.

---

## Systems Architecture

The project is split into three decoupled plugins to keep process execution, memory, and structured research isolated:

1. **`delivery-team-plugin`**: The *Process Framework* (Triage $\rightarrow$ QA Mapping $\rightarrow$ TDD Implementation $\rightarrow$ Scribing $\rightarrow$ Status Auditing).
2. **`librarian-plugin`**: The *Durable Memory* (Shared library, Table of Contents indexer, and auto-load context wiring).
3. **`research-team-plugin`**: The *Research Team* (Deep OSINT research, verification synthesis, and bibliography builder).

---

## Detailed Workflow

```mermaid
graph TD
    %% Define Styles
    classDef delivery fill:#d5e8d4,stroke:#333,stroke-width:2px;
    classDef library fill:#fff2cc,stroke:#333,stroke-width:2px;
    classDef research fill:#f8cecc,stroke:#333,stroke-width:2px;
    classDef data fill:#dae8fc,stroke:#333,stroke-width:2px;

    %% Workflow Flowchart
    User[User Request] -->|1. Submit Request| DT_Intake[team-intake: Blueprinting]
    
    subgraph DT ["Delivery Team (Process Execution)"]
        DT_Intake -->|technical-plan.md| DT_QA[team-qa: Risk & Coverage Audit]
        DT_QA -->|test-plan.md| DT_Build[team-build: TDD Production]
        DT_Build -->|build-report.md| DT_Release[team-release: Release Scribe]
    end
    
    subgraph RT ["Research Team (Structured OSINT)"]
        DT_Intake -.->|Librarian Miss / Tech Uncertainty| R_Trigger[team-research: Deep Investigation]
        DT_QA -.->|Unexplored Edge Cases| R_Trigger
        R_Trigger -->|Compile Findings| R_Doc[editor-final.md]
    end
    
    subgraph TL ["The Librarian (Durable Memory)"]
        DT_Release -->|2. Recommend Capture| L_Curator[librarian-curator]
        R_Doc -->|Index & Archive| L_Curator
        L_Curator -->|3. Propose Entries| L_Gate{User Approval Gate}
        L_Gate -- Approved --> L_Archivist[librarian-archivist]
        L_Archivist -->|4. Commit & Rebuild TOC| L_Store[(Shared Library Root)]
        L_Archivist -->|Wire Repository Pointer| RepoDoc[GEMINI.md]
    end
    
    L_Store -.->|5. Autoload Context & Retrieve Lessons| DT_Intake
    L_Store -.->|5. Autoload Context & Retrieve Lessons| DT_QA

    class DT_Intake,DT_QA,DT_Build,DT_Release delivery;
    class L_Curator,L_Gate,L_Archivist library;
    class R_Trigger,R_Doc research;
    class L_Store,RepoDoc data;
```

### Integrated Knowledge Loop (Self-Improving):
* **Knowledge Retrieval**: During `team-intake` and `team-qa`, the planners check the Librarian's Table of Contents to pull in established architectural guidelines, local repository patterns, and lessons learned.
* **Research Trigger**: If triage or planning hits a blind spot (new technology, library, or API missing from the Librarian TOC), the team triggers `team-research` to investigate and archive the structured findings (`editor-final.md`) back into the Librarian's shared memory.
* **Knowledge Capture**: After a release is cut via `team-release`, you run the `librarian` in `capture` mode to document any new lessons, codebase idiosyncrasies, or environment quirks resolved during implementation.

---

## Prerequisites

- **Python 3.8+** (Required for scripting support and workspace verification).
- **Git** (Required for linking files and managing per-effort build worktrees).

---

## Installation by AI Harness

### 1. Gemini CLI / Antigravity (2.0)
Gemini CLI utilizes JSON-manifest extensions. You can install extensions in link mode:
```bash
# Link delivery-team-plugin
gemini extensions link ./delivery-team-plugin/delivery-team-plugin

# Link librarian-plugin
gemini extensions link ./librarian-plugin/librarian-plugin

# Link research-team-plugin
gemini extensions link ./research-team-plugin/research-team-plugin
```

### 2. Claude Code
Claude Code loads instructions from your local profile configurations. Run the installer script or copy the files directly:
```bash
# Create target directories
mkdir -p ~/.claude/skills ~/.claude/agents

# Copy skills
cp -R */*/skills/* ~/.claude/skills/

# Copy agent definitions
cp -R */*/agents/* ~/.claude/agents/
```

### 3. Cursor / Custom IDE Agents
The Windows installer mirrors skills/agents into `~/.cursor/skills` and `~/.cursor/agents`, and writes `.cursor/rules/syntropy.mdc`. You can also point a workspace ruleset at the plugin folders:
```markdown
# Cursor Rules Reference
Load instructions from:
- ./delivery-team-plugin/delivery-team-plugin/skills/
- ./librarian-plugin/librarian-plugin/skills/
- ./research-team-plugin/research-team-plugin/skills/
```

---

## Installation by Operating System

We provide automated platform installers in the root folder that auto-detect your active AI harness and configure directory paths.

### Windows (PowerShell)
Execute the PowerShell installer script:
```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

### macOS & Linux (Bash)
Execute the Bash installer script:
```bash
chmod +x install-mac-linux.sh
./install-mac-linux.sh
```
