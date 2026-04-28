# Phase 21 — PR Review Agent

## Summary

Implement the **PR Review Agent** — an AI-powered code review assistant that evaluates pull requests against AD Ports coding standards, security policies, performance best practices, and the project's own architecture decisions. The PR Review Agent posts structured review comments directly in GitLab/Azure DevOps and calculates a reviewability score. Human architects retain final merge authority.

---

## Objectives

1. Implement PR diff fetcher (GitLab MCP + ADO MCP).
2. Implement coding standards checker (language-specific rules from Capability Fabric).
3. Implement security vulnerability scanner (pre-check before Checkmarx; pattern-based).
4. Implement architecture drift detector (checks PR against approved architecture in Ledger).
5. Implement test coverage analyzer (reports coverage delta from PR).
6. Implement performance anti-pattern detector.
7. Implement PR review comment poster (structured markdown comments in GitLab/ADO).
8. Implement reviewability score calculator.
9. Implement PR merge gate (blocks merge if critical issues found + reviewer override).
10. Implement `adports-ai review pr` CLI command.

---

## Prerequisites

- Phase 08 (GitLab MCP / ADO MCP — diff fetch and comment posting).
- Phase 07 (Capability Fabric — coding standards skills + instructions).
- Phase 10 (Orchestrator — PR review is a delegatable work package).
- Phase 18 (Hook Engine — PR review requests evaluated against policies).

---

## Duration

**3 weeks**

**Squad:** QA & Test Squad + Delivery Agents Squad (1 senior QA + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | PR diff fetcher | Full diff (unified format) retrieved for a DGD PR |
| D2 | Coding standards checker | AD Ports C# and Angular rules checked; violations reported |
| D3 | Security vulnerability scanner | Pattern-based SQL injection, hardcoded secret detection works |
| D4 | Architecture drift detector | Added dependency not in approved architecture flagged |
| D5 | Test coverage analyzer | Coverage delta shown; failing coverage gate blocks merge |
| D6 | Performance anti-pattern detector | N+1 query, synchronous HTTP in hot path detected |
| D7 | Comment poster | Inline GitLab/ADO comments with severity labels and fix suggestions |
| D8 | Reviewability score | 0–100 score with breakdown by category |
| D9 | Merge gate | PR with critical findings blocks merge; architect override flow |
| D10 | CLI command | `adports-ai review pr --repo=dgd --pr=42` runs full review |

---

## PR Review Workflow

```
Developer opens PR in GitLab
        │
        ▼ (GitLab webhook → Portal)
PR Review Agent triggered
        │
        ▼
Fetch diff via GitLab MCP
        │
        ├── Coding standards checker (deterministic AST analysis)
        ├── Security pattern scanner (regex + AST)
        ├── Architecture drift check (compare against Ledger)
        ├── Test coverage delta (from CI test artifacts)
        └── LLM review (10-20% of total analysis)
                        │
                        ▼
        Compose review (group findings by file + category)
                        │
                        ▼
        Post comments to GitLab PR (inline + summary)
                        │
                        ▼
        Post reviewability score on PR
                        │
                        ├─ CRITICAL findings → Block merge + notify architect
                        └─ No CRITICAL → Approve (human still required for merge)
```

---

## Coding Standards Rules (C#)

The PR Review Agent checks the rules from `shared/instructions/coding-standards-csharp.md`:

```python
# review/checkers/csharp_checker.py
CSHARP_RULES: list[ReviewRule] = [
    ReviewRule(
        id="CS001",
        severity="ERROR",
        description="Do not call .Result or .Wait() on async tasks",
        pattern=r'\.(Result|Wait)\s*[\(;]',
        message="Use 'await' instead of blocking .Result/.Wait() to avoid deadlocks.",
        fix_suggestion="Replace `.Result` with `await`."
    ),
    ReviewRule(
        id="CS002",
        severity="ERROR",
        description="Do not return Task from void methods (use async Task)",
        pattern=r'public\s+void\s+\w+\s*\([^)]*\)\s*\{[^}]*await',
        message="Async void methods can't be awaited and swallow exceptions.",
        fix_suggestion="Change return type from `void` to `Task`."
    ),
    ReviewRule(
        id="CS003",
        severity="WARNING",
        description="EF Core queries should use AsNoTracking() for read-only operations",
        pattern=r'\.FirstOrDefaultAsync|\.ToListAsync|\.SingleOrDefaultAsync',
        # Further check: no AsNoTracking() in same chain
        message="Read-only queries should use .AsNoTracking() for performance.",
        fix_suggestion="Add `.AsNoTracking()` before `.FirstOrDefaultAsync()` or `.ToListAsync()`."
    ),
    ReviewRule(
        id="CS004",
        severity="ERROR",
        description="Do not hardcode secrets or connection strings",
        pattern=r'(?i)(password|connectionstring|secret|apikey)\s*=\s*"[^"]{4,}"',
        message="Hardcoded secret detected. Use IConfiguration or Vault.",
        fix_suggestion="Read from `config['SectionName:Key']` or use Vault Agent Injector."
    ),
    ReviewRule(
        id="CS005",
        severity="WARNING",
        description="Use cancellation tokens in async methods",
        pattern=r'public\s+async\s+Task.*\([^)]*\)\s*\{',
        # Further check: no CancellationToken parameter
        message="Async methods should accept CancellationToken to support cancellation.",
        fix_suggestion="Add `CancellationToken cancellationToken = default` parameter."
    ),
]
```

---

## Reviewability Score

```python
SCORE_WEIGHTS = {
    "coding_standards": 0.25,   # 25 points
    "security":         0.35,   # 35 points (highest weight)
    "architecture":     0.20,   # 20 points
    "test_coverage":    0.15,   # 15 points
    "performance":      0.05,   # 5 points
}

def calculate_score(findings: ReviewFindings) -> ReviewScore:
    scores = {}
    for category, weight in SCORE_WEIGHTS.items():
        category_findings = findings.by_category[category]
        critical = sum(1 for f in category_findings if f.severity == "ERROR")
        warnings  = sum(1 for f in category_findings if f.severity == "WARNING")

        # Deductions: -10 per ERROR, -3 per WARNING (capped at category max)
        deductions = min(critical * 10 + warnings * 3, int(weight * 100))
        scores[category] = int(weight * 100) - deductions

    total = sum(scores.values())
    return ReviewScore(
        total=total,
        breakdown=scores,
        grade="A" if total >= 90 else "B" if total >= 75 else "C" if total >= 60 else "F",
        merge_blocked=any(f.severity == "ERROR" for f in findings.all)
    )
```

---

## GitLab Comment Format

```markdown
## 🤖 AI Portal Code Review

**Reviewability Score: 73/100 (Grade C)**

| Category | Score | Findings |
|----------|-------|---------|
| Security | 20/35 | 3 ERRORs |
| Coding Standards | 22/25 | 1 WARNING |
| Architecture | 20/20 | ✓ |
| Test Coverage | 6/15 | Coverage dropped from 82% → 71% |
| Performance | 5/5 | ✓ |

---

### 🔴 CRITICAL — Merge Blocked

**[CS004] Hardcoded secret — `src/DeclarationService.Api/appsettings.json:45`**
```json
"ConnectionStrings": {
  "Postgres": "Host=prod-db;Username=app;Password=Sup3rS3cret!"
}
```
❌ Hardcoded connection string with password in source code.
✅ Fix: Use `config['ConnectionStrings:Postgres']` populated by Vault Agent Injector.

---

### ⚠️ Warnings (2)

**[CS003] Missing AsNoTracking — `src/.../GetDeclarationQueryHandler.cs:28`**
```csharp
return await _context.Declarations
    .Where(d => d.ProjectId == request.ProjectId)
    .ToListAsync();  // Missing .AsNoTracking()
```

---
*Review by AD Ports AI Portal — [View in Portal](#) | [Override](# "Requires architect role")*
```

---

## Step-by-Step Execution Plan

### Week 1: Diff Fetch + Static Analysis

- [ ] Implement PR diff fetcher via GitLab MCP + ADO MCP.
- [ ] Implement coding standards checker (C# + TypeScript rules).
- [ ] Implement security pattern scanner (hardcoded secrets, SQL injection, SSRF patterns).
- [ ] Implement architecture drift detector (new service deps vs. Ledger-approved architecture).

### Week 2: Coverage + Performance + Score

- [ ] Implement test coverage analyzer (parse coverage reports from CI artifacts).
- [ ] Implement performance anti-pattern detector (N+1, sync HTTP, large payload).
- [ ] Implement reviewability score calculator.
- [ ] Implement comment formatter (inline + summary markdown).

### Week 3: Comment Posting + Gate + CLI

- [ ] Implement GitLab/ADO comment poster (inline + summary comment).
- [ ] Implement merge gate (block/unblock via GitLab API approval rules).
- [ ] Implement architect override flow (override requires Portal approval + Ledger entry).
- [ ] Implement `adports-ai review pr` CLI command.
- [ ] End-to-end test: DGD PR with a hardcoded secret → blocked + inline comment posted.

---

## Gate Criterion

- PR with hardcoded secret → inline comment posted + merge blocked within 2 minutes.
- PR without issues → reviewability score 90+ + auto-approve (human still merges).
- Architecture drift (new unapproved dependency) flagged correctly.
- Architect override flow works: override requires Portal approval + Ledger entry.
- `adports-ai review pr` CLI command runs full review.

---

*Phase 21 — PR Review Agent — AI Portal — v1.0*
