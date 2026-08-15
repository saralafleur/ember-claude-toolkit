export const meta = {
  name: 'build',
  description: 'team-build Steps 1-7: triage -> plan -> red -> implement/verify/review loop (bounded) -> lead synthesis. Step 0/0.5 (resolve plans, version bump) and Step 8 (ship: commit+push) stay outside, in the calling SKILL.md -- Workflow scripts have no filesystem/git access of their own, and Step 8 was always an orchestrator action, not an agent one.',
  whenToUse: 'Invoked by team-build SKILL.md Step 1, once Step 0/0.5 have resolved the intake dir, both plan paths, and (if configured) the version-bump decision. Requires args {intakeDir, technicalPlanPath, testPlanPath, buildDir}.',
  phases: [
    { title: 'Triage', detail: 'confirm plans, discover repo layout, provision per-effort worktrees + Docker stack, gate on a clean tree (auto-stash), record starting commits' },
    { title: 'Plan', detail: 'ordered dependency-correct task list; MANDATORY durable-cure steps marked' },
    { title: 'Red', detail: 'author tests from test-plan.md, prove each RED' },
    { title: 'Implement + Verify + Review', detail: 'bounded loop: implement to green, verify, adversarial review; a verify failure or a real review defect re-enters the loop' },
    { title: 'Ship', detail: 'build-lead writes build-report.md -- the actual git commit/push happens outside this workflow, in the calling SKILL.md' },
  ],
}

const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})

const intakeDir = ARGS.intakeDir
const technicalPlanPath = ARGS.technicalPlanPath
const testPlanPath = ARGS.testPlanPath
const buildDir = ARGS.buildDir // <intake-dir>/build/<date>-<slug>/

if (!intakeDir || !technicalPlanPath || !testPlanPath || !buildDir) {
  throw new Error('build.js requires args: {intakeDir, technicalPlanPath, testPlanPath, buildDir}')
}

// This whole build loop is bounded at MAX_CYCLES total implement attempts,
// combined across both trigger sources (a verify failure, or a real defect
// build-reviewer found after a green verify) -- the skill's own docs specify
// "~3 fix attempts" for the verify-failure case and leave the review-driven
// case unbounded in prose (a human would just notice non-convergence); a
// script needs an explicit bound either way, so this treats both as draws
// against the same 3-attempt budget rather than inventing a second implicit
// unbounded loop. Flagged here deliberately -- worth the user's eyes if a real
// build ever needs more than 3 rounds to converge.
const MAX_CYCLES = 3

const TRIAGE_SCHEMA = {
  type: 'object',
  required: ['verdict'],
  properties: {
    verdict: { type: 'string', enum: ['READY', 'BLOCKED'] },
    reason: { type: 'string', description: 'required when BLOCKED -- only a missing/incomplete plan should still be BLOCKED here; a dirty tree is auto-stashed and reported READY' },
    briefWritten: { type: 'boolean' },
    worktrees: {
      type: 'array',
      items: { type: 'object', properties: { repo: { type: 'string' }, path: { type: 'string' }, branch: { type: 'string' }, startingCommit: { type: 'string' } } },
    },
    autoStashedRepos: { type: 'array', items: { type: 'string' }, description: 'repos where a dirty tree was auto-stashed (git stash -u) before provisioning proceeded' },
  },
}

const PLAN_SCHEMA = {
  type: 'object',
  required: ['taskListWritten'],
  properties: {
    taskListWritten: { type: 'boolean' },
    taskCount: { type: 'integer' },
    mandatoryCureSteps: { type: 'array', items: { type: 'string' } },
  },
}

const TESTAUTHOR_SCHEMA = {
  type: 'object',
  required: ['testsWritten', 'allRed'],
  properties: {
    testsWritten: { type: 'boolean' },
    allRed: { type: 'boolean' },
    alreadyGreenTests: { type: 'array', items: { type: 'string' }, description: 'non-empty only when allRed is false -- a test that should be red but already passes; this is a terminal stop, not something to loop on' },
  },
}

const IMPLEMENTER_SCHEMA = {
  type: 'object',
  required: ['implemented'],
  properties: {
    implemented: { type: 'boolean' },
    summary: { type: 'string' },
    mandatoryCuresApplied: { type: 'array', items: { type: 'string' } },
  },
}

const VERIFIER_SCHEMA = {
  type: 'object',
  required: ['status'],
  properties: {
    status: { type: 'string', enum: ['GREEN', 'RED', 'DOD_FAIL'] },
    failingTests: { type: 'array', items: { type: 'string' } },
    dodStatus: { type: 'string' },
    evidence: { type: 'string' },
  },
}

const REVIEWER_SCHEMA = {
  type: 'object',
  required: ['realDefect'],
  properties: {
    realDefect: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
  },
}

const LEAD_SCHEMA = {
  type: 'object',
  required: ['reportWritten', 'verdict'],
  properties: {
    reportWritten: { type: 'boolean' },
    verdict: { type: 'string', enum: ['GREEN', 'GREEN-WITH-CAVEATS'] },
    headline: { type: 'string' },
    reportPath: { type: 'string' },
  },
}

// ---- Phase: Triage ---------------------------------------------------------

phase('Triage')
const triage = await agent(
  `Confirm ${technicalPlanPath} and ${testPlanPath} are present and buildable, discover this project's repo layout, provision a per-effort worktree set (+ namespaced Docker stack, if this project has one), confirm each worktree is clean (auto-stash any dirty tree with 'git stash -u', never ask), record the starting commit per repo, and write build-brief.md under ${buildDir}.`,
  { agentType: 'build-triage', label: 'triage', phase: 'Triage', schema: TRIAGE_SCHEMA },
)
if (!triage) throw new Error('build-triage died or was skipped')
if (triage.verdict === 'BLOCKED') {
  log(`BLOCKED at triage: ${triage.reason || '(no reason given)'} -- this is a terminal outcome, not a loop`)
  return { status: 'BLOCKED', step: 'triage', reason: triage.reason || null }
}

// Every prompt from here on repeats the concrete worktree path(s) and
// buildDir explicitly -- earlier draft of this script said only "in this
// effort's worktree" and left agents to infer the actual path, which is
// exactly the kind of ambiguity that broke in testing (a later-cycle
// build-verifier call ended up investigating an unrelated repo instead of
// this effort's worktree). Never rely on an agent re-deriving a path that's
// already known and cheap to state.
const worktreesBlock = (triage.worktrees || []).length
  ? `\n\nThis effort's worktree(s) -- work ONLY inside these, never any other checkout:\n${(triage.worktrees || []).map(w => `- ${w.repo}: ${w.path} (branch ${w.branch}, starting commit ${w.startingCommit})`).join('\n')}`
  : `\n\n(build-triage returned no worktree list -- if you cannot find this effort's own isolated worktree from build-brief.md under ${buildDir}, stop and report BLOCKED rather than guessing at a repo.)`
const buildDirBlock = `\n\nBuild artifacts directory: ${buildDir}`

// ---- Phase: Plan -----------------------------------------------------------

phase('Plan')
const plan = await agent(
  `Turn ${technicalPlanPath} + ${testPlanPath} + build-brief.md into one ordered, dependency-correct build-task-list.md under ${buildDir}. Mark every durable-cure step this project's defect catalog (if configured) calls for as MANDATORY, citing the catalog id.${worktreesBlock}${buildDirBlock}`,
  { agentType: 'build-planner', label: 'planner', phase: 'Plan', schema: PLAN_SCHEMA },
)
if (!plan) throw new Error('build-planner died or was skipped')

// ---- Phase: Red -------------------------------------------------------------

phase('Red')
const red = await agent(
  `Write the tests named in ${testPlanPath}, run them, and prove each one RED against the current unbuilt code. Test files only -- no product code.${worktreesBlock}${buildDirBlock}`,
  { agentType: 'build-test-author', label: 'test-author', phase: 'Red', schema: TESTAUTHOR_SCHEMA },
)
if (!red) throw new Error('build-test-author died or was skipped')
if (!red.allRed) {
  log(`BLOCKED at red: test(s) already green before implementation -- ${(red.alreadyGreenTests || []).join(', ')}`)
  return { status: 'BLOCKED', step: 'red', reason: 'test already green before implementation', alreadyGreenTests: red.alreadyGreenTests || [] }
}

// ---- Phase: Implement + Verify + Review (bounded loop) ----------------------

let verify = null
let review = null
let priorFindingsBlock = ''
let cycle = 0
while (cycle < MAX_CYCLES) {
  cycle += 1
  phase('Implement + Verify + Review')

  await agent(
    `Work build-task-list.md in order, applying the change set from ${technicalPlanPath} to make the red tests pass (cycle ${cycle} of up to ${MAX_CYCLES}). Apply any structural cure the plan marked MANDATORY -- no inline shortcut. One implementer, sequential, no parallel edits.${priorFindingsBlock}${worktreesBlock}${buildDirBlock}`,
    { agentType: 'build-implementer', label: `implementer:${cycle}`, phase: 'Implement + Verify + Review', schema: IMPLEMENTER_SCHEMA },
  )

  verify = await agent(
    `Bring up this effort's own isolated Docker stack (if this project has one and scope needs it), run the full relevant suites, confirm each new test went red-to-green, and run the Definition of Done plus any standing guards this project's defect catalog calls for.${worktreesBlock}${buildDirBlock}`,
    { agentType: 'build-verifier', label: `verifier:${cycle}`, phase: 'Implement + Verify + Review', schema: VERIFIER_SCHEMA },
  )
  if (!verify || verify.status !== 'GREEN') {
    const failReason = verify
      ? `verify came back ${verify.status}${verify.failingTests && verify.failingTests.length ? ` -- failing: ${verify.failingTests.join(', ')}` : ''}${verify.dodStatus ? ` (DoD: ${verify.dodStatus})` : ''}`
      : 'the verifier agent died or produced no result (e.g. a transient infrastructure error) -- treat as not-yet-green and retry'
    log(`cycle ${cycle}: ${failReason} -- ${cycle < MAX_CYCLES ? 're-entering implement' : 'out of attempts'}`)
    priorFindingsBlock = `\n\nA prior verify pass this run failed -- fix this specifically, don't just re-run the same change: ${failReason}`
    review = null
    continue
  }

  review = await agent(
    `Review the diff since the starting commit, per touched repo, against this project's known traps (if it has a defect catalog configured) plus ordinary correctness/simplification.${worktreesBlock}${buildDirBlock}`,
    { agentType: 'build-reviewer', label: `reviewer:${cycle}`, phase: 'Implement + Verify + Review', schema: REVIEWER_SCHEMA },
  )
  if (!review) throw new Error(`build-reviewer died or was skipped on cycle ${cycle}`)
  if (!review.realDefect) break // converged: green verify, clean review

  const findingsList = (review.findings || []).join('\n- ')
  log(`cycle ${cycle}: build-reviewer found a real defect -- ${cycle < MAX_CYCLES ? 're-entering implement' : 'out of attempts'}: ${findingsList}`)
  priorFindingsBlock = `\n\nA prior review pass this run found real defect(s) still unresolved -- fix these specifically, don't just re-run the same change; if a finding recurs across cycles, that means the previous attempt didn't actually address it:\n- ${findingsList}`
}

if (!verify || verify.status !== 'GREEN') {
  return { status: 'BLOCKED', step: 'verify', reason: `non-converging fix loop after ${MAX_CYCLES} cycles`, lastVerify: verify, cycles: cycle }
}
if (review && review.realDefect) {
  return { status: 'BLOCKED', step: 'review', reason: `reviewer kept finding real defects after ${MAX_CYCLES} cycles`, findings: review.findings || [], cycles: cycle }
}

// ---- Phase: Ship (lead synthesis only -- the actual commit/push happens
// outside this workflow, in the calling SKILL.md; scripts have no
// filesystem/git access of their own) --------------------------------------

phase('Ship')
const lead = await agent(
  `Write build-report.md under ${buildDir}, update the build run-log, and -- if this build had to re-apply a known cure, took or was tempted to take a shortcut, or exposed a new repeatable build trap, and this project has a defect catalog configured -- update it.${worktreesBlock}${buildDirBlock}`,
  { agentType: 'build-lead', label: 'lead', phase: 'Ship', schema: LEAD_SCHEMA },
)
if (!lead) throw new Error('build-lead died or was skipped')

// ---- Return -----------------------------------------------------------------
// No filesystem/git access here -- every artifact (build-brief.md,
// build-task-list.md, the test files, the product-code diff,
// build-report.md) was written by the agent that owns it, via that agent's
// own Write/Edit/Bash tools. The commit + push in Step 8 is the calling
// SKILL.md's job, exactly as before this conversion -- it was never an
// agent action to begin with.

return {
  status: lead.verdict, // 'GREEN' | 'GREEN-WITH-CAVEATS'
  cycles: cycle,
  worktrees: triage.worktrees || [],
  autoStashedRepos: triage.autoStashedRepos || [],
  reportPath: lead.reportPath || `${buildDir}/build-report.md`,
  headline: lead.headline || null,
}
