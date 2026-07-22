# UAT Tag Insertion Field Matrix

Purpose: define the preferred user-input fields where the UAT agent should insert deterministic tags:

`[[UAT|<UAT_RUN_ID>|<SCENARIO_ID>|<ENTITY>|<SEQ>]]`

## Rules of Use
- Insert tags only in free-text/business-text fields that are user-visible and searchable.
- Prefer one primary tag field per created record; add secondary tag field only when needed.
- Never place tags in credentials, secrets, IDs, enum-only fields, date-only fields, or system-generated identifiers.
- If a preferred field is unavailable, use the first available fallback field listed for that workflow.

## Workflow Matrix

Populate one row per role/workflow/track discovered during the scaffold generator's discovery phase. Example shape (replace with real discovered workflows — do not leave this example row in the generated file):

| Role | Workflow | Track | Primary Tag Field | Fallback Field(s) | Entity Label |
|---|---|---|---|---|---|
| [Role] | wf-[workflow-id] | Happy Path | [free-text field on the create/submit form] | [alternate free-text field(s)] | [ENTITY_LABEL] |
| [Role] | wf-[workflow-id] | Edge Cases | [free-text field on the create/submit form] | [alternate free-text field(s)] | [ENTITY_LABEL] |

## Tag Sequence Guidance
- Start `SEQ` at `01` for first created record in each scenario.
- Increment by 1 for each additional created record in that same scenario.
- Example:
  - `[[UAT|UAT-20260301T191500Z-A7K2|PUBLIC-WF-CHANGE-REQUEST-HAPPY-01|CHANGE_REQUEST|01]]`
  - `[[UAT|UAT-20260301T191500Z-A7K2|PUBLIC-WF-CHANGE-REQUEST-HAPPY-01|CHANGE_REQUEST|02]]`

## Manifest Mapping Requirement
For each inserted tag, add a row to `story-map/status/data-manifest.md` with:
- matching `Run ID`
- matching `Scenario ID`
- `Entity Type` = `Entity Label`
- `Unique Tag` = full inserted tag token
- `Cleanup Method` = UI flow used for deletion/reversal/archive
- `Cleanup Status` initialized to `PENDING`
