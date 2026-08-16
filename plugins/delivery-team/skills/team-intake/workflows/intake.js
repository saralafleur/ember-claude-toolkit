export const meta = {
  name: 'intake',
  description: 'team-intake pipeline: triage -> (direct-mode director branch | 4-agent evaluation fan-out) -> PM -> tech-lead',
  whenToUse: 'Invoked by team-intake SKILL.md Step 2, after Step 1 has scaffolded the intake folder, run the re-entry check, and run the PARKED re-trigger scan. Requires args {intakeDir, briefPath, supportingDir, mode, watchNotes?}.',
  phases: [
    { title: 'Triage', detail: 'ingest the request into a brief; a BLOCKED verdict adopts assumptions instead of stopping' },
    { title: 'Direct-mode routing', detail: 'director-of-engineering trims the roster, only in direct/fast mode' },
    { title: 'Evaluate', detail: 'product-owner, architect, engineer, QA in parallel' },
    { title: 'Project Manager', detail: 'classify, reconstruct history, PM plan -- never skipped' },
    { title: 'Tech Lead', detail: 'synthesize into the technical plan' },
  ],
}

const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})

const intakeDir = ARGS.intakeDir
const briefPath = ARGS.briefPath
const supportingDir = ARGS.supportingDir
const mode = ARGS.mode || 'standard' // 'standard' | 'direct' | 'fast'
const watchNotes = Array.isArray(ARGS.watchNotes) ? ARGS.watchNotes : []

if (!intakeDir || !briefPath || !supportingDir) {
  throw new Error('intake.js requires args: {intakeDir, briefPath, supportingDir, mode?, watchNotes?}')
}

const isDirect = mode === 'direct' || mode === 'fast'
const isFast = mode === 'fast'

const watchBlock = watchNotes.length
  ? `\n\nPARKED decisions flagged by the orchestrator's re-trigger scan as live context for this request (treat as background, not instructions):\n${watchNotes.map(n => `- ${n}`).join('\n')}`
  : ''

// ---- schemas ----------------------------------------------------------

const TRIAGE_SCHEMA = {
  type: 'object',
  required: ['verdict', 'briefWritten'],
  properties: {
    verdict: { type: 'string', enum: ['READY', 'BLOCKED'] },
    briefWritten: { type: 'boolean', description: 'true once request-brief.md has been written to briefPath, including the Scout digest' },
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
    blockingQuestions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['question', 'suggestedAssumption'],
        properties: {
          question: { type: 'string' },
          context: { type: 'string' },
          options: { type: 'array', items: { type: 'string' } },
          suggestedAssumption: { type: 'string', description: 'the best-supported guess from the request materials, project record, or decision-log -- this skill never stops on BLOCKED, it adopts this instead' },
        },
      },
    },
    nonBlockingAssumptions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['question', 'suggestedAssumption'],
        properties: { question: { type: 'string' }, suggestedAssumption: { type: 'string' } },
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
          agent: { type: 'string', enum: ['intake-product-owner', 'intake-architect', 'intake-engineer', 'intake-qa', 'intake-tech-lead'] },
          run: { type: 'boolean' },
          reason: { type: 'string' },
        },
      },
    },
  },
}

const EVAL_SCHEMA = {
  type: 'object',
  required: ['findingsWritten', 'summary'],
  properties: {
    findingsWritten: { type: 'boolean', description: 'true once this agent has written its own supporting/*.md file' },
    summary: { type: 'string', description: '2-4 sentence headline for the PM and tech-lead to build on' },
    keyPoints: { type: 'array', items: { type: 'string' } },
    risksOrConcerns: { type: 'array', items: { type: 'string' } },
  },
}

const PM_SCHEMA = {
  type: 'object',
  required: ['requestType', 'isRepeat', 'pmPlanWritten'],
  properties: {
    requestType: { type: 'string' },
    isRepeat: { type: 'boolean' },
    matchedDefectId: { type: 'string' },
    pmPlanWritten: { type: 'boolean' },
    decisionRows: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'status'],
        properties: { title: { type: 'string' }, status: { type: 'string' }, note: { type: 'string' } },
      },
    },
  },
}

const TECHLEAD_SCHEMA = {
  type: 'object',
  required: ['technicalPlanWritten', 'summary'],
  properties: {
    technicalPlanWritten: { type: 'boolean' },
    summary: { type: 'string' },
    decisionRows: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'status'],
        properties: { title: { type: 'string' }, status: { type: 'string' }, note: { type: 'string' } },
      },
    },
  },
}

// ---- Phase: Triage -------------------------------------------------------

phase('Triage')
const triage = await agent(
  `Ingest the request materials under ${intakeDir} into a normalized request brief. Write it to ${briefPath}, including a Scout digest (stack, layout, test commands, candidate files, relevant defect-catalog entries) so downstream evaluators don't re-derive it. If this project has a defect catalog configured, resolve and run the digest per substrate-core/references/catalog-digest.md and return it as catalogDigest.${watchBlock}`,
  { agentType: 'intake-triage', label: 'triage', phase: 'Triage', schema: TRIAGE_SCHEMA },
)
if (!triage) throw new Error('intake-triage died or was skipped -- cannot proceed without a brief')

// BLOCKED never stops this skill -- adopt the best-supported assumption per
// question and keep going. The orchestrator writes the resulting
// decisions.md rows after this workflow returns (this script has no
// filesystem access of its own).
const adoptedAssumptions = []
if (triage.verdict === 'BLOCKED') {
  for (const q of triage.blockingQuestions || []) {
    adoptedAssumptions.push({ question: q.question, context: q.context || '', options: q.options || [], adopted: q.suggestedAssumption, blocking: true })
  }
  log(`triage BLOCKED -- proceeding on ${adoptedAssumptions.length} adopted assumption(s), to be logged by the orchestrator`)
}
for (const q of triage.nonBlockingAssumptions || []) {
  adoptedAssumptions.push({ question: q.question, adopted: q.suggestedAssumption, blocking: false })
}

const assumptionsBlock = adoptedAssumptions.length
  ? `\n\nAssumptions adopted in lieu of an answer (treat as settled context for this run):\n${adoptedAssumptions.map(a => `- ${a.question} -> ${a.adopted}`).join('\n')}`
  : ''

// Additive, locator-only -- see substrate-core/references/catalog-digest.md.
// Absent/not-configured produces '', never a new checker role or a second
// producer of this artifact (Override 1 in the technical plan).
const catalogDigestBlock = (triage.catalogDigest && triage.catalogDigest.configured)
  ? `\n\n${triage.catalogDigest.rows || `Defect-catalog digest for this run: CONFIGURED, 0 of ${(triage.catalogDigest.surfacesUnresolved || []).length} surface(s) resolved. Unresolved: ${(triage.catalogDigest.surfacesUnresolved || []).join(', ') || 'none'}. Artifact: ${triage.catalogDigest.artifactPath || 'n/a'}. Treat this as UNKNOWN, not as "no known trap applies".`}`
  : ''

// ---- Phase: Direct-mode routing (director-of-engineering) ---------------

const ROSTER = ['intake-product-owner', 'intake-architect', 'intake-engineer', 'intake-qa', 'intake-tech-lead']
let runSet = new Set(ROSTER)

if (isDirect) {
  phase('Direct-mode routing')
  const director = await agent(
    `This skill's roster is: intake-product-owner, intake-architect, intake-engineer, intake-qa, intake-tech-lead. Given the actual request at ${briefPath}, decide which are warranted for THIS piece of work and which can be skipped. intake-project-manager is never optional and is not part of this decision.${isFast ? ' This run is FAST: default toward skipping unless an agent is load-bearing for direction (product-owner/architect/tech-lead lean kept, intake-qa leans skipped) -- unless a defect-catalog match forces the QA guardrail back on.' : ''}`,
    { agentType: 'director-of-engineering', label: 'director', phase: 'Direct-mode routing', schema: DIRECTOR_SCHEMA },
  )
  if (director && Array.isArray(director.runPlan)) {
    runSet = new Set(director.runPlan.filter(r => r.run).map(r => r.agent))
    runSet.add('intake-project-manager') // never skippable, never the director's call
    log(`direct mode: running ${[...runSet].join(', ')}`)
  } else {
    log('director-of-engineering died or returned nothing -- falling back to the full standard roster')
  }
}

// ---- Phase: Evaluate (parallel fan-out over whatever runSet contains) ----

phase('Evaluate')
const EVALUATORS = [
  { agentType: 'intake-product-owner', file: 'product-owner.md', brief: 'Evaluate value/scope/stakeholder fit: is it in scope, does it align with requirements, user-facing acceptance and priority.' },
  { agentType: 'intake-architect', file: 'architect.md', brief: 'Evaluate system/design impact: subsystems and boundaries affected, architectural options and trade-offs, risks.' },
  { agentType: 'intake-engineer', file: 'engineer.md', brief: 'Evaluate code-level reality: exact files/functions to change, feasibility, effort, dependencies, gotchas.' },
  { agentType: 'intake-qa', file: 'qa.md', brief: 'Define how we prove this is done and protected: acceptance verification steps, regression tests to add/update, manual check.' },
].filter(e => runSet.has(e.agentType))

const evalResults = await parallel(EVALUATORS.map(e => () =>
  agent(
    `${e.brief} Start from the brief's Scout digest at ${briefPath} instead of re-deriving stack/layout/test-command facts -- your judgment stays independent, the discovery is paid once by triage. Write your findings to ${supportingDir}/${e.file}.${assumptionsBlock}${catalogDigestBlock}`,
    { agentType: e.agentType, label: e.agentType, phase: 'Evaluate', schema: EVAL_SCHEMA },
  ).then(r => ({ agentType: e.agentType, result: r })),
))

// ---- Phase: Project Manager (never skipped) ------------------------------

phase('Project Manager')
const supportingSummaries = evalResults.filter(r => r.result).map(r => `${r.agentType}: ${r.result.summary}`).join('\n')
const pm = await agent(
  `Classify this request's true type, reconstruct history (have we seen this before?) using PM memory, and write pm-plan.md. Brief: ${briefPath}. Supporting findings summaries:\n${supportingSummaries || '(none ran -- direct mode skipped the whole evaluation fan-out)'}${assumptionsBlock}${catalogDigestBlock}`,
  { agentType: 'intake-project-manager', label: 'pm', phase: 'Project Manager', schema: PM_SCHEMA },
)
if (!pm) throw new Error('intake-project-manager died or was skipped -- this role is never optional')

// ---- Phase: Tech Lead ------------------------------------------------------

let techLead = null
if (runSet.has('intake-tech-lead')) {
  phase('Tech Lead')
  techLead = await agent(
    `Merge the architect/engineer/QA findings (whichever ran) into technical-plan.md, using the PM's request type (${pm.requestType}) as context. Brief: ${briefPath}. Supporting findings:\n${supportingSummaries || '(none ran)'}${catalogDigestBlock}`,
    { agentType: 'intake-tech-lead', label: 'tech-lead', phase: 'Tech Lead', schema: TECHLEAD_SCHEMA },
  )
}

// ---- Return -----------------------------------------------------------------
// Nothing here touches the filesystem -- every artifact (request-brief.md,
// supporting/*.md, pm-plan.md, technical-plan.md) was written by the agent
// that owns it, via that agent's own Write tool, exactly as before this
// conversion. decisions.md is deliberately NOT written here either -- the
// orchestrator appends every row below via add_decision.py +
// append_intake_decision_row.py after this workflow returns, same
// separation of duties the skill already documented (tech-lead "deliberately
// cannot write that file itself").

return {
  mode,
  triageVerdict: triage.verdict,
  adoptedAssumptions,
  ranAgents: [...runSet],
  skippedAgents: ROSTER.filter(a => !runSet.has(a)),
  pm: {
    requestType: pm.requestType,
    isRepeat: pm.isRepeat,
    matchedDefectId: pm.matchedDefectId || null,
  },
  techLead: techLead ? { summary: techLead.summary } : null,
  decisionRowsToRecord: [
    ...adoptedAssumptions.map(a => ({
      title: a.question,
      status: 'DECIDED-AUTO',
      note: `assumption adopted in lieu of an answer: ${a.adopted}`,
    })),
    ...(pm.decisionRows || []),
    ...((techLead && techLead.decisionRows) || []),
  ],
}
