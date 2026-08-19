# ember-foundation-substrate-toolkit

⚠️ **Experimental.** These skills are actively evolving — expect rough edges,
and report issues if something breaks.

Three chained virtual teams that take a product idea from question to plan.
Each is a pipeline of specialist subagents with an adversarial check before a
lead synthesizes the final artifact — nothing ships on a single agent's
opinion.

| Skill | Question it answers | Output |
|---|---|---|
| `team-research` | What does the external evidence say about this space? | `research/<topic-slug>/dossier.md` — sourced market size, competitors, monetization patterns, contradicting evidence |
| `team-viability` | Should we build (or keep investing in) this? | `viability/<target-slug>/verdict.md` — **BUILD / DON'T BUILD / NEEDS MORE EVIDENCE**, with confidence and the judge's strongest counter-argument |
| `team-business-plan` | It's a BUILD — what's the plan? | `viability/<target-slug>/business-plan/business-plan.md` — offering & MVP, financial model, plan-level go-to-market, milestones, risks |

## The chain is the point

- `team-viability` **requires** a `team-research` dossier for the target's
  topic — its market specialist consumes the dossier instead of improvising
  its own research. No dossier → the run stops and tells you to research
  first.
- `team-business-plan` **requires** a `team-viability` verdict — no
  `verdict.md`, no plan. A DON'T BUILD verdict requires your explicit
  override; NEEDS MORE EVIDENCE requires your explicit go-ahead, with every
  named evidence gap carried forward as a standing risk.
- `team-viability`'s differentiator is `viability-product`: it ingests the
  **real** product/repo/artifact when one exists, not a description of it.

## Usage

```
/team-research research <topic>
/team-viability evaluate <idea or path to a real repo/artifact>
/team-business-plan plan <evaluated target>
```

Outputs land in the current project (`research/` and `viability/` folders at
the project root). Team memory (run-logs, standing decisions) lives with the
plugin's bundled skill folders — see the "Path note (plugin install)" in each
`SKILL.md`.

## Agents

17 registered subagent types: `research-triage`, `research-scout`,
`research-comparator`, `research-validator`, `research-lead`,
`viability-triage`, `viability-product`, `viability-market`,
`viability-stakeholder`, `viability-judge`, `viability-lead`,
`bizplan-triage`, `bizplan-offering`, `bizplan-financial`, `bizplan-gtm`,
`bizplan-judge`, `bizplan-lead`.
