#!/usr/bin/env python3
"""Import the live standalone install (~/.claude/skills + ~/.claude/agents)
into this repo's plugins/, applying the distribution transforms:

  - experimental banner on every SKILL.md
  - personalized wording sanitized (Sara -> the user)
  - existing plugin path-note blocks preserved in agent files
  - engineering-manager home paths rewritten plugin-relative
  - bash portability enforced in shipped shell templates
  - memory/ never synced (plugins ship empty memory)

Direction is one-way: ~/.claude is the working set; this repo is the
packaged distribution. Run before /refresh-plugins, review `git diff`,
then publish. Exits non-zero if a personal reference survives.

Usage: python3 scripts/sync-from-local.py [--dry-run]
"""
import os, re, sys, shutil, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TK = os.path.join(REPO, 'plugins')
SA = os.path.expanduser('~/.claude')
DRY = '--dry-run' in sys.argv

BANNER = '⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.'

# standalone skill dir -> plugin skill dir (SKILL.md + templates/references; never memory/)
SKILL_MAP = {
    'team-intake':         'delivery-team/skills/team-intake',
    'team-qa':             'delivery-team/skills/team-qa',
    'team-build':          'delivery-team/skills/team-build',
    'team-release':        'delivery-team/skills/team-release',
    'team-status':         'delivery-team/skills/team-status',
    'team-decisions':      'delivery-team/skills/team-decisions',
    'engineering-manager': 'engineering-manager/skills/engineering-manager',
    'wrap-up':             'dev-workflow/skills/wrap-up',
    'create-skill-devops': 'dev-workflow/skills/create-skill-devops',
    'team-research':       'viability-division/skills/team-research',
    'team-viability':      'viability-division/skills/team-viability',
    'team-business-plan':  'viability-division/skills/team-business-plan',
}

# Plugins whose packaged copies diverge from ~/.claude on purpose (heavier
# path-relativization / genericization than these transforms model). Sync
# them by hand, with a diff review, when their standalone behavior changes.
MANUAL_PLUGINS = ['librarian', 'product-analyst', 'story-map']

# standalone agent name -> plugin holding it
AGENT_MAP = {
    'delivery-team': [
        'build-implementer','build-lead','build-planner','build-reviewer',
        'build-test-author','build-triage','build-verifier',
        'director-of-engineering',
        'intake-architect','intake-client-liaison','intake-engineer',
        'intake-product-owner','intake-project-manager','intake-qa',
        'intake-tech-lead','intake-triage',
        'qa-coverage-cartographer','qa-e2e-architect','qa-lead',
        'qa-risk-analyst','qa-strategist','qa-triage','qa-unit-architect',
        'release-lead','release-scribe',
        'status-lead','status-scanner','status-triage',
    ],
    'engineering-manager': ['em-analyst','em-judge','em-lead'],
    'viability-division': [
        'research-triage','research-scout','research-comparator',
        'research-validator','research-lead',
        'viability-triage','viability-product','viability-market',
        'viability-stakeholder','viability-judge','viability-lead',
        'bizplan-triage','bizplan-offering','bizplan-financial',
        'bizplan-gtm','bizplan-judge','bizplan-lead',
    ],
}

SANITIZE = [
    ('so Sara can', 'so the user can'),
    ('Use when Sara says', 'Use when the user says'),
    ('Use when Sara types', 'Use when the user types'),
    ('Use when Sara runs', 'Use when the user runs'),
    ('Only after Sara answers', 'Only after the user answers'),
    ('deferred item Sara chose to skip', 'deferred item the user chose to skip'),
    ('Remind her:', 'Remind them:'),
    ("needs Sara's choice", "needs the user's choice"),
    ('Show Sara the audit output', 'Show the user the audit output'),
    ('are what Sara has asked for', 'are what the user has asked for'),
    ('show Sara', 'show the user'),
    ('Show Sara', 'Show the user'),
    ('give Sara', 'give the user'),
    ('make sure Sara answered', 'make sure the user answered'),
    ('ask Sara', 'ask the user'),
    ('Ask Sara', 'Ask the user'),
    # team-decisions pronoun phrasing (bare "Sara" is caught generically below,
    # but a bare-word swap reads wrong wherever the surrounding sentence also
    # carries a gendered pronoun referring to her — fix those together)
    ('to her directly via AskUserQuestion, recording her answer as a real DECIDED',
     'to them directly via AskUserQuestion, recording their answer as a real DECIDED'),
    ('Use when Sara asks', 'Use when the user asks'),
    ('or right after Sara answers', 'or right after the user answers'),
    ('used to be hers is now', 'used to be theirs is now'),
    ('taken off her plate', 'taken off their plate'),
    ('never gets taken off her\nplate', 'never gets taken off their\nplate'),
    ('of her — never a wall of raw markdown', 'of them — never a wall of raw markdown'),
    ("a risk tolerance she hasn't stated anywhere", "a risk tolerance they haven't stated anywhere"),
    ("fact about her actual intent that the file doesn't carry",
     "fact about their actual intent that the file doesn't carry"),
    ('whether she still wants this feature', 'whether they still want this feature'),
    ('two things she cares about', 'two things they care about'),
    ("If yes, it's hers.", "If yes, it's theirs."),
    ('already where a genuinely-hers call goes', 'already where a genuinely-theirs call goes'),
    ("Put Sara's-call items to her", "Put the user's-call items to them"),
    ('this is her actual answer (including her', 'this is their actual answer (including their'),
    ('own wording if she used "Other"', 'own wording if they used "Other"'),
    ('with her answer) already stated', 'with their answer) already stated'),
    ('team-decisions asks her directly via', 'team-decisions asks them directly via'),
    ('`AskUserQuestion` instead of guessing, and her answer gets the plain',
     '`AskUserQuestion` instead of guessing, and their answer gets the plain'),
    ('with `Decided by` naming her:', 'with `Decided by` naming them:'),
    ('(via team-decisions)` for one she answered through Step 4.5.',
     '(via team-decisions)` for one they answered through Step 4.5.'),
    ('a tie-break rule that re-applies a signal she said no to as the',
     'a tie-break rule that re-applies a signal they said no to as the'),
]

PERSONAL = ('Sara', '/Users/sara', 'CODE-LOCAL')

def sanitize(text):
    for a, b in SANITIZE:
        text = text.replace(a, b)
    # Any literal "Sara" surviving the phrase-level rewrites above is still a
    # personalization to catch, not a special case. Compound adjectives and
    # possessives go first so the article/hyphen come out right; YAML's
    # doubled-apostrophe escaping (''s) is handled before the plain 's form.
    text = re.sub(r"\bSara-", 'user-', text)
    text = re.sub(r"\bSara''s\b", "the user''s", text)
    text = re.sub(r"\bSara's\b", "the user's", text)
    text = re.sub(r"\bSara\b", 'the user', text)
    return text

def add_banner(text):
    if 'Experimental.' in text:
        return text
    lines = text.split('\n')
    for i, l in enumerate(lines):
        if l.startswith('# '):
            return '\n'.join(lines[:i+1] + ['', BANNER] + lines[i+1:])
    return text

def extract_pathnote(path):
    if not os.path.exists(path):
        return None
    lines = open(path).read().split('\n')
    start = next((i for i, l in enumerate(lines)
                  if l.startswith('> **Path note (plugin install):**')), None)
    if start is None:
        return None
    end = start
    while end + 1 < len(lines) and lines[end + 1].startswith('>'):
        end += 1
    return '\n'.join(lines[start:end+1])

def insert_after_frontmatter(text, block):
    lines = text.split('\n')
    dashes = [i for i, l in enumerate(lines) if l.strip() == '---']
    if len(dashes) < 2:
        return text
    return '\n'.join(lines[:dashes[1]+1] + ['', block] + lines[dashes[1]+1:])

def relativize_home_paths(text, plugin_skill):
    # `~/.claude/skills/<name>/...` refs are fine where a path note explains
    # them; for plugins that instead relativize inline, rewrite.
    return re.sub(
        r"\(see\s*\n?`~/\.claude/skills/" + re.escape(plugin_skill) + r"/(templates/[\w./-]+)` for the\s*\n?exact section order\)",
        r"(see this plugin's own\nbundled `\1` for the exact section order)", text
    ).replace(f'`~/.claude/skills/{plugin_skill}/', "this plugin's own bundled `")

def enforce_bash(text):
    return text.replace('#!/bin/zsh', '#!/usr/bin/env bash') \
               .replace('setopt null_glob', 'shopt -s nullglob') \
               .replace('zsh <skill-base-dir>', 'bash <skill-base-dir>')

def write(dst, text, report, tag):
    if os.path.exists(dst) and open(dst).read() == text:
        return
    report.append(f'{tag}  {os.path.relpath(dst, REPO)}')
    if not DRY:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'w').write(text)

def main():
    report, missing = [], []

    for sa_name, tk_rel in SKILL_MAP.items():
        src_dir = f'{SA}/skills/{sa_name}'
        if not os.path.isdir(src_dir):
            missing.append(f'skill {sa_name}')
            continue
        dst_dir = f'{TK}/{tk_rel}'
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in ('memory', '.git', 'audit', 'config', '__pycache__')]
            for f in files:
                if f.startswith('.'):
                    continue
                src = os.path.join(root, f)
                rel = os.path.relpath(src, src_dir)
                dst = os.path.join(dst_dir, rel)
                text = sanitize(open(src).read())
                if f == 'SKILL.md':
                    text = add_banner(text)
                if 'engineering-manager' in tk_rel:
                    text = relativize_home_paths(text, sa_name)
                text = enforce_bash(text)
                write(dst, text, report, 'SKILL' if f == 'SKILL.md' else 'FILE ')

    for plugin, agents in AGENT_MAP.items():
        for n in agents:
            src = f'{SA}/agents/{n}.md'
            if not os.path.isfile(src):
                missing.append(f'agent {n}')
                continue
            dst = f'{TK}/{plugin}/agents/{n}.md'
            note = extract_pathnote(dst)
            text = sanitize(open(src).read())
            if plugin == 'engineering-manager':
                text = relativize_home_paths(text, 'engineering-manager')
            if note and 'Path note (plugin install)' not in text:
                text = insert_after_frontmatter(text, note)
            write(dst, text, report, 'AGENT')

    print('\n'.join(report) if report else 'Nothing to sync — plugins already match ~/.claude.')
    print('\nManual-sync plugins (not touched — diverge from ~/.claude by design): '
          + ', '.join(MANUAL_PLUGINS))
    if missing:
        print('\nNo standalone counterpart (left as-is):')
        print('\n'.join(f'  - {m}' for m in missing))

    if not DRY and report:
        leaks = []
        for r in report:
            path = os.path.join(REPO, r.split(None, 1)[1])
            t = open(path).read()
            leaks += [f'{m} in {r.split(None, 1)[1]}' for m in PERSONAL if m in t]
        if leaks:
            print('\nFAIL — personal references survived sanitize (extend SANITIZE and re-run):')
            print('\n'.join(f'  - {l}' for l in leaks))
            sys.exit(1)
        print('\nPASS — no personal references in synced files. Review `git diff`, then run /refresh-plugins.')

if __name__ == '__main__':
    main()
