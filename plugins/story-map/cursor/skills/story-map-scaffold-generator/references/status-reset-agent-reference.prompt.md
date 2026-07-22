---
agent: agent
model: [model name]
description: Reset and reinitialize story-map UAT status tracking
---

# Story Map Status Reset Agent

## Purpose
Reset UAT status tracking artifacts for the story map so a new cycle can start cleanly.

This prompt supports two reset modes:
- `soft-reset` (default): Rebuild `status.md` to initial state, keep failure files
- `hard-reset`: Rebuild `status.md` and remove failure files

## Artifacts
- Tracker: `story-map/status/status.md`
- Failure folder: `story-map/status/failures/`
- Data manifest: `story-map/status/data-manifest.md`
- Schema snapshot: `story-map/status/schema.md`
- DB connection settings: `story-map/.env`
- Source workflows: `story-map/02-uat-run-sheet.md`

## Data Management Contract Support
Reset must also manage UAT data-tracking metadata so blackbox cleanup remains auditable.

`data-manifest.md` columns:
- `Run ID`
- `Scenario ID`
- `Role/Workflow`
- `Entity Type`
- `Unique Tag`
- `Where Created`
- `Cleanup Method`
- `Cleanup Status`
- `Notes`

`schema.md` handling:
- Keep `story-map/.env` intact (do not rewrite credentials/settings).
- Rebuild `story-map/status/schema.md` to a pending snapshot scaffold during reset.
- Live schema capture occurs on next UAT run startup.

## Safety Rules
- Always announce reset plan before applying changes.
- For `hard-reset`, explicitly require confirmation from user before deleting failure files.
- Never delete files outside `story-map/status/failures/`.

## Initialization Rules for New status.md
When rebuilding `status.md`:
1. Create top section `Current Failures (Active)` with no active failures placeholder row
2. Create full `Task Tracker` table with columns:
   - `Task`
   - `Role/Workflow`
   - `Current Status`
   - `Notes`
   - `Failure Link`
3. Seed tasks from `story-map/02-uat-run-sheet.md`:
   - One Happy Path row and one Edge Cases row per workflow
   - IN-SCOPE tasks => `NOT-RUN`
   - DEFERRED tasks => `DEFERRED`
   - Preserve any scope/phase column value from the run sheet for each row
4. Ensure `data-manifest.md` exists with header row and no active record rows for a fresh cycle
5. Ensure `schema.md` exists with pending snapshot metadata

## Reset Modes
### 1) soft-reset (default)
- Rebuild `status.md` to initial seeded state
- Keep existing files in `story-map/status/failures/`
- Clear all links/notes in tracker rows
- Rebuild/clear `data-manifest.md` to headers only
- Rebuild/clear `schema.md` to pending snapshot scaffold

### 2) hard-reset
- Ask user for explicit confirmation
- Rebuild `status.md` to initial seeded state
- Delete all markdown files under `story-map/status/failures/`
- Rebuild/clear `data-manifest.md` to headers only
- Rebuild/clear `schema.md` to pending snapshot scaffold

## Post-Reset Report
After reset, report:
- Mode used
- Number of tracker rows initialized
- Number of failure files retained/deleted
- Data manifest reset confirmation (`data-manifest.md` headers recreated)
- Schema snapshot reset confirmation (`schema.md` pending for next startup capture)
- Ready state confirmation for next UAT run

## Suggested Invocation
"Reset story-map UAT status using `soft-reset`"

or

"Reset story-map UAT status using `hard-reset`"
