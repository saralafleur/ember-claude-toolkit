export const meta = {
  name: 'release-autopilot',
  description: 'Auto-pilot-only release pass: draft client notes, fact-check against shipped commits (with a bounded lead->scribe->lead redraft loop), finalize. Never asks -- the required-input gate and the SHIP report happen in the calling SKILL.md before/after this runs.',
  whenToUse: 'Call only after SKILL.md Step 0 has resolved the version/item list under auto-pilot, and Step 1 has resolved the output directory. Do not call for standard (non-auto-pilot) mode -- its SHIP and scope gates have no place inside a workflow script.',
  phases: [
    { title: 'Draft', detail: 'release-scribe drafts release-notes.md + crosswalk' },
    { title: 'Fact-check', detail: 'release-lead verifies claims against shipped commits, sweeps jargon, finalizes; may send back to the scribe for a targeted redraft' },
  ],
}

const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})

const version = ARGS.version
const items = Array.isArray(ARGS.items) ? ARGS.items : [] // [{slug, path, buildReportPath}]
const outputDir = ARGS.outputDir
const scopeAssumptionNote = ARGS.scopeAssumptionNote || '' // Step 0's DECIDED-AUTO scope pick, for context only
const priorCrosswalkPath = ARGS.priorCrosswalkPath || null // re-entry pass
const priorReleaseLogStatus = ARGS.priorReleaseLogStatus || null // re-entry pass

if (!version || !outputDir || !items.length) {
  throw new Error('release.js requires args: {version, items, outputDir, scopeAssumptionNote?, priorCrosswalkPath?, priorReleaseLogStatus?}')
}

const SCRIBE_SCHEMA = {
  type: 'object',
  required: ['notesWritten', 'crosswalkWritten'],
  properties: {
    notesWritten: { type: 'boolean' },
    crosswalkWritten: { type: 'boolean' },
    notesPath: { type: 'string' },
    crosswalkPath: { type: 'string' },
  },
}

const LEAD_SCHEMA = {
  type: 'object',
  required: ['finalized', 'statusToken'],
  properties: {
    finalized: { type: 'boolean' },
    statusToken: { type: 'string', description: 'HOLD -- <reason> | CLEARED | SENT <date>' },
    claimsRepaired: { type: 'array', items: { type: 'string' } },
    claimsCut: { type: 'array', items: { type: 'string' } },
    claimsAdded: { type: 'array', items: { type: 'string' } },
    greenWithCaveats: { type: 'array', items: { type: 'string' } },
    scopeReopened: { type: 'boolean' },
    needsScribeRedraft: { type: 'boolean' },
    redraftNotes: { type: 'string' },
    runLogRowAppended: { type: 'boolean' },
  },
}

const itemsBlock = items.map(i => `- ${i.slug}: ${i.path}${i.buildReportPath ? ` (build-report: ${i.buildReportPath})` : ''}`).join('\n')
const reentryBlock = priorCrosswalkPath
  ? `\n\nRe-entry pass: prior crosswalk at ${priorCrosswalkPath}${priorReleaseLogStatus ? `, prior release-log status: ${priorReleaseLogStatus}` : ''}. Apply the delta-verification rule if the prior marks + commit set are unchanged; otherwise verify from scratch.`
  : ''

// ---- Phase: Draft --------------------------------------------------------

phase('Draft')
const draft = await agent(
  `Draft the client-facing release notes for version ${version}. Items in this release:\n${itemsBlock}${scopeAssumptionNote ? `\n\nScope note: ${scopeAssumptionNote}` : ''}\n\nSeed both documents from this skill's own templates, read each item's build-report/pm-plan/plan/decisions, and write release-notes.md + release-crosswalk.md to ${outputDir}.${reentryBlock}`,
  { agentType: 'release-scribe', label: 'scribe', phase: 'Draft', schema: SCRIBE_SCHEMA },
)
if (!draft) throw new Error('release-scribe died or was skipped')

// ---- Phase: Fact-check (bounded lead -> scribe -> lead redraft loop) -----

phase('Fact-check')
let lead = await agent(
  `Fact-check ${outputDir}/release-notes.md against the actual shipped git commits for version ${version}. Items:\n${itemsBlock}\n\nRepair or cut any claim no commit supports (this binds regardless of mode -- never a stop-and-wait, always a repair mandate); add anything shipped but omitted; sweep for leaked jargon; confirm version/date; finalize; append the release-log row.${reentryBlock}`,
  { agentType: 'release-lead', label: 'lead', phase: 'Fact-check', schema: LEAD_SCHEMA },
)
if (!lead) throw new Error('release-lead died or was skipped')

let redrafts = 0
const MAX_REDRAFTS = 2
while (lead.needsScribeRedraft && redrafts < MAX_REDRAFTS) {
  redrafts += 1
  phase('Draft')
  await agent(
    `Targeted redraft of ${outputDir}/release-notes.md per the lead's request:\n${lead.redraftNotes || '(no specific notes given -- re-read the lead\'s prior finding in the crosswalk)'}`,
    { agentType: 'release-scribe', label: `scribe:redraft${redrafts}`, phase: 'Draft', schema: SCRIBE_SCHEMA },
  )
  phase('Fact-check')
  lead = await agent(
    `Re-verify ${outputDir}/release-notes.md after the targeted redraft above (redraft pass ${redrafts}). Apply the delta-verification rule -- only the redrafted claims need fresh checking, not the whole document.`,
    { agentType: 'release-lead', label: `lead:${redrafts + 1}`, phase: 'Fact-check', schema: LEAD_SCHEMA },
  )
  if (!lead) throw new Error(`release-lead died or was skipped on redraft pass ${redrafts}`)
}
if (lead.needsScribeRedraft) {
  log(`still requesting a redraft after ${MAX_REDRAFTS} passes -- returning as-is rather than looping further; the orchestrator should treat this as a HOLD and look at it directly`)
}

// ---- Return -----------------------------------------------------------------
// No filesystem access here -- release-notes.md, release-crosswalk.md, and
// the release-log row were all written by the agent that owns them, via
// that agent's own Write/Bash tools. decisions.md (if the lead reopened
// Step 0's scope) is the lead's own write too, unchanged.

return {
  status: 'ready-to-send',
  version,
  redraftPasses: redrafts,
  statusToken: lead.statusToken,
  claimsRepaired: lead.claimsRepaired || [],
  claimsCut: lead.claimsCut || [],
  claimsAdded: lead.claimsAdded || [],
  greenWithCaveats: lead.greenWithCaveats || [],
  scopeReopened: !!lead.scopeReopened,
  stillNeedsRedraft: !!lead.needsScribeRedraft,
}
