# Glossary — AD Ports AI Portal

> Definitions for all domain-specific, AD Ports-specific, and Portal-specific terms used throughout the implementation plan.

---

## A

**AC (Acceptance Criterion)** — A testable condition that must be satisfied for a user story to be considered complete. ID format: `AC-{DOMAIN}-{NNN}` e.g. `AC-DGD-042`.

**ACS (Access Control System)** — AD Ports' physical and logical access control system. Integrated via the LCS MCP server.

**Activity (Temporal)** — A single unit of work in a Temporal workflow. Activities can be retried independently and emit heartbeats for long-running operations.

**Agent** — An AI subsystem in the Portal that performs a specific role (e.g. Backend Specialist Agent, QA Agent). Agents are LangGraph state machines backed by LiteLLM.

**ArgoCD** — GitOps continuous delivery tool for Kubernetes. The Portal uses ArgoCD to deploy all services from the GitLab repository. No `kubectl apply` is used directly.

**AKS (Azure Kubernetes Service)** — The managed Kubernetes platform used by AD Ports for all Portal workloads. Version: 1.30.x.

---

## B

**BA (Business Analyst)** — Role responsible for authoring Business Requirements Documents (BRDs) and reviewing generated user stories.

**BRD (Business Requirements Document)** — A document describing business needs for a new service or feature. Uploaded to the Portal as the starting input for the AI pipeline.

**Bounded Context** — A DDD (Domain-Driven Design) term. Each AD Ports service operates within a named bounded context (e.g. `DangerousGoods`, `LicenseAndCertifications`).

**Budget Limit** — The monthly LLM spend cap per project tier. Enforced by `budget-limits.rego` before each LLM call.

---

## C

**Capability Fabric** — The shared knowledge layer of the Portal. Contains skills, specifications, instructions, and standards that all AI agents read before generating code.

**Campaign (Fleet Upgrade)** — A coordinated upgrade of multiple services to a new framework version. Managed by the Fleet Upgrade Agent using Temporal workflows and wave-based rollout.

**CQRS (Command Query Responsibility Segregation)** — The architectural pattern used for all AD Ports backend services. Commands mutate state; queries read state. Implemented with MediatR.

**CRUISE** — AD Ports cruise terminal operations domain. One of the three primary Portal domains alongside DGD and LCS.

---

## D

**DGD (Dangerous Goods Declaration)** — AD Ports' system for managing hazardous cargo declarations required by the IMDG Code and UAE port regulations. The first pilot project for the AI Portal.

**Digital Signature** — A cryptographic signature attached to Pipeline Ledger events for non-repudiation. Signed using the actor's Keycloak X.509 certificate.

**Domain Pack** — A Fabric bundle containing domain-specific skills, specifications, prompts, and glossary terms. Activatable per project. Examples: `dgd-domain-pack`, `lcs-domain-pack`.

---

## E

**Economy Tier (LLM)** — The lowest-cost LLM tier. Uses DeepSeek-V3 or Llama 3.3. Suitable for bulk template-based generation where judgment is not required.

**EventStoreDB** — The append-only event store used as the primary storage for the Pipeline Ledger. Provides per-project streams (`ledger-{projectId}`).

---

## F

**Fabric** — Short for Capability Fabric.

**FastAPI** — The Python web framework used for MCP servers and the Hook Engine.

**Fleet** — The full set of AD Ports services deployed to AKS. The Fleet Upgrade Agent operates across the fleet.

---

## G

**Gate** — An approval checkpoint in the AI pipeline. Gates require explicit human approval before the next stage begins. Enforced by `approval-gate-enforcement.rego`.

**GitOps** — Infrastructure and deployment management via Git commits and pull requests. ArgoCD watches the GitLab repository and reconciles cluster state.

---

## H

**HLD (High-Level Design)** — A technical design document that complements a BRD. Uploaded alongside BRDs to the Portal for architecture-aware code generation.

**Hook Engine** — The OPA-based pre-action enforcement layer. Evaluates every agent action before it executes. Responses include: `allow`, `deny reasons`, `redact fields`, `selected_llm_tier`.

---

## I

**ICD (Interface Control Document)** — A document specifying integration contracts between AD Ports systems. Used by the Orchestrator to identify external dependencies.

**IMDG Code** — International Maritime Dangerous Goods Code. The international standard for transporting hazardous materials by sea. Governs DGD form requirements.

---

## J

**Jira** — The project management tool used by AD Ports development teams. The Portal integrates via `adports-jira-mcp` to create epics and stories automatically.

---

## K

**Keycloak** — The identity and access management platform. All Portal users, service accounts, and agents authenticate via Keycloak 25.

---

## L

**LangGraph** — A Python framework for building stateful, multi-step LLM agent workflows. Used for deterministic, bounded-time orchestration (tasks completing in < 5 min).

**LCS (License & Certification System)** — AD Ports' licensing domain. Manages vessel certifications, permits, and operational licenses.

**Ledger** — Short for Pipeline Ledger.

**LiteLLM** — Provider-agnostic Python LLM gateway. Routes calls to the correct LLM provider based on tier selection from the Hook Engine.

**LLM (Large Language Model)** — AI language model. The Portal uses four tiers: Premium (Claude Sonnet 4), Standard (GPT-4o), Economy (DeepSeek-V3), Sovereign (Llama 3.3 on AKS).

---

## M

**MCP (Model Context Protocol)** — An open standard for exposing tools to AI agents. The Portal exposes 12+ MCP servers, each providing domain-specific tool sets.

**MCP Server** — A FastAPI service implementing the MCP protocol. All AD Ports MCP servers extend `AdPortsMcpBase` and require Keycloak JWT authentication.

**MediatR** — A .NET library implementing the Mediator pattern. Used for CQRS command/query dispatching in all backend services.

**MFE (Micro-Frontend)** — An independently deployable Angular application that composes into the Portal shell via Native Federation.

---

## N

**Native Federation** — Module federation for Angular using native browser ES modules. Used in the Developer Portal shell and all Angular MFEs.

**NESA** — UAE National Electronic Security Authority. Sets cybersecurity standards for government entities in the UAE.

---

## O

**OpenFGA** — Fine-grained authorization service (Relationship-Based Access Control). Every API resource check includes a project-scoped OpenFGA tuple check.

**Orchestrator** — The central coordinator service. Receives tasks from the Portal UI, runs Hook Engine checks, dispatches work to agents, and records all actions to the Pipeline Ledger.

**OPA (Open Policy Agent)** — Policy engine used by the Hook Engine. Evaluates Rego policies to determine allow/deny for every agent action.

---

## P

**Pipeline Ledger** — The append-only, cryptographically-chained audit trail. Every significant AI action creates a `LedgerEvent` with a SHA-256 hash chain.

**Premium Tier (LLM)** — The highest-quality LLM tier. Uses Claude Sonnet 4. Reserved for architecture proposals, code review, and complex judgment tasks.

**PrimeNG** — The Angular component library used for all Portal UI components. Version: 18.x.

**Project** — A unit of work in the Portal. Each project corresponds to one AD Ports service being built or maintained. Projects are isolated by Keycloak realm, Vault path, K8s namespace, and OpenFGA namespace.

---

## R

**Rego** — OPA's declarative policy language. All Hook Engine policies are written in Rego.

**ReBAC (Relationship-Based Access Control)** — The authorization model used by OpenFGA. Access is determined by relationships between entities (users, projects, resources).

---

## S

**Scriban** — A .NET template engine used by the Backend Specialist Agent for boilerplate code generation. Preferred over raw LLM generation for deterministic output.

**Sovereign Tier (LLM)** — The on-premises LLM tier. Uses Llama 3.3 70B on AKS GPU nodes in the UAE region. Required for CLASSIFIED data — no data leaves AD Ports infrastructure.

**Squad** — An autonomous development team in the AD Ports AI Portal programme. Squads: Platform Squad, Delivery Agents Squad, Fabric Squad, Governance Squad, Portal UX Squad.

**Standard Tier (LLM)** — The mid-tier LLM. Uses Azure OpenAI GPT-4o (UAE region). Suitable for general code generation and analysis tasks.

**State Machine** — A LangGraph `StateGraph` that models the steps of an AI orchestration flow as nodes with conditional edges.

---

## T

**Temporal** — A durable workflow execution platform. Used for long-running orchestrations (> 5 min) that require human approval signals, like Fleet Upgrade Campaigns.

**Transloco** — The Angular i18n library used for all Portal text. Supports English and Arabic. All UI text must use Transloco — never raw strings.

**Two-Person Rule** — A governance policy requiring two distinct individuals to approve certain high-risk actions (fleet upgrades to production, production deployments).

---

## V

**Vault** — HashiCorp Vault. All secrets are stored in Vault and injected at runtime via the Vault Agent Injector. Services never store credentials in configuration files.

**vLLM** — An open-source LLM serving engine optimised for throughput and GPU efficiency. Used to self-host Llama 3.3 on AKS GPU nodes for the Sovereign tier.

---

## W

**Wave** — A group of services in a Fleet Upgrade Campaign that are upgraded concurrently. Maximum 5 services per wave. Order: low-risk → medium-risk → high-risk.

**Work Package (WP)** — A discrete unit of AI-implementable work decomposed from a BRD by the Orchestrator. Each WP targets one agent type (backend, frontend, devops, qa).

---

*Glossary — AD Ports AI Portal — Maintained by: Governance Squad — Review Cycle: Per phase completion*
