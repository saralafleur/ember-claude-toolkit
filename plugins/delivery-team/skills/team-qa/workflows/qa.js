export const meta = {
  name: 'qa',
  description: 'team-qa pipeline: change-intake gate -> staged two-wave evaluation fan-out (or director-routed) -> strategist -> lead',
  whenToUse: 'Invoked by team-qa SKILL.md Step 1, once scope and output paths are resolved. Requires args {changeBriefPath, supportingDir, scope, mode}.',
  phases: [
    { title: 'Change-intake', detail: 'gate -- a BLOCKED verdict here ends the run, everything else is autonomous' },
    { title: 'Direct-mode routing', detail: 'director-of-engineering trims the roster, only in direct mode' },
    { title: 'Evaluate wave 1', detail: 'coverage cartographer + risk analyst, in parallel' },
    { title: 'Evaluate wave 2', detail: 'unit + e2e architects, in parallel, fed wave 1\'s named traps' },
    { title: 'Strategist', detail: 'coverage verdict + test-debt diagnosis + memory' },
    { title: 'Lead', detail: 'synthesize into the buildable test plan' },
  ],
}

const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})

const changeBriefPath = ARGS.changeBriefPath
const supportingDir = ARGS.supportingDir
const scope = ARGS.scope || ''
const mode = ARGS.mode || 'standard' // 'standard' | 'direct'

if (!changeBriefPath || !supportingDir) {
  throw new Error('qa.js requires args: {changeBriefPath, supportingDir, scope?, mode?}')
}

const isDirect = mode === 'direct'

// ---- schemas ------------------------------------------------------------

const TRIAGE_SCHEMA = {
  type: 'object',
  required: ['verdict'],
  properties: {
    verdict: { type: 'string', enum: ['READY', 'BLOCKED'] },
    blockedReason: { type: 'string' },
    changeBriefWritten: { type: 'boolean' },
    catalogDigest: {
      type: 'object',
      description: 'optional -- the run-local defect-catalog digest, per substrate-core/references/catalog-digest.md. Omit entirely if the project has no catalog configured.',
      properties: {
        configured: { type: 'boolean' },
        rows: { type: 'string', description: 'the pre-rendered digest block (STATE B or STATE C text)' },
        surfacesResolved: { type: 'array', items: { type: 'string' } },
        surfacesUnresolved: { type: 'array', items: { type: 'string' } },
        artifactPath: { type: 'string' },
      },
    },
  },
}

const DIRECTOR_SCHEMA = {
  type: 'object',
  required: ['runPlan'],
  properties: {
    runPlan: {
      type: 'array',
      items: {
        type: 'object',
        required: ['agent', 'run', 'reason'],
        properties: {
          agent: { type: 'string', enum: ['qa-coverage-cartographer', 'qa-risk-analyst', 'qa-unit-architect', 'qa-e2e-architect', 'qa-strategist', 'qa-lead'] },
          run: { type: 'boolean' },
          reason: { type: 'string' },
        },
      },
    },
  },
}

const COVERAGE_SCHEMA = {
  type: 'object',
  required: ['findingsWritten'],
  properties: {
    findingsWritten: { type: 'boolean' },
    baseline: { type: 'object', properties: { green: { type: 'integer' }, red: { type: 'integer' }, total: { type: 'integer' } } },
    gaps: { type: 'array', items: { type: 'string' } },
  },
}

const RISK_SCHEMA = {
  type: 'object',
  required: ['findingsWritten'],
  properties: {
    findingsWritten: { type: 'boolean' },
    invariantsAtRisk: { type: 'array', items: { type: 'string' } },
    traps: {
      type: 'array',
      items: { type: 'object', required: ['id', 'description'], properties: { id: { type: 'string' }, description: { type: 'string' } } },
    },
    defectCatalogMatches: { type: 'array', items: { type: 'string' } },
  },
}

const UNIT_SCHEMA = {
  type: 'object',
  required: ['findingsWritten'],
  properties: {
    findingsWritten: { type: 'boolean' },
    tests: { type: 'array', items: { type: 'object', properties: { spec: { type: 'string' }, testCase: { type: 'string' }, trapId: { type: 'string' } } } },
  },
}

const E2E_SCHEMA = {
  type: 'object',
  required: ['findingsWritten'],
  properties: {
    findingsWritten: { type: 'boolean' },
    tests: { type: 'array', items: { type: 'object', properties: { spec: { type: 'string' }, bucket: { type: 'string' }, runCommand: { type: 'string' }, trapId: { type: 'string' } } } },
  },
}

const STRATEGIST_SCHEMA = {
  type: 'object',
  required: ['verdict', 'assessmentWritten'],
  properties: {
    verdict: { type: 'string', enum: ['ADEQUATE', 'GAPPED', 'BLIND'] },
    assessmentWritten: { type: 'boolean' },
    testDebtDiagnosis: { type: 'string' },
    matchedRecurringGap: { type: 'string' },
  },
}

const LEAD_SCHEMA = {
  type: 'object',
  required: ['testPlanWritten'],
  properties: {
    testPlanWritten: { type: 'boolean' },
    summary: { type: 'string' },
  },
}

// ---- Phase: Change-intake (gate) -----------------------------------------

phase('Change-intake')
const triage = await agent(
  `Ingest the change scope (${scope}) into a change brief at ${changeBriefPath} -- name the surfaces touched and the test-invariants at risk. If this project has a defect catalog configured, resolve and run the digest per substrate-core/references/catalog-digest.md and return it as catalogDigest.`,
  { agentType: 'qa-triage', label: 'triage', phase: 'Change-intake', schema: TRIAGE_SCHEMA },
)
if (!triage) throw new Error('qa-triage died or was skipped')

if (triage.verdict === 'BLOCKED') {
  log(`BLOCKED: ${triage.blockedReason || '(no reason given)'} -- this is the one case team-qa terminates early; no evaluation runs`)
  return { blocked: true, reason: triage.blockedReason || null }
}

// ---- Phase: Direct-mode routing -------------------------------------------

const ROSTER = ['qa-coverage-cartographer', 'qa-risk-analyst', 'qa-unit-architect', 'qa-e2e-architect', 'qa-strategist', 'qa-lead']
let runSet = new Set(ROSTER)
if (isDirect) {
  phase('Direct-mode routing')
  const director = await agent(
    `This skill's roster (beyond triage, which already ran) is: qa-coverage-cartographer, qa-risk-analyst, qa-unit-architect, qa-e2e-architect, qa-strategist, qa-lead. Given the change brief at ${changeBriefPath}, decide which are warranted for THIS piece of work.`,
    { agentType: 'director-of-engineering', label: 'director', phase: 'Direct-mode routing', schema: DIRECTOR_SCHEMA },
  )
  if (director && Array.isArray(director.runPlan)) {
    runSet = new Set(director.runPlan.filter(r => r.run).map(r => r.agent))
    log(`direct mode: running ${[...runSet].join(', ') || '(none)'}`)
  } else {
    log('director-of-engineering died or returned nothing -- falling back to the full standard roster')
  }
}

// ---- Phase: Evaluate wave 1 (coverage + risk, parallel) -------------------

phase('Evaluate wave 1')
// Additive, locator-only -- see substrate-core/references/catalog-digest.md.
// Absent/not-configured produces '', never a new checker role.
const catalogDigestBlock = (triage.catalogDigest && triage.catalogDigest.configured)
  ? `\n\n${triage.catalogDigest.rows || `Defect-catalog digest for this run: CONFIGURED, 0 of ${(triage.catalogDigest.surfacesUnresolved || []).length} surface(s) resolved. Unresolved: ${(triage.catalogDigest.surfacesUnresolved || []).join(', ') || 'none'}. Artifact: ${triage.catalogDigest.artifactPath || 'n/a'}. Treat this as UNKNOWN, not as "no known trap applies".`}`
  : ''
const wave1 = {}
await parallel([
  runSet.has('qa-coverage-cartographer') ? () => agent(
    `Map EXISTING test coverage for the surfaces touched by the change at ${changeBriefPath}, across every layer this project tests at. Run the relevant suites and record the current green/red baseline. Write ${supportingDir}/coverage.md.${catalogDigestBlock}`,
    { agentType: 'qa-coverage-cartographer', label: 'coverage', phase: 'Evaluate wave 1', schema: COVERAGE_SCHEMA },
  ).then(r => { wave1.coverage = r }) : () => Promise.resolve(),
  runSet.has('qa-risk-analyst') ? () => agent(
    `Evaluate blast radius and name "ships-green-but-broken" traps (each with a stable id) for the change at ${changeBriefPath}. Write ${supportingDir}/risk.md.${catalogDigestBlock}`,
    { agentType: 'qa-risk-analyst', label: 'risk', phase: 'Evaluate wave 1', schema: RISK_SCHEMA },
  ).then(r => { wave1.risk = r }) : () => Promise.resolve(),
])

// ---- Phase: Evaluate wave 2 (unit + e2e, fed wave 1's named traps) --------

phase('Evaluate wave 2')
const trapsBlock = wave1.risk && Array.isArray(wave1.risk.traps) && wave1.risk.traps.length
  ? `\n\nNamed traps from risk.md (design tests against these, cite the trap id):\n${wave1.risk.traps.map(t => `- ${t.id}: ${t.description}`).join('\n')}`
  : ''
const wave2 = {}
await parallel([
  runSet.has('qa-unit-architect') ? () => agent(
    `Design unit/parity/component tests for the change at ${changeBriefPath}.${trapsBlock} Write ${supportingDir}/unit-tests.md.${catalogDigestBlock}`,
    { agentType: 'qa-unit-architect', label: 'unit', phase: 'Evaluate wave 2', schema: UNIT_SCHEMA },
  ).then(r => { wave2.unit = r }) : () => Promise.resolve(),
  runSet.has('qa-e2e-architect') ? () => agent(
    `Design e2e/API tests for the change at ${changeBriefPath}.${trapsBlock} Write ${supportingDir}/e2e-tests.md.${catalogDigestBlock}`,
    { agentType: 'qa-e2e-architect', label: 'e2e', phase: 'Evaluate wave 2', schema: E2E_SCHEMA },
  ).then(r => { wave2.e2e = r }) : () => Promise.resolve(),
])

// ---- Phase: Strategist ------------------------------------------------------

let strategist = null
if (runSet.has('qa-strategist')) {
  phase('Strategist')
  strategist = await agent(
    `Set the coverage verdict, diagnose test-debt, and write qa-assessment.md for the change at ${changeBriefPath}, using whichever of the four supporting findings ran, plus this project's recurring-issue memory if configured.${catalogDigestBlock}`,
    { agentType: 'qa-strategist', label: 'strategist', phase: 'Strategist', schema: STRATEGIST_SCHEMA },
  )
}

// ---- Phase: Lead ---------------------------------------------------------------

let lead = null
if (runSet.has('qa-lead')) {
  phase('Lead')
  lead = await agent(
    `Synthesize the supporting findings and the strategist's verdict${strategist ? ` (${strategist.verdict})` : ' (none -- qa-strategist did not run this pass)'} into a buildable test-plan.md for the change at ${changeBriefPath}.${catalogDigestBlock}`,
    { agentType: 'qa-lead', label: 'lead', phase: 'Lead', schema: LEAD_SCHEMA },
  )
}

// ---- Return -----------------------------------------------------------------
// No filesystem access here -- every artifact (change-brief.md,
// supporting/*.md, qa-assessment.md, test-plan.md) was written by the agent
// that owns it, via that agent's own Write tool. decisions.md is the
// orchestrator's job after this workflow returns, same as team-intake.

return {
  blocked: false,
  mode,
  ranAgents: [...runSet],
  skippedAgents: ROSTER.filter(a => !runSet.has(a)),
  coverageVerdict: strategist ? strategist.verdict : null,
  matchedRecurringGap: (strategist && strategist.matchedRecurringGap) || null,
  leadSummary: lead ? lead.summary : null,
}
