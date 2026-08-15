export const meta = {
  name: 'decide',
  description: 'engineering-manager decide phase (shared by dispatch and triage): em-analyst -> conditional em-judge panel -> em-lead synthesis',
  whenToUse: 'Invoked by references/dispatch.md Step 1-2 (kind: "dispatch", only when the candidate set has 2+ items -- fewer is a QUALITY-gate stop before this ever runs) or references/triage.md Step 3-4 (kind: "triage", only when the NEEDS-INTAKE set has 2+ items -- exactly 1 skips the analyst entirely). Requires args {kind, targetDir, runId, candidates, standingConstraintsPath?, housekeepingGrouping?, existingEffortsNote?}.',
  phases: [
    { title: 'Analyze', detail: 'em-analyst reads the candidate set, proposes a grouping with a confidence rating' },
    { title: 'Judge panel', detail: '2-3 independent em-judge votes, only when confidence is not explicitly HIGH' },
    { title: 'Synthesize', detail: 'em-lead reconciles into dispatch-plan.md or triage-plan.md' },
  ],
}

const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})

const kind = ARGS.kind // 'dispatch' | 'triage'
const targetDir = ARGS.targetDir
const runId = ARGS.runId
const candidates = Array.isArray(ARGS.candidates) ? ARGS.candidates : []
const standingConstraintsPath = ARGS.standingConstraintsPath || null
const housekeepingGrouping = ARGS.housekeepingGrouping || null // triage only
const existingEffortsNote = ARGS.existingEffortsNote || null // dispatch only, from the effort-worktree registry

if (!kind || !targetDir || !runId || candidates.length < 2) {
  throw new Error('decide.js requires args: {kind: "dispatch"|"triage", targetDir, runId, candidates (2+)} -- the caller is responsible for the <2-candidate degenerate case, this script assumes it never happens')
}
if (kind !== 'dispatch' && kind !== 'triage') throw new Error(`decide.js: unknown kind ${JSON.stringify(kind)}`)

const planPath = `${targetDir}/.em-state/${runId}/${kind === 'dispatch' ? 'dispatch-plan.md' : 'triage-plan.md'}`
const validVotes = kind === 'dispatch' ? ['PARALLEL', 'SEQUENTIAL', 'SINGLE-SESSION'] : ['PARALLEL', 'SEQUENTIAL', 'BATCHED', 'SINGLE-SESSION']

const ANALYST_SCHEMA = {
  type: 'object',
  required: ['grouping', 'confidence'],
  properties: {
    grouping: {
      type: 'object',
      required: ['type', 'reason'],
      properties: {
        type: { type: 'string', enum: validVotes },
        groups: { type: 'array', items: { type: 'array', items: { type: 'string' } } },
        order: { type: 'array', items: { type: 'string' } },
        batches: { type: 'array', items: { type: 'object', properties: { items: { type: 'array', items: { type: 'string' } }, why: { type: 'string' } } } },
        reason: { type: 'string' },
      },
    },
    confidence: { type: 'string', enum: ['HIGH', 'LOW'] },
    ambiguity: { type: 'string', description: 'required when confidence is not HIGH -- the exact conflicting signal, for the judge panel' },
  },
}

const JUDGE_SCHEMA = {
  type: 'object',
  required: ['vote', 'reasoning', 'confidence'],
  properties: {
    vote: { type: 'string', enum: validVotes },
    groupingOrOrder: { type: 'string' },
    reasoning: { type: 'string' },
    confidence: { type: 'string', enum: ['HIGH', 'LOW'] },
  },
}

const LEAD_SCHEMA = {
  type: 'object',
  required: ['planWritten', 'decisionType'],
  properties: {
    planWritten: { type: 'boolean' },
    decisionType: { type: 'string', enum: validVotes },
    disagreementNoted: { type: 'boolean' },
    flaggedForHuman: { type: 'array', items: { type: 'string' }, description: 'items pulled out for direct human attention instead of auto-dispatch' },
  },
}

const candidateBlock = candidates.map(c => `- ${c.slug}: ${c.path}${c.note ? ` (${c.note})` : ''}`).join('\n')
const constraintsBlock = standingConstraintsPath ? `\n\nStanding constraints (established shared-DB/registry/ceiling facts, treat as fact -- does not compromise judge independence): ${standingConstraintsPath}` : ''
const effortsBlock = existingEffortsNote ? `\n\nExisting open efforts from this project's effort-worktree registry (check candidates against work already in flight, not just against each other): ${existingEffortsNote}` : ''
const housekeepingBlock = housekeepingGrouping ? `\n\nHousekeeping grouping already computed mechanically (Step 2, no analyst involvement) -- include as-is in the plan document: ${typeof housekeepingGrouping === 'string' ? housekeepingGrouping : JSON.stringify(housekeepingGrouping)}` : ''

// ---- Phase: Analyze -------------------------------------------------------

phase('Analyze')
const analyst = await agent(
  `${kind === 'dispatch'
    ? 'Determine whether these build-ready items can safely run at the same time in isolated worktrees, must run sequentially, or should stay single-session. Note: each candidate\'s QA coverage verdict matters -- BLIND is not ADEQUATE.'
    : 'Determine whether these not-yet-planned request items can go through team-intake concurrently, should batch into one request (name which items combine), must run sequentially (one intake should see another\'s conclusion first), or should stay single-session.'
  } Candidates:\n${candidateBlock}${constraintsBlock}${effortsBlock}`,
  { agentType: 'em-analyst', label: 'analyst', phase: 'Analyze', schema: ANALYST_SCHEMA },
)
if (!analyst) throw new Error('em-analyst died or was skipped -- nothing to synthesize')

// "Any confidence rating other than an explicit HIGH is treated as LOW" --
// an out-of-vocabulary rating must never silently skip the panel.
const panelNeeded = analyst.confidence !== 'HIGH'

// ---- Phase: Judge panel (conditional) --------------------------------------

let judgeVotes = []
if (panelNeeded) {
  phase('Judge panel')
  log(`analyst confidence: ${JSON.stringify(analyst.confidence)} -- convening a 3-judge panel`)
  const votes = await parallel(Array.from({ length: 3 }, (_, n) =>
    () => agent(
      `Independently vote on the same candidate set em-analyst saw. The analyst flagged this as ambiguous: ${analyst.ambiguity || '(no specific ambiguity given)'}. Candidates:\n${candidateBlock}${constraintsBlock}${effortsBlock}`,
      { agentType: 'em-judge', label: `judge:${n + 1}`, phase: 'Judge panel', schema: JUDGE_SCHEMA },
    ),
  ))
  judgeVotes = votes.filter(Boolean)
  if (judgeVotes.length < 2) log(`only ${judgeVotes.length}/3 judges returned -- em-lead will treat this as a low-confidence outcome`)
} else {
  log('analyst confidence HIGH -- skipping the judge panel')
}

// ---- Phase: Synthesize --------------------------------------------------------

phase('Synthesize')
const votesBlock = judgeVotes.length
  ? `\n\nJudge panel votes:\n${judgeVotes.map((v, i) => `- judge ${i + 1}: ${v.vote} (confidence ${v.confidence}) -- ${v.reasoning}`).join('\n')}`
  : ''
const lead = await agent(
  `Reconcile em-analyst's finding${judgeVotes.length ? ' and the judge panel' : ' (no panel ran -- analyst was HIGH confidence)'} into the final ${validVotes.join('/')} decision. Write ${planPath} and update the LATEST-${kind} pointer. This run's id is ${runId}. Dispatch prompts do NOT carry a mode token, in any mode -- team-build and team-intake both run fully autonomous and accept legacy tokens only as no-ops.${housekeepingBlock}\n\nAnalyst finding: ${analyst.grouping.type} -- ${analyst.grouping.reason}${votesBlock}`,
  { agentType: 'em-lead', label: 'lead', phase: 'Synthesize', schema: LEAD_SCHEMA },
)
if (!lead) throw new Error('em-lead died or was skipped -- no plan was written')

// ---- Return -----------------------------------------------------------------
// No filesystem access here -- dispatch-plan.md / triage-plan.md and the
// LATEST-* pointer were written by em-lead itself, via its own Write tool,
// exactly as before this conversion.

return {
  kind,
  planPath,
  analystConfidence: analyst.confidence,
  panelRan: panelNeeded,
  judgeVoteCount: judgeVotes.length,
  decisionType: lead.decisionType,
  disagreementNoted: !!lead.disagreementNoted,
  flaggedForHuman: lead.flaggedForHuman || [],
}
