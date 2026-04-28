# Instructions — Phase 22: BA/PM Story Agent & Ticket Implementation Agent

> Add this file to your IDE's custom instructions when working on the BA/PM Story Agent or Ticket Implementation Agent.

---

## Context

You are building two closely-related agents:
1. **BA/PM Story Agent** — Parses business requirements (BRDs, HLDs, ICDs) and generates structured Jira epics/stories ready for sprint planning
2. **Ticket Implementation Agent** — Takes a ready Jira ticket and autonomously implements it end-to-end (backend + frontend + tests + PR)

---

## BA/PM Story Agent

### Input Requirements

```python
class BaPmAgentInput(BaseModel):
    documents:           list[str]     # File paths or text of BRD/HLD/ICD
    project_id:          str
    domain:              str           # e.g. "DGD"
    target_sprint_count: int = 3       # How many sprints to plan
    story_point_scale:   list[int] = [1, 2, 3, 5, 8, 13]
```

### Story Output Format

```python
class UserStory(BaseModel):
    id:               str      # AC-{DOMAIN}-{NNN} format
    epic:             str      # Epic name
    title:            str      # "As a {role} I want {goal} so that {benefit}"
    acceptance_criteria: list[str]  # Each item is a testable AC
    story_points:     int      # Fibonacci scale
    dependencies:     list[str]  # Other story IDs this depends on
    suggested_sprint: int      # 1-based sprint number
    risk_items:       list[str]  # Technical risks identified
    labels:           list[str]  # ["ai-implement"] if eligible for Ticket Agent
```

### Eligibility for Ticket Implementation Agent

Stories get `ai-implement` label if they meet ALL:
- story_points ≤ 8
- No cross-system integration dependencies
- Bounded context already exists in codebase
- No UI redesign (feature additions only)

## Ticket Implementation Agent

### Pre-Implementation Checks

```python
ELIGIBILITY_RULES = [
    lambda t: t.story_points <= 8,                    # Size limit
    lambda t: "ai-implement" in t.labels,             # Opted in
    lambda t: t.status == "Ready for Development",    # Correct status
    lambda t: not t.is_blocked_by_critical_bug,       # No blockers
    lambda t: architecture_in_ledger(t.project_id),   # Architecture approved
    lambda t: t.story_points > 0,                     # Must be estimated
    lambda t: len(t.acceptance_criteria) >= 2,        # Must have testable ACs
    lambda t: not any("API_KEY" in ac for ac in t.acceptance_criteria),  # No secrets in ACs
]
```

### PR Generation Rules

```python
class PrAssembly(BaseModel):
    branch_name:     str    # ticket/{TICKET-ID}-{slug}  e.g. ticket/DGD-142-submit-dgd
    commit_message:  str    # "{TICKET-ID}: {title}" e.g. "DGD-142: Submit dangerous goods declaration"
    pr_title:        str    # Same as commit_message
    pr_description:  str    # Markdown with AC checklist (see below)
    target_branch:   str    # Always "develop"
    draft:           bool   # True until Playwright E2E pass

# PR description template:
"""
## {TICKET-ID}: {Story Title}

### Changes
{bullet list of files changed}

### Acceptance Criteria
- [x] AC1: {criterion text}
- [x] AC2: {criterion text}
- [ ] AC3: {criterion text — check marks only after CI passes}

### Test Evidence
- Unit tests: {X} added, all passing
- Integration tests: {Y} added, all passing
- Playwright E2E: Running in pipeline...

### Ledger Reference
Pipeline Ledger event: `{event_id}`
"""
```

### Jira Ticket Transitions

```
"Ready for Development" → "In Progress"    ← When agent starts
"In Progress"           → "In Review"      ← When PR is created
"In Review"             → "Done"           ← When PR is merged (webhook)
"In Review"             → "In Progress"    ← When PR has requested changes
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Story without acceptance criteria | Untestable stories cannot be implemented |
| `ai-implement` label on stories > 8 points | Agent may not complete; wastes LLM budget |
| Agent pushing directly to `main` | All changes go to `develop` via PR |
| Agent approving its own PR | Self-approval is forbidden (enforced by Hook Engine) |
| Implementing a ticket with a CRITICAL security label | Security issues go to manual track |

---

*Instructions — Phase 22 — AD Ports AI Portal — Applies to: Delivery Agents Squad + BA/PM*
