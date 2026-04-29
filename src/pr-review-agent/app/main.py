"""PR Review Agent — Phase 21: Enhanced AI-powered code review for GitLab MRs.

Features:
  - Full diff fetch via GitLab API
  - Coding standards checker (C# + TypeScript/Angular rules)
  - Security pattern scanner (hardcoded secrets, SQL injection, SSRF)
  - Architecture drift detector (checks against Pipeline Ledger approved architecture)
  - Test coverage analyser (coverage delta from CI artifacts)
  - Performance anti-pattern detector (N+1, sync HTTP, large payload)
  - Reviewability score calculator (0-100 with letter grade)
  - Inline GitLab comment poster (structured markdown)
  - Merge gate (blocks merge if CRITICAL findings)
  - Records all reviews to Pipeline Ledger
"""
from __future__ import annotations

import asyncio
import json
import logging
import operator
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, TypedDict

import httpx
import litellm
from fastapi import FastAPI, HTTPException
from langgraph.graph import END, StateGraph
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ── Settings ──────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRREVIEW_", env_file=".env", extra="ignore")

    gitlab_url: str = "https://gitlab.adports.ae"
    gitlab_token: str = ""
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    premium_model: str = "gpt-4o"
    pipeline_ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80/api/ledger"
    coverage_threshold: float = 80.0   # minimum acceptable coverage %
    max_diff_bytes: int = 80_000       # truncate diff beyond this


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


# ── Review rules ──────────────────────────────────────────────────────────────
class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ReviewRule:
    id: str
    severity: Severity
    category: str
    description: str
    pattern: str
    message: str
    fix_suggestion: str


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    category: str
    file: str
    line: int
    message: str
    fix_suggestion: str
    snippet: str = ""


CSHARP_RULES: list[ReviewRule] = [
    ReviewRule(
        id="CS001", severity=Severity.ERROR, category="coding_standards",
        description="Blocking async task with .Result/.Wait()",
        pattern=r"\.(Result|Wait)\s*[\(;]",
        message="Use 'await' instead of blocking .Result/.Wait() to avoid deadlocks.",
        fix_suggestion="Replace `.Result` with `await`.",
    ),
    ReviewRule(
        id="CS002", severity=Severity.ERROR, category="coding_standards",
        description="async void method",
        pattern=r"public\s+async\s+void\s+\w+",
        message="Async void methods can't be awaited and swallow exceptions.",
        fix_suggestion="Change return type from `void` to `Task`.",
    ),
    ReviewRule(
        id="CS003", severity=Severity.WARNING, category="coding_standards",
        description="Missing AsNoTracking() on read-only EF Core query",
        pattern=r"(?:FirstOrDefaultAsync|ToListAsync|SingleOrDefaultAsync)\(\)",
        message="Read-only queries should use .AsNoTracking() for performance.",
        fix_suggestion="Add `.AsNoTracking()` before the terminal method.",
    ),
    ReviewRule(
        id="CS004", severity=Severity.ERROR, category="security",
        description="Hardcoded secret / connection string",
        pattern=r'(?i)(password|connectionstring|secret|apikey)\s*=\s*"[^"]{4,}"',
        message="Hardcoded secret detected. Use IConfiguration or Vault.",
        fix_suggestion="Read from config / Vault Agent Injector.",
    ),
    ReviewRule(
        id="CS005", severity=Severity.ERROR, category="security",
        description="Potential SQL injection via string concatenation",
        pattern=r'(?i)(execute|executesql|fromSqlRaw)\s*\(\s*\$?"[^"]*\+',
        message="SQL injection risk — use parameterised queries.",
        fix_suggestion="Use EF Core parameters or `SqlParameter`.",
    ),
    ReviewRule(
        id="CS006", severity=Severity.WARNING, category="performance",
        description="Synchronous HTTP call inside async method",
        pattern=r"\.GetAwaiter\(\)\.GetResult\(\)|\.Result\b",
        message="Blocking HTTP call detected. Use await with HttpClient.",
        fix_suggestion="Await the async HTTP method directly.",
    ),
]

TYPESCRIPT_RULES: list[ReviewRule] = [
    ReviewRule(
        id="TS001", severity=Severity.ERROR, category="security",
        description="Direct innerHTML assignment (XSS risk)",
        pattern=r"innerHTML\s*=",
        message="Direct innerHTML assignment can lead to XSS. Use DomSanitizer.",
        fix_suggestion="Use Angular `[innerHTML]` with DomSanitizer.bypassSecurityTrustHtml().",
    ),
    ReviewRule(
        id="TS002", severity=Severity.ERROR, category="security",
        description="Hardcoded API key or secret in TypeScript",
        pattern=r'(?i)(apikey|secret|token|password)\s*[:=]\s*["\'][^"\']{8,}["\']',
        message="Hardcoded secret in TypeScript. Use environment files.",
        fix_suggestion="Move to environment.ts and inject via injection token.",
    ),
    ReviewRule(
        id="TS003", severity=Severity.WARNING, category="coding_standards",
        description="console.log left in production code",
        pattern=r"\bconsole\.(log|warn|error|debug)\b",
        message="Remove console.log statements from production code.",
        fix_suggestion="Use the Angular Logger service instead.",
    ),
    ReviewRule(
        id="TS004", severity=Severity.WARNING, category="performance",
        description="Missing OnPush change detection strategy",
        pattern=r"@Component\({(?!.*changeDetection)[^}]+}\)",
        message="Components should use ChangeDetectionStrategy.OnPush.",
        fix_suggestion="Add `changeDetection: ChangeDetectionStrategy.OnPush` to @Component.",
    ),
]

SECURITY_PATTERNS: list[ReviewRule] = [
    ReviewRule(
        id="SEC001", severity=Severity.ERROR, category="security",
        description="Vault token or JWT hardcoded",
        pattern=r"hvs\.[A-Za-z0-9+/=]{24,}",
        message="Vault token hardcoded in source. Rotate immediately.",
        fix_suggestion="Remove from code; use Vault Agent Injector.",
    ),
    ReviewRule(
        id="SEC002", severity=Severity.ERROR, category="security",
        description="PostgreSQL connection string with embedded password",
        pattern=r"postgres://[^:]+:[^@]{4,}@",
        message="DB password in connection string. Use Vault-injected credentials.",
        fix_suggestion="Use Vault PKI / dynamic secrets for DB creds.",
    ),
    ReviewRule(
        id="SEC003", severity=Severity.WARNING, category="security",
        description="Potential SSRF — user-controlled URL passed to HTTP client",
        pattern=r"(?i)httpClient\.(get|post|put|delete)\s*\(\s*\$?[\w]+\s*\+",
        message="Possible SSRF if URL is user-controlled.",
        fix_suggestion="Validate and allowlist the target URL.",
    ),
]

SCORE_WEIGHTS = {
    "coding_standards": 0.25,
    "security": 0.35,
    "architecture": 0.20,
    "test_coverage": 0.15,
    "performance": 0.05,
}


# ── LangGraph state ───────────────────────────────────────────────────────────
class ReviewState(TypedDict):
    project_path: str
    mr_iid: int
    diff: str
    file_paths: list[str]
    findings: Annotated[list[dict], operator.add]
    coverage_delta: float
    architecture_issues: Annotated[list[str], operator.add]
    llm_summary: str
    score: dict
    comment_body: str
    merge_blocked: bool


# ── Pipeline nodes ────────────────────────────────────────────────────────────
async def _fetch_diff(state: ReviewState) -> dict:
    """Fetch MR diff from GitLab API."""
    encoded = state["project_path"].replace("/", "%2F")
    url = f"{settings.gitlab_url}/api/v4/projects/{encoded}/merge_requests/{state['mr_iid']}/diffs"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers={"PRIVATE-TOKEN": settings.gitlab_token})
        r.raise_for_status()
    diffs = r.json()
    file_paths = [d.get("new_path", "") for d in diffs]
    diff_text = "\n".join(
        f"--- {d.get('old_path', '')}\n+++ {d.get('new_path', '')}\n{d.get('diff', '')}"
        for d in diffs
    )
    return {"diff": diff_text[: settings.max_diff_bytes], "file_paths": file_paths}


def _apply_rules(diff: str, rules: list[ReviewRule], file_hint: str = "") -> list[dict]:
    """Apply regex-based rules against the diff, return Finding dicts."""
    findings = []
    lines = diff.split("\n")
    for rule in rules:
        try:
            pattern = re.compile(rule.pattern)
        except re.error:
            continue
        for i, line in enumerate(lines):
            if line.startswith("+") and pattern.search(line):
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        file=file_hint or f"line_{i}",
                        line=i + 1,
                        message=rule.message,
                        fix_suggestion=rule.fix_suggestion,
                        snippet=line[:200],
                    ).__dict__
                )
    return findings


async def _check_coding_standards(state: ReviewState) -> dict:
    """Run static rule checks for C# and TypeScript."""
    all_findings: list[dict] = []
    diff = state["diff"]
    all_findings.extend(_apply_rules(diff, CSHARP_RULES))
    all_findings.extend(_apply_rules(diff, TYPESCRIPT_RULES))
    all_findings.extend(_apply_rules(diff, SECURITY_PATTERNS))
    return {"findings": all_findings}


async def _detect_architecture_drift(state: ReviewState) -> dict:
    """Check for unapproved new dependencies vs. Pipeline Ledger architecture."""
    issues: list[str] = []
    new_pkgs: list[str] = []
    for line in state["diff"].split("\n"):
        if line.startswith("+"):
            if re.search(r'<PackageReference Include="([^"]+)"', line):
                m = re.search(r'<PackageReference Include="([^"]+)"', line)
                if m:
                    new_pkgs.append(m.group(1))
            m = re.search(r'"([^"]+)":\s*"\^?\d', line)
            if m and not m.group(1).startswith("@angular") and not m.group(1).startswith("@"):
                new_pkgs.append(m.group(1))

    if new_pkgs:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{settings.pipeline_ledger_url}/architecture/approved-deps",
                    params={"project": state["project_path"]},
                )
                if r.status_code == 200:
                    approved = set(r.json().get("packages", []))
                    unapproved = [p for p in new_pkgs if p not in approved]
                    for pkg in unapproved:
                        issues.append(
                            f"New dependency `{pkg}` not in approved architecture. "
                            "Get architect approval before merging."
                        )
        except Exception:
            if new_pkgs:
                issues.append(
                    f"New packages detected ({', '.join(new_pkgs[:5])}). "
                    "Could not verify against architecture ledger (unreachable)."
                )
    return {"architecture_issues": issues}


async def _analyse_coverage(state: ReviewState) -> dict:
    """Fetch coverage delta from GitLab MR data (best-effort)."""
    try:
        encoded = state["project_path"].replace("/", "%2F")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{settings.gitlab_url}/api/v4/projects/{encoded}/merge_requests/{state['mr_iid']}",
                headers={"PRIVATE-TOKEN": settings.gitlab_token},
            )
            if r.status_code == 200:
                mr = r.json()
                # GitLab exposes coverage on the MR object (requires CI pipeline)
                base = mr.get("base_pipeline", {}).get("coverage") or 0
                head = mr.get("head_pipeline", {}).get("coverage") or 0
                delta = float(head) - float(base) if base and head else 0.0
                return {"coverage_delta": delta}
    except Exception:
        pass
    return {"coverage_delta": 0.0}


async def _llm_review(state: ReviewState) -> dict:
    """LLM-based holistic review — logic, architecture, and patterns."""
    findings_summary = json.dumps(state["findings"][:20], indent=2)
    arch_issues = "\n".join(state["architecture_issues"])

    prompt = f"""You are an expert code reviewer at AD Ports.

Diff (truncated to 6000 chars):
{state['diff'][:6000]}

Static analysis findings:
{findings_summary}

Architecture issues:
{arch_issues or 'None detected'}

Review for: logic errors, race conditions, missing error handling, performance (N+1, blocking I/O, large payloads), security not already flagged.

Respond in JSON:
{{
  "summary": "2-3 sentence overview",
  "additional_findings": [
    {{"severity": "ERROR|WARNING|INFO", "category": "security|coding_standards|performance|architecture|test_coverage", "message": "...", "fix": "..."}}
  ]
}}"""
    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {"summary": content[:500], "additional_findings": []}

    extra_findings = [
        {
            "rule_id": "LLM",
            "severity": f.get("severity", "WARNING"),
            "category": f.get("category", "general"),
            "file": "review",
            "line": 0,
            "message": f.get("message", ""),
            "fix_suggestion": f.get("fix", ""),
            "snippet": "",
        }
        for f in data.get("additional_findings", [])
    ]
    return {"findings": extra_findings, "llm_summary": data.get("summary", "")}


def _calculate_score(findings: list[dict], coverage_delta: float, architecture_issues: list[str]) -> dict:
    """Calculate reviewability score 0-100 with letter grade."""
    by_category: dict[str, list[dict]] = {cat: [] for cat in SCORE_WEIGHTS}
    for f in findings:
        cat = f.get("category", "coding_standards")
        if cat in by_category:
            by_category[cat].append(f)

    by_category["architecture"].extend(
        [{"severity": "WARNING"}] * len(architecture_issues)
    )
    if coverage_delta < -5:
        by_category["test_coverage"].append({"severity": "WARNING"})
    if coverage_delta < -15:
        by_category["test_coverage"].append({"severity": "ERROR"})

    scores: dict[str, int] = {}
    for cat, weight in SCORE_WEIGHTS.items():
        cat_findings = by_category.get(cat, [])
        critical = sum(1 for f in cat_findings if f.get("severity") in ("ERROR", Severity.ERROR))
        warnings = sum(1 for f in cat_findings if f.get("severity") in ("WARNING", Severity.WARNING))
        max_pts = int(weight * 100)
        deductions = min(critical * 10 + warnings * 3, max_pts)
        scores[cat] = max_pts - deductions

    total = sum(scores.values())
    has_critical = any(f.get("severity") in ("ERROR", Severity.ERROR) for f in findings)
    return {
        "total": total,
        "breakdown": scores,
        "grade": "A" if total >= 90 else "B" if total >= 75 else "C" if total >= 60 else "F",
        "merge_blocked": has_critical or len(architecture_issues) > 0,
    }


async def _build_comment(state: ReviewState) -> dict:
    """Format all findings into a structured GitLab markdown comment."""
    score = _calculate_score(state["findings"], state["coverage_delta"], state["architecture_issues"])

    critical = [f for f in state["findings"] if f.get("severity") in ("ERROR", Severity.ERROR)]
    warnings = [f for f in state["findings"] if f.get("severity") in ("WARNING", Severity.WARNING)]

    breakdown_rows = "\n".join(
        f"| {cat.replace('_', ' ').title()} | {pts}/{int(SCORE_WEIGHTS[cat]*100)} | "
        f"{'✓' if pts == int(SCORE_WEIGHTS[cat]*100) else f'{int(SCORE_WEIGHTS[cat]*100)-pts} pts lost'} |"
        for cat, pts in score["breakdown"].items()
    )

    critical_section = ""
    if critical:
        items = "\n\n".join(
            f"**[{f['rule_id']}] {f['message']}** — `{f['file']}:{f['line']}`\n"
            f"> {f['snippet'][:150]}\n"
            f"✅ Fix: {f['fix_suggestion']}"
            for f in critical[:10]
        )
        critical_section = f"\n---\n### 🔴 CRITICAL — Merge Blocked\n\n{items}\n"

    warning_section = ""
    if warnings:
        items = "\n\n".join(
            f"**[{f['rule_id']}] {f['message']}** — `{f['file']}:{f['line']}`"
            for f in warnings[:10]
        )
        warning_section = f"\n---\n### ⚠️ Warnings ({len(warnings)})\n\n{items}\n"

    arch_section = ""
    if state["architecture_issues"]:
        items = "\n".join(f"- {issue}" for issue in state["architecture_issues"])
        arch_section = f"\n---\n### 🏗️ Architecture Drift\n\n{items}\n"

    block_banner = (
        "\n> ⛔ **Merge is blocked.** Critical issues must be resolved. "
        "Architect can override via Portal.\n"
        if score["merge_blocked"]
        else "\n> ✅ No critical issues. Human reviewer still required for merge.\n"
    )

    body = (
        f"## 🤖 ORBIT AI Portal — Code Review\n\n"
        f"**Reviewability Score: {score['total']}/100 (Grade {score['grade']})**\n"
        f"{block_banner}\n"
        f"| Category | Score | Notes |\n"
        f"|----------|-------|-------|\n"
        f"{breakdown_rows}\n\n"
        f"**Summary:** {state['llm_summary']}\n"
        f"{critical_section}{warning_section}{arch_section}\n"
        f"---\n*Review by AD Ports AI Portal · "
        f"[Override](https://portal.ai.adports.ae) (requires architect role)*"
    )
    return {"comment_body": body, "score": score, "merge_blocked": score["merge_blocked"]}


async def _post_comment(state: ReviewState) -> dict:
    """Post review comment to GitLab MR and optionally block merge."""
    encoded = state["project_path"].replace("/", "%2F")
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{settings.gitlab_url}/api/v4/projects/{encoded}/merge_requests/{state['mr_iid']}/notes",
            headers={"PRIVATE-TOKEN": settings.gitlab_token},
            json={"body": state["comment_body"]},
        )
        if state["merge_blocked"]:
            await client.post(
                f"{settings.gitlab_url}/api/v4/projects/{encoded}"
                f"/merge_requests/{state['mr_iid']}/unapprove",
                headers={"PRIVATE-TOKEN": settings.gitlab_token},
            )

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                settings.pipeline_ledger_url,
                json={
                    "event": "pr_review_completed",
                    "project": state["project_path"],
                    "mr_iid": state["mr_iid"],
                    "score": state["score"],
                    "merge_blocked": state["merge_blocked"],
                    "findings_count": len(state["findings"]),
                },
            )
    except Exception:
        pass
    return {}


def _build_graph():
    g = StateGraph(ReviewState)
    g.add_node("fetch_diff", _fetch_diff)
    g.add_node("check_coding_standards", _check_coding_standards)
    g.add_node("detect_architecture_drift", _detect_architecture_drift)
    g.add_node("analyse_coverage", _analyse_coverage)
    g.add_node("llm_review", _llm_review)
    g.add_node("build_comment", _build_comment)
    g.add_node("post_comment", _post_comment)

    g.set_entry_point("fetch_diff")
    g.add_edge("fetch_diff", "check_coding_standards")
    g.add_edge("fetch_diff", "detect_architecture_drift")
    g.add_edge("fetch_diff", "analyse_coverage")
    g.add_edge("check_coding_standards", "llm_review")
    g.add_edge("detect_architecture_drift", "llm_review")
    g.add_edge("analyse_coverage", "llm_review")
    g.add_edge("llm_review", "build_comment")
    g.add_edge("build_comment", "post_comment")
    g.add_edge("post_comment", END)
    return g.compile()


_graph = _build_graph()

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="ORBIT PR Review Agent", version="2.0.0")
FastAPIInstrumentor.instrument_app(app)


class ReviewRequest(BaseModel):
    project_path: str   # e.g. "adports/dgd-service"
    mr_iid: int


class OverrideRequest(BaseModel):
    project_path: str
    mr_iid: int
    architect_token: str
    reason: str


@app.post("/api/review")
async def review_mr(req: ReviewRequest):
    """Trigger full AI code review for a GitLab MR."""
    state = ReviewState(
        project_path=req.project_path,
        mr_iid=req.mr_iid,
        diff="",
        file_paths=[],
        findings=[],
        coverage_delta=0.0,
        architecture_issues=[],
        llm_summary="",
        score={},
        comment_body="",
        merge_blocked=False,
    )
    result = await _graph.ainvoke(state)
    return {
        "score": result["score"],
        "merge_blocked": result["merge_blocked"],
        "findings_count": len(result["findings"]),
        "comment_posted": True,
    }


@app.post("/api/review/override")
async def override_merge_gate(req: OverrideRequest):
    """Architect override: unblock merge gate with reason recorded in Ledger."""
    encoded = req.project_path.replace("/", "%2F")
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{settings.gitlab_url}/api/v4/projects/{encoded}"
            f"/merge_requests/{req.mr_iid}/approve",
            headers={"PRIVATE-TOKEN": req.architect_token},
        )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                settings.pipeline_ledger_url,
                json={
                    "event": "merge_gate_override",
                    "project": req.project_path,
                    "mr_iid": req.mr_iid,
                    "reason": req.reason,
                },
            )
    except Exception:
        pass
    return {"status": "override_applied", "mr_iid": req.mr_iid}


@app.get("/api/review/rules")
async def list_rules():
    """Return all configured review rules."""
    all_rules = CSHARP_RULES + TYPESCRIPT_RULES + SECURITY_PATTERNS
    return [
        {"id": r.id, "severity": r.severity, "category": r.category, "description": r.description}
        for r in all_rules
    ]


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
