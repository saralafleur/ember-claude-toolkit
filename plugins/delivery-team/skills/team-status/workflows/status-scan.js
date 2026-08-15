export const meta = {
  name: 'status-scan',
  description: 'team-status per-item scanner fan-out (dynamic N, from the already-gated RESCAN-CANDIDATE list) plus the status-lead synthesis',
  whenToUse: 'Invoked by team-status Step 2, only after Step 1.5\'s human gate has resolved which items to rescan and which to carry forward from cache. Requires args {targetDir, reportPath, itemsToScan, skippedItems, triageInventory}; optional args cover prior-run context, cosmetic-downgrade annotations, and shared-stack wave capping -- see below.',
  phases: [
    { title: 'Scan', detail: 'one status-scanner per item marked RESCAN, fanned out dynamically over a runtime-computed list, optionally wave-capped' },
    { title: 'Synthesize', detail: 'status-lead merges scan results + carried-forward SKIP items into status-report.md' },
  ],
}

const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})

const targetDir = ARGS.targetDir
const reportPath = ARGS.reportPath
const items = Array.isArray(ARGS.itemsToScan) ? ARGS.itemsToScan : [] // [{slug, path, fieldChangedDiff?}]
const skippedItems = Array.isArray(ARGS.skippedItems) ? ARGS.skippedItems : [] // [{slug, path, reason}]
const triageInventory = ARGS.triageInventory || null
const priorReportPath = ARGS.priorReportPath || null
const lastRun = ARGS.lastRun || null
const statusDecisionsPath = ARGS.statusDecisionsPath || null
const cosmeticDowngradeAnnotations = Array.isArray(ARGS.cosmeticDowngradeAnnotations) ? ARGS.cosmeticDowngradeAnnotations : []
const unverifiedSinceLastRun = Array.isArray(ARGS.unverifiedSinceLastRun) ? ARGS.unverifiedSinceLastRun : []
const batchWideFindings = ARGS.batchWideFindings || null // on a force-full-rescan with a prior report
const capConcurrency = !!ARGS.capConcurrency // orchestrator already checked PROJECT-CONTEXT.md for a shared dev/test stack
const waveSize = Number.isInteger(ARGS.waveSize) && ARGS.waveSize > 0 ? ARGS.waveSize : 8

if (!targetDir || !reportPath) {
  throw new Error('status-scan.js requires args: {targetDir, reportPath, itemsToScan, skippedItems, triageInventory, ...}')
}

const SCANNER_SCHEMA = {
  type: 'object',
  required: ['slug', 'stage', 'scratchWritten', 'fingerprintWritten'],
  properties: {
    slug: { type: 'string' },
    stage: { type: 'string', description: 'one of: not-started, intake-only, qa-done, build-in-progress, build-green, build-green-with-qa-debt, build-green-with-caveats, stale, blocked' },
    scratchWritten: { type: 'boolean' },
    fingerprintWritten: { type: 'boolean' },
    discrepancies: { type: 'array', items: { type: 'string' } },
    openDecisions: { type: 'array', items: { type: 'string' } },
    crossItemDrift: { type: 'array', items: { type: 'string' } },
    catalogIdsCited: { type: 'array', items: { type: 'string' } },
  },
}

const LEAD_SCHEMA = {
  type: 'object',
  required: ['statusReportWritten', 'recommendedNextAction'],
  properties: {
    statusReportWritten: { type: 'boolean' },
    recommendedNextAction: {
      type: 'object',
      properties: { skill: { type: 'string' }, folder: { type: 'string' }, why: { type: 'string' } },
    },
    parallelizationOpportunity: { type: 'string' },
    runLogRowAppended: { type: 'boolean' },
  },
}

// ---- Phase: Scan (dynamic N, optionally wave-capped) -----------------------

phase('Scan')
log(`scanning ${items.length} item(s), carrying forward ${skippedItems.length} unchanged item(s) from cache${capConcurrency ? `, wave-capped at ${waveSize} concurrent scanners (shared dev/test stack)` : ''}`)

function scannerPrompt(item) {
  const fieldChangedBlock = item.fieldChangedDiff
    ? `\n\nThis item was flagged RESCAN by the fingerprint re-check -- here's exactly which field(s) changed, look there first:\n${item.fieldChangedDiff}`
    : ''
  const decisionsBlock = statusDecisionsPath
    ? `\n\nPrior-run acceptances/dispositions (an input, not just this run's): ${statusDecisionsPath}`
    : ''
  const batchWideBlock = batchWideFindings
    ? `\n\nKnown batch-wide findings from the prior report -- confirm or contradict in one command, don't re-derive:\n${typeof batchWideFindings === 'string' ? batchWideFindings : JSON.stringify(batchWideFindings)}`
    : ''
  return `Reconcile intent vs. last-reported state for the work item at ${item.path} (slug: ${item.slug}). Re-verify every load-bearing claim against the live code -- re-run cited tests, grep cited files, check cited endpoints. Classify the stage and flag drift. Write scratch findings to ${targetDir}/.status-scratch/${item.slug}.md, then write the fingerprint frontmatter via write_fingerprint.py per this skill's own convention.${fieldChangedBlock}${decisionsBlock}${batchWideBlock}`
}

let scanResults = []
if (capConcurrency && items.length > waveSize) {
  for (let i = 0; i < items.length; i += waveSize) {
    const wave = items.slice(i, i + waveSize)
    log(`wave ${Math.floor(i / waveSize) + 1}: scanning ${wave.map(w => w.slug).join(', ')}`)
    const waveResults = await parallel(wave.map(item => () =>
      agent(scannerPrompt(item), { agentType: 'status-scanner', label: `scan:${item.slug}`, phase: 'Scan', schema: SCANNER_SCHEMA }),
    ))
    scanResults = scanResults.concat(waveResults)
  }
} else {
  scanResults = await parallel(items.map(item => () =>
    agent(scannerPrompt(item), { agentType: 'status-scanner', label: `scan:${item.slug}`, phase: 'Scan', schema: SCANNER_SCHEMA }),
  ))
}

const scanned = scanResults.filter(Boolean)
const diedCount = items.length - scanned.length
if (diedCount > 0) log(`${diedCount} of ${items.length} scanner(s) died or were skipped -- status-lead will see those items as unscanned, not silently omitted`)

// ---- Phase: Synthesize -------------------------------------------------------

phase('Synthesize')
const lead = await agent(
  `Merge these scanner findings and the carried-forward cached items into ${reportPath} -- the full stage-map (Intake/QA/Build/Merged columns) plus the Ready-for-Deployment table, report-vs-reality discrepancies, open decisions, cross-item drift, a parallelization-opportunity check, the in-flight engineering-manager dispatch check, and the single recommended next action. Triage inventory: ${typeof triageInventory === 'string' ? triageInventory : JSON.stringify(triageInventory)}\n\nFreshly scanned: ${scanned.map(s => s.slug).join(', ') || '(none)'}\nCarried forward from cache: ${skippedItems.map(s => `${s.slug} (${s.reason || 'unchanged'})`).join(', ') || '(none)'}\nDied/unscanned: ${items.filter(i => !scanned.find(s => s.slug === i.slug)).map(i => i.slug).join(', ') || '(none)'}${cosmeticDowngradeAnnotations.length ? `\nCosmetic-downgrade annotations (surface these, don't hide them): ${cosmeticDowngradeAnnotations.join('; ')}` : ''}${unverifiedSinceLastRun.length ? `\nUnverified since ${lastRun || 'last run'} (trust-cache branch, flag in stage-map Notes and the overall verdict line): ${unverifiedSinceLastRun.join(', ')}` : ''}${priorReportPath ? `\nPrior report: ${priorReportPath}${lastRun ? ` (as of ${lastRun})` : ''}` : ''}`,
  { agentType: 'status-lead', label: 'lead', phase: 'Synthesize', schema: LEAD_SCHEMA },
)
if (!lead) throw new Error('status-lead died or was skipped -- no status-report.md was written')

// ---- Return -----------------------------------------------------------------
// No filesystem access here -- status-report.md, every scratch file, and
// every fingerprint were written by the agent that owns them, via that
// agent's own Write/Bash tools. status-decisions.md / the run-log row are
// each written by the agent responsible for them (status-lead appends the
// run-log row itself via its script), not by this script.

return {
  scannedCount: scanned.length,
  diedCount,
  carriedForwardCount: skippedItems.length,
  recommendedNextAction: lead.recommendedNextAction,
  parallelizationOpportunity: lead.parallelizationOpportunity || null,
}
