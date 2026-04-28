# Phase 03 — Portal Backend API (CQRS .NET)

## Summary

Implement the full Portal Backend API — all the CQRS handlers, REST endpoints, and background services that the Portal UI and external clients (CLI, IDE MCPs) depend on. By end of this phase, the Portal API supports project lifecycle management, artifact versioning, user management, and stub endpoints for agents (implemented fully in later phases).

---

## Objectives

1. Implement all Project management CRUD (create, list, get, update, archive).
2. Implement Artifact management (upload, version, list, compare diffs).
3. Implement Approval workflow API (request review, approve, reject, request-changes).
4. Implement User + Team management.
5. Implement Ledger query API (query events by project, stage, actor, date).
6. Implement shared project context API (read/write context turns with Redis).
7. Implement Portal admin API (skill library, MCP registry stubs).
8. Wire all commands/queries to Pipeline Ledger recording.
9. Implement full REST API with OpenAPI documentation.
10. Deploy to TKG (on-prem Tanzu) with health checks, auth middleware, OTEL.

---

## Prerequisites

- Phase 02 complete (schema, auth, skeleton).
- OpenFGA model deployed and tuples writable.
- Redis cluster running.

---

## Duration

**3 weeks**

**Squad:** Core Squad (2 senior .NET engineers + 1 full-stack)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Project CRUD API | Integration tests pass for create/list/get/update |
| D2 | Artifact versioning API | Upload, version, hash verify, cold-store pointer |
| D3 | Approval workflow API | Full approve/reject/request-changes flow with signature |
| D4 | User + Team API | Add/remove team members; role assignment |
| D5 | Ledger query API | Query by project, stage, actor, date; returns typed events |
| D6 | Shared context API | Read/write context turns; Redis TTL; OpenFGA gating |
| D7 | Admin API stubs | Skill library, MCP registry (stubs returning 501) |
| D8 | OpenAPI spec | Swagger UI at `/swagger`; spec exported to `docs/api/` |
| D9 | Deployed to TKG | `kubectl get pods -n ai-portal-core` shows Running |
| D10 | CI/CD pipeline | GitLab/Azure DevOps pipeline: build → test → SAST → deploy |

---

## API Endpoint Reference

### Projects

```
GET     /api/projects                        List projects (with pagination, filters)
POST    /api/projects                        Create project
GET     /api/projects/{id}                   Get project by ID
PATCH   /api/projects/{id}                   Update project metadata
DELETE  /api/projects/{id}                   Archive project (soft delete)
GET     /api/projects/{id}/team              Get team members
POST    /api/projects/{id}/team              Add team member
DELETE  /api/projects/{id}/team/{userId}     Remove team member
```

### Artifacts

```
GET     /api/projects/{id}/artifacts                           List artifacts
POST    /api/projects/{id}/artifacts                           Upload new artifact (multipart)
GET     /api/projects/{id}/artifacts/{artifactId}              Get artifact metadata
GET     /api/projects/{id}/artifacts/{artifactId}/download     Download artifact content
GET     /api/projects/{id}/artifacts/{artifactId}/versions     List all versions
GET     /api/projects/{id}/artifacts/{artifactId}/diff         Diff against previous version
```

### Approvals

```
GET     /api/projects/{id}/stages/{stage}/approval             Get current review status
POST    /api/projects/{id}/stages/{stage}/approval/approve     Approve stage artifacts
POST    /api/projects/{id}/stages/{stage}/approval/reject      Reject with reason
POST    /api/projects/{id}/stages/{stage}/approval/request-changes  Request changes with comments
GET     /api/projects/{id}/stages/{stage}/approval/history     Full approval history
```

### Ledger

```
GET     /api/ledger/projects/{id}/events                Query ledger events for project
GET     /api/ledger/projects/{id}/stages/{stage}        All events in a specific stage
GET     /api/ledger/actors/{userId}/events              All events by actor
GET     /api/ledger/search                              Full-text search across all projects
GET     /api/ledger/projects/{id}/chain-verify         Verify cryptographic chain integrity
```

### Shared Project Context

```
GET     /api/projects/{id}/context                     Get current context session
POST    /api/projects/{id}/context/turns               Add a context turn
GET     /api/projects/{id}/context/turns               List context turns (paginated)
GET     /api/projects/{id}/context/decisions           List major decisions in context
DELETE  /api/projects/{id}/context                     Clear context (admin only)
```

### Health & Admin

```
GET     /health/live          Liveness probe
GET     /health/ready         Readiness probe (checks Postgres, Redis, Keycloak)
GET     /api/admin/skills     List skills in fabric (stub → 501 until Phase 07)
GET     /api/admin/mcps       List MCP servers (stub → 501 until Phase 08)
```

---

## Approval Workflow State Machine

```
Pending Review
    │ [POST /approval/approve]  ──→  Approved ──→ [delegates to agents]
    │ [POST /approval/reject]   ──→  Rejected ──→ [stops pipeline]
    └ [POST /approval/request-changes] ──→ Changes Requested
                                              │ [orchestrator revises]
                                              └──→ Pending Review (new version)
```

Each transition:
1. Records a `LedgerEvent` (type = `ApprovalDecision`) with actor, artifact hashes, decision, comment.
2. For `Approved`: emits a Kafka `portal.stage.transitions` event triggering next stage.
3. For `Approved` with two-person-rule: checks that two distinct approvers have signed (OpenFGA check).

---

## Shared Context — Redis Schema

```
Key: context:{projectId}:session:{sessionId}:meta
  → Hash: { created_at, creator_id, status: active|archived }

Key: context:{projectId}:session:{sessionId}:turns
  → List of JSON: { turn_id, user_id, role, timestamp, type: prompt|response|decision, content, artifact_refs[] }

Key: context:{projectId}:active_session
  → String: {sessionId}  (TTL: 7 days)

Key: context:{projectId}:decisions
  → Sorted set by timestamp: { decision_text, session_id, turn_id, artifact_refs[] }
```

Access control: every context read/write is gated by an OpenFGA `CanRead`/`CanWrite` check on the project.

---

## Pipeline Ledger Recording

Every API endpoint that produces a state change records a ledger event:

```csharp
public class RecordLedgerEventBehaviour<TRequest, TResponse>(ILedgerService ledger)
    : IPipelineBehavior<TRequest, TResponse>
    where TRequest : ILedgerableCommand
{
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken ct)
    {
        var response = await next();
        await ledger.RecordAsync(new LedgerEvent(
            StreamId: $"project-{request.ProjectId}",
            EventType: request.LedgerEventType,
            ProjectId: request.ProjectId,
            ActorId: request.ActorId,
            EventData: request.ToLedgerData(response)
        ), ct);
        return response;
    }
}
```

---

## Step-by-Step Execution Plan

### Week 1: Project + Artifact APIs

- [ ] Implement `CreateProjectCommand` + handler + validator.
- [ ] Implement `ListProjectsQuery` + handler (with paging, filters by status/program).
- [ ] Implement `GetProjectByIdQuery` + handler.
- [ ] Implement `UpdateProjectCommand` + handler.
- [ ] Implement `UploadArtifactCommand` + handler (multipart upload → MinIO S3 bucket → hash → DB record).
- [ ] Implement `ListArtifactsQuery` + `GetArtifactVersionsQuery`.
- [ ] Write integration tests for all above (Testcontainers for Postgres).

### Week 2: Approval + Ledger + Context APIs

- [ ] Implement `ApproveStageCommand` + handler (signature generation + OpenFGA two-person check).
- [ ] Implement `RejectStageCommand` + `RequestChangesCommand`.
- [ ] Implement `GetApprovalHistoryQuery`.
- [ ] Implement `QueryLedgerEventsQuery` + handler (reads from Postgres ledger index).
- [ ] Implement `VerifyChainIntegrityQuery` (re-hashes chain from first event).
- [ ] Implement `AddContextTurnCommand` + `GetContextSessionQuery` (Redis operations).
- [ ] Write integration tests for approval workflow state machine.

### Week 3: Polish + CI + Deploy

- [ ] Implement User + Team management endpoints.
- [ ] Add Swagger/OpenAPI configuration.
- [ ] Add problem details responses for all errors.
- [ ] Write GitLab CI pipeline YAML for: build → test → SonarQube → container build → push Harbor → deploy to TKG.
- [ ] Configure Kong ingress for `/api/` path.
- [ ] Load test: 50 concurrent users, verify p99 < 200ms.
- [ ] Export OpenAPI spec and publish to Docusaurus stub.

---

## Gate Criterion

- All D1–D10 deliverables pass acceptance criteria.
- ≥50 integration tests green.
- SonarQube quality gate passes.
- Load test: p99 latency < 200ms at 50 concurrent users.
- Pipeline Ledger records events for every state-changing operation.
- Deployed to TKG `ai-portal-core` namespace.

---

*Phase 03 — Portal Backend API — AI Portal — v1.0*
