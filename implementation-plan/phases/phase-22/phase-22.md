# Phase 22 — BA/PM Story Agent & Ticket Implementation Agent

## Summary

Implement two complementary agents:

1. **BA/PM Story Agent** — takes a raw project request (email, Confluence page, or free text) and produces a structured Product Backlog: epics, user stories, acceptance criteria, story points, dependencies, and a prioritized roadmap. Output syncs to Jira or Azure Boards.

2. **Ticket Implementation Agent** — takes a single JIRA/ADO ticket (user story or task) and produces a complete, ready-to-review code change that implements that specific story end-to-end (backend handler + API endpoint + Angular component + migration + tests).

---

## Objectives

1. Implement BA Agent — intake parser (raw text → structured requirement model).
2. Implement BA Agent — BRD decomposer (bounded contexts, user journeys, acceptance criteria).
3. Implement BA Agent — story generator (epics → stories → tasks with estimates).
4. Implement BA Agent — Jira/ADO sync (create epics/stories/tasks via MCP).
5. Implement BA Agent — roadmap generator (prioritized sprint plan).
6. Implement BA Agent — human review gate (BA must approve before sync).
7. Implement Ticket Agent — ticket reader (fetch story + acceptance criteria from Jira/ADO).
8. Implement Ticket Agent — multi-agent orchestration (Backend + Frontend + Database + QA agents all delegated).
9. Implement Ticket Agent — PR creator (opens PR with all generated code + links to ticket).
10. Implement Ticket Agent — completion signal (marks ticket In Review when PR opened).

---

## Prerequisites

- Phase 09 (Jira MCP + Azure Boards MCP).
- Phase 10 (Orchestrator — orchestrates multi-agent delegation).
- Phase 12–16 (all specialist agents already implemented).
- Phase 21 (PR Review Agent — auto-reviews the PR after Ticket Agent creates it).

---

## Duration

**4 weeks**

**Squad:** Intelligence Squad + Delivery Agents Squad (2 Python/AI engineers + 1 .NET + 1 Angular)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Intake parser | Raw DGD project request → structured requirement model |
| D2 | BRD decomposer | BRD sections → bounded contexts + user journeys |
| D3 | Story generator | 3 epics + 15 stories with estimates generated for DGD |
| D4 | Jira/ADO sync | Epics + stories created in Jira; hierarchy correct |
| D5 | Roadmap generator | Prioritized sprint plan with dependencies |
| D6 | Human review gate | BA must review + approve before Jira sync |
| D7 | Ticket reader | Story + acceptance criteria read from Jira/ADO |
| D8 | Multi-agent orchestration | Backend + Frontend + DB + QA agents all delegated from one ticket |
| D9 | PR creator | PR opened with all generated code; linked to Jira ticket |
| D10 | Ticket completion | Ticket transitions to "In Review" when PR opened |

---

## BA/PM Story Agent

### Intake Flow

```
Input: "We need to digitize the DGD (Dangerous Goods Declaration) process.
Currently shippers email PDF forms to customs@adports.ae and we manually
enter them. The new system needs to accept online submissions, validate
against SINTECE customs rules, calculate the dangerous goods surcharge,
notify the shipper, and report to the Ministry of Economy."

        │
        ▼ IntakeParser
        
ProjectRequirement(
  name="DGD — Dangerous Goods Declaration Digitization",
  domain="customs",
  stakeholders=["Customs Operations", "Shippers", "Ministry of Economy"],
  pain_points=["Manual PDF processing", "No real-time status", "Delayed notifications"],
  bounded_contexts=[
    BoundedContext("Declaration Submission", actors=["Shipper"]),
    BoundedContext("Customs Validation", actors=["Customs Officer", "SINTECE API"]),
    BoundedContext("Fee Calculation", actors=["Finance System"]),
    BoundedContext("Notification", actors=["Shipper", "MoE"]),
  ],
  integrations=["SINTECE API", "Ministry of Economy API", "Notification Hub"]
)
```

### Story Generator Output

```json
{
  "epics": [
    {
      "id": "EP-001",
      "title": "Declaration Submission Portal",
      "stories": [
        {
          "id": "US-001",
          "title": "As a shipper, I can submit a general cargo declaration online",
          "acceptanceCriteria": [
            "Given I am logged in as a shipper",
            "When I fill in the declaration form with required fields",
            "And I click Submit",
            "Then the system creates a declaration with status 'Submitted'",
            "And I receive a reference number DGD-XXXXXXXX",
            "And the customs team is notified"
          ],
          "storyPoints": 5,
          "priority": "P1",
          "labels": ["backend", "frontend", "api"]
        }
      ]
    }
  ]
}
```

### Jira Sync

```python
# BA agent → Jira MCP
await jira_mcp.create_epic({
    "project": "DGD",
    "summary": "Declaration Submission Portal",
    "description": epic.description,
    "customFields": {
        "customfield_10014": roadmap.target_quarter  # Fix version
    }
})

for story in epic.stories:
    await jira_mcp.create_story({
        "project": "DGD",
        "parent": epic_key,
        "summary": story.title,
        "description": format_story_description(story),
        "storyPoints": story.story_points,
        "priority": story.priority
    })
```

---

## Ticket Implementation Agent

### End-to-End Flow

```
Architect assigns ticket DGD-US-001 to Ticket Implementation Agent
        │
        ▼ Ticket Agent reads from Jira
Story: "As a shipper, I can submit a general cargo declaration online"
Acceptance Criteria: [5 items]
Labels: [backend, frontend, api]
        │
        ▼ Orchestrator delegates to specialist agents in sequence:
        │
        ├── 1. Architecture check: Is this story in the approved architecture? ✓
        │
        ├── 2. Backend Agent:
        │      Create{Declaration}Command + Handler + Validator
        │      DeclarationsController.Post endpoint
        │      Result: new files added to dgd-declaration-service
        │
        ├── 3. Database Agent:
        │      Add EF Core migration for declarations table changes (if any)
        │
        ├── 4. Frontend Agent:
        │      DeclarationFormComponent in dgd-mfe
        │      Wire to declaration-service API client
        │
        ├── 5. QA Agent:
        │      Playwright test for AC-DGD-001
        │      Newman test case for POST /declarations
        │
        ▼ Ticket Agent creates PR:
        
PR Title: "[DGD-US-001] feat: shipper can submit general cargo declaration"
PR Body: 
  - Links to ticket
  - Summary of changes (auto-generated)
  - Checklist: ✓ Backend handler, ✓ API endpoint, ✓ DB migration, ✓ Frontend form, ✓ Tests
  
Jira ticket → "In Review"
PR Review Agent → auto-reviews PR and posts score
```

---

## PR Template (Generated)

```markdown
## Summary
Implements [DGD-US-001](https://jira.adports.ae/browse/DGD-US-001): As a shipper, I can submit a general cargo declaration online.

## Changes
### Backend (dgd-declaration-service)
- Added `CreateDeclarationCommand` + `Handler` + `Validator`
- Added `POST /api/declarations` endpoint in `DeclarationsController`
- All FluentValidation rules for required fields

### Database
- Added EF Core migration `20250101_AddDeclarationsTable`
- RLS policy added for tenant isolation

### Frontend (dgd-mfe)
- Added `DeclarationFormComponent` with PrimeNG form
- Wired to generated `DeclarationApiClient`
- English + Arabic translations added

### Tests
- Playwright: `dgd-submission.spec.ts` covers all 5 acceptance criteria
- Newman: `POST /declarations` happy path test case added

## Acceptance Criteria Coverage
- [x] AC1: Shipper can fill form with required fields
- [x] AC2: System creates declaration with Submitted status
- [x] AC3: Reference number DGD-XXXXXXXX returned
- [x] AC4: Customs team notified
- [x] AC5: Validation error for missing fields

## AI Review
This PR was generated and self-reviewed by the AI Portal Ticket Implementation Agent.
A human architect must approve before merge.
```

---

## Step-by-Step Execution Plan

### Week 1: BA Agent — Intake + Decompose + Generate

- [ ] Implement intake parser (raw text → structured requirement model).
- [ ] Implement BRD decomposer (extracts bounded contexts + user journeys).
- [ ] Implement story + acceptance criteria generator.
- [ ] Implement story point estimator (based on complexity heuristics).

### Week 2: BA Agent — Jira/ADO Sync + Roadmap

- [ ] Implement Jira sync (create epics/stories/tasks hierarchy).
- [ ] Implement ADO sync (create work items with same hierarchy).
- [ ] Implement roadmap generator (sprint-based dependency ordering).
- [ ] Implement human review gate (BA must approve decomposition before sync).

### Week 3: Ticket Implementation Agent — Core

- [ ] Implement ticket reader (Jira/ADO MCP fetch with full context).
- [ ] Implement story-to-work-package mapper (determines which specialist agents are needed).
- [ ] Implement multi-agent delegation orchestration (Backend + Frontend + DB + QA).
- [ ] Test: DGD-US-001 → all four agents run → code generated.

### Week 4: PR Creation + Completion + Integration

- [ ] Implement PR creator (opens GitLab/ADO PR with generated changes + template).
- [ ] Implement ticket completion signal (transitions Jira/ADO ticket status).
- [ ] Wire PR Review Agent auto-trigger after Ticket Agent PR creation.
- [ ] End-to-end test: Jira ticket → Ticket Agent → PR opened → PR Review Agent scores → architect approves merge.

---

## Gate Criterion

- Raw DGD project request → 3 epics + 15 stories + acceptance criteria in Jira within 15 minutes.
- BA approves decomposition before Jira sync.
- Jira ticket DGD-US-001 → Ticket Agent → PR opened with all 4 code layers + tests.
- PR Review Agent auto-reviews the Ticket Agent PR within 2 minutes.
- Jira ticket transitions to "In Review" when PR is opened.

---

*Phase 22 — BA/PM Story Agent & Ticket Implementation Agent — AI Portal — v1.0*
