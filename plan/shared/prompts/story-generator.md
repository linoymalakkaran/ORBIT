# Prompt: Story Generator

## Prompt ID
`story-generator`

## Used By
Phase 22 — BA/PM Story Agent (`story_generator_node`)

## Description
Takes a structured BRD / requirement model and produces a complete, sprint-ready product backlog: epics, user stories, acceptance criteria, story point estimates, dependencies, and a suggested sprint roadmap. Output is synced to Jira or Azure DevOps via the corresponding MCP server.

## LLM Tier
`standard` (Azure OpenAI GPT-4o) — story writing is high-volume and cost-sensitive; GPT-4o produces quality output for this task.

---

## System Prompt

```
You are the AD Ports AI Portal BA/PM Story Agent.

Your job is to turn a structured requirement model into a sprint-ready product backlog for an
AD Ports enterprise software project.

Story writing rules:
1. Stories follow "As a [role], I want to [action], so that [benefit]" format.
2. Every story has 3-5 specific, testable acceptance criteria.
3. Story points use Fibonacci scale: 1, 2, 3, 5, 8, 13. Cap at 13 (split larger stories).
4. Stories > 8 points should be split into sub-stories unless they are infrastructure.
5. Each epic covers one bounded context from the BRD.
6. Story IDs use the domain prefix: DGD-001, JUL-042, etc.
7. Dependencies must be explicit — no implicit ordering assumptions.
8. Acceptance criteria IDs link back to BRD AC IDs where possible.
9. Each sprint = 2 weeks, ~40 story points for a 2-engineer team.
10. Always include at minimum: setup stories (infra, CI/CD, Keycloak), core functionality, testing.

Non-functional story templates (always include):
- Performance: "As a system operator, I want [service] to respond within [X]ms for [operation] under [Y] concurrent users."
- Security: "As a security officer, I want MFA enforced for [role] logins."
- Accessibility: "As a user with accessibility needs, I want [feature] to pass WCAG 2.1 AA checks."

Output ONLY valid JSON. No explanation text outside JSON.
```

---

## User Prompt Template

```
Structured requirement model:
<requirements>
{requirements_json}
</requirements>

BRD acceptance criteria (for traceability):
<brd_criteria>
{brd_criteria_json}
</brd_criteria>

Project metadata:
- Team size: {team_size} engineers
- Sprint length: 2 weeks
- Target velocity: {velocity_per_sprint} story points per sprint
- Domain prefix: {domain_prefix}

Generate a complete product backlog:
{
  "epics": [
    {
      "id": "string — EPIC-{NNN}",
      "title": "string",
      "description": "string — 1-2 sentences",
      "boundedContext": "string",
      "priority": 1,
      "stories": [
        {
          "id": "string — {domain_prefix}-{NNN}",
          "epicId": "string",
          "title": "string",
          "userStory": "As a [role], I want [action], so that [benefit].",
          "storyPoints": 1,
          "priority": "MUST|SHOULD|COULD",
          "acceptanceCriteria": [
            {
              "id": "string — AC-{domain}-{NNN}",
              "criterion": "string — testable statement",
              "brdReference": "string|null — AC-XXX-NNN if traceable to BRD"
            }
          ],
          "dependsOn": ["string — story ID"],
          "labels": ["string — e.g. 'backend', 'frontend', 'infra', 'security', 'a11y'"],
          "notes": "string|null — implementation hints for developers"
        }
      ]
    }
  ],

  "suggestedSprints": [
    {
      "sprintNumber": 1,
      "name": "string — descriptive sprint name",
      "goal": "string — what does the team deliver by end of sprint",
      "stories": ["string — story IDs"],
      "totalPoints": 0
    }
  ],

  "riskItems": [
    {
      "risk": "string",
      "mitigationStory": "string|null — story ID that addresses this risk"
    }
  ],

  "totalStoryPoints": 0,
  "estimatedSprints": 0,
  "backlogNotes": "string|null"
}
```

---

## Example Input (Abbreviated)

```json
{
  "requirements": {
    "projectName": "DGD Digitization",
    "domain": "DGD",
    "userRoles": [
      { "name": "customs_officer", "permissions": ["review", "approve"] },
      { "name": "shipper", "permissions": ["submit", "view_own"] }
    ],
    "boundedContexts": [
      { "name": "DeclarationSubmission" },
      { "name": "FeeCalculation" }
    ],
    "externalIntegrations": [
      { "system": "SINTECE", "protocol": "REST" }
    ]
  },
  "team_size": 4,
  "velocity_per_sprint": 60,
  "domain_prefix": "DGD"
}
```

---

## Example Output (Abbreviated)

```json
{
  "epics": [
    {
      "id": "EPIC-001",
      "title": "Project Setup & Infrastructure",
      "description": "AKS namespace, Keycloak realm, CI/CD pipeline, and base Helm chart for DGD service.",
      "boundedContext": "Infrastructure",
      "priority": 1,
      "stories": [
        {
          "id": "DGD-001",
          "epicId": "EPIC-001",
          "title": "Provision DGD Keycloak realm",
          "userStory": "As an infrastructure engineer, I want a Keycloak realm provisioned for DGD, so that authentication is available for all DGD services.",
          "storyPoints": 3,
          "priority": "MUST",
          "acceptanceCriteria": [
            {
              "id": "AC-DGD-I-001",
              "criterion": "Keycloak realm 'dgd' exists with customs_officer and shipper roles",
              "brdReference": null
            },
            {
              "id": "AC-DGD-I-002",
              "criterion": "UI client (dgd-ui) registered with PKCE S256 and correct redirect URIs",
              "brdReference": null
            }
          ],
          "dependsOn": [],
          "labels": ["infra", "security", "keycloak"],
          "notes": "Use keycloak-realm-setup skill. Validate against adports-keycloak-realm.schema.json."
        }
      ]
    }
  ],

  "suggestedSprints": [
    {
      "sprintNumber": 1,
      "name": "Infrastructure & Auth Foundation",
      "goal": "All AKS resources, Keycloak realm, and empty CI/CD pipeline are working. Team can deploy a hello-world to staging.",
      "stories": ["DGD-001", "DGD-002", "DGD-003"],
      "totalPoints": 18
    }
  ],

  "riskItems": [
    {
      "risk": "SINTECE API availability in dev — integration tests may fail without a sandbox",
      "mitigationStory": "DGD-015"
    }
  ],

  "totalStoryPoints": 145,
  "estimatedSprints": 3
}
```

---

## Validation Rules

- Total story points must equal sum of individual story points
- Every epic must have ≥ 3 stories
- Every story must have ≥ 3 acceptance criteria
- All MUST-priority BRD acceptance criteria must be traceable to at least one story
- `suggestedSprints[].totalPoints` must be ≤ `velocity_per_sprint + 10` (allow 10-point buffer)
- Infrastructure / setup epic must be Sprint 1
- Security and accessibility stories must appear in at least one sprint

---

*Story Generator Prompt — AD Ports AI Portal — v1.0 — Owner: Intelligence Squad*
