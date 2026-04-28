# External References — Complete Technology Stack

## Purpose

Master reference list for all external documentation used across the AI Portal implementation plan. Grouped by component. All URLs verified at time of writing.

---

## Infrastructure (Phase 01)

| Component | Version | Documentation |
|-----------|---------|--------------|
| Azure Kubernetes Service | 1.30.x | https://learn.microsoft.com/en-us/azure/aks/ |
| CloudNativePG (Postgres operator) | 1.23.x | https://cloudnative-pg.io/documentation/1.23/ |
| PostgreSQL | 16 | https://www.postgresql.org/docs/16/ |
| Redis Cluster | 7.2 | https://redis.io/docs/manual/scaling/ |
| Strimzi Kafka | 3.7 | https://strimzi.io/docs/operators/latest/overview.html |
| EventStoreDB | 24.x | https://developers.eventstore.com/server/v24.2/ |
| HashiCorp Vault | 1.17.x | https://developer.hashicorp.com/vault/docs |
| Vault Agent Injector | 1.4.x | https://developer.hashicorp.com/vault/docs/platform/k8s/injector |
| ArgoCD | 2.12.x | https://argo-cd.readthedocs.io/en/stable/ |
| Kong API Gateway | 3.7.x | https://docs.konghq.com/gateway/3.7.x/ |
| KongIngress CRD | 0.12.x | https://docs.konghq.com/kubernetes-ingress-controller/latest/ |
| Pulumi Azure Native | 2.x | https://www.pulumi.com/registry/packages/azure-native/ |
| cert-manager | 1.15.x | https://cert-manager.io/docs/ |

---

## Identity & Authorization (Phases 01–02)

| Component | Version | Documentation |
|-----------|---------|--------------|
| Keycloak | 25.x | https://www.keycloak.org/documentation |
| Keycloak JS adapter | 25.x | https://www.keycloak.org/docs/latest/securing_apps/#_javascript_adapter |
| Keycloak Admin REST API | 25.x | https://www.keycloak.org/docs-api/25.0/rest-api/ |
| OpenFGA | 1.x | https://openfga.dev/docs |
| OpenFGA Authorization Model | — | https://openfga.dev/docs/configuration-language |
| JWT.io debugger | — | https://jwt.io |

---

## Backend Stack (Phases 02–03, 12)

| Component | Version | Documentation |
|-----------|---------|--------------|
| .NET SDK | 9.0 | https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-9/ |
| MediatR | 12.x | https://github.com/jbogard/MediatR/wiki |
| FluentValidation | 11.x | https://docs.fluentvalidation.net/en/latest/ |
| EF Core | 9.x | https://learn.microsoft.com/en-us/ef/core/ |
| EF Core Migrations | 9.x | https://learn.microsoft.com/en-us/ef/core/managing-schemas/migrations/ |
| Npgsql EF Core | 9.x | https://www.npgsql.org/efcore/index.html |
| ASP.NET Core JWT Bearer | 9.x | https://learn.microsoft.com/en-us/aspnet/core/security/authentication/jwt-authn |
| MassTransit | 8.x | https://masstransit.io/documentation |
| Camunda BPMN | 7.x | https://docs.camunda.org/manual/7.21/ |
| Polly | 8.x | https://www.pollydocs.org/ |

---

## Frontend Stack (Phases 04, 13)

| Component | Version | Documentation |
|-----------|---------|--------------|
| Angular | 20.x | https://angular.dev/overview |
| Angular Standalone Components | 20.x | https://angular.dev/guide/components |
| Angular Signals | 20.x | https://angular.dev/guide/signals |
| Nx | 20.x | https://nx.dev/getting-started |
| Native Federation | 2.x | https://www.npmjs.com/package/@angular-architects/native-federation |
| PrimeNG | 18.x | https://primeng.org/installation |
| Tailwind CSS | 3.4.x | https://tailwindcss.com/docs/installation |
| Transloco | 7.x | https://jsverse.github.io/transloco/ |
| Angular Testing Library | 16.x | https://testing-library.com/docs/angular-testing-library/intro/ |
| Playwright (Angular) | 1.46.x | https://playwright.dev/docs/intro |

---

## Observability (Phase 01)

| Component | Version | Documentation |
|-----------|---------|--------------|
| OpenTelemetry .NET | 1.9.x | https://opentelemetry.io/docs/languages/dotnet/ |
| OpenTelemetry Python | 1.26.x | https://opentelemetry.io/docs/languages/python/ |
| Prometheus | 2.53.x | https://prometheus.io/docs/introduction/overview/ |
| Grafana | 11.x | https://grafana.com/docs/grafana/latest/ |
| Grafana Loki | 3.x | https://grafana.com/docs/loki/latest/ |
| Grafana Tempo | 2.5.x | https://grafana.com/docs/tempo/latest/ |
| LangSmith | — | https://docs.smith.langchain.com/ |

---

## AI & Orchestration (Phases 08–10)

| Component | Version | Documentation |
|-----------|---------|--------------|
| LangGraph | 0.2.x | https://langchain-ai.github.io/langgraph/ |
| Temporal.io | 1.24.x | https://docs.temporal.io/ |
| LiteLLM | 1.x | https://docs.litellm.ai/docs/ |
| LiteLLM Proxy | 1.x | https://docs.litellm.ai/docs/proxy/quick_start |
| Model Context Protocol (MCP) | 1.0 | https://modelcontextprotocol.io/introduction |
| Claude Sonnet API | 4.x | https://docs.anthropic.com/en/api/getting-started |
| Azure OpenAI | 2024-10+ | https://learn.microsoft.com/en-us/azure/ai-services/openai/ |
| vLLM | 0.5.x | https://docs.vllm.ai/en/latest/ |
| OPA (Open Policy Agent) | 0.67.x | https://www.openpolicyagent.org/docs/latest/ |

---

## Security Tools (Phases 15, 18, 23)

| Component | Version | Documentation |
|-----------|---------|--------------|
| SonarQube Community | 10.x | https://docs.sonarqube.org/latest/ |
| Checkmarx SAST | 24.x | https://checkmarx.com/resource/documents/en/34965-137477.html |
| Snyk CLI | 1.x | https://docs.snyk.io/snyk-cli |
| Trivy | 0.54.x | https://aquasecurity.github.io/trivy/ |
| GitLeaks | 8.x | https://github.com/zricethezav/gitleaks |
| OWASP Top 10 (2021) | — | https://owasp.org/www-project-top-ten/ |
| NVD (CVE database) | — | https://nvd.nist.gov/developers/vulnerabilities |

---

## Testing (Phases 16–17)

| Component | Version | Documentation |
|-----------|---------|--------------|
| Playwright | 1.46.x | https://playwright.dev/docs/intro |
| Axe-core | 4.10.x | https://github.com/dequelabs/axe-core |
| @axe-core/playwright | 4.10.x | https://www.npmjs.com/package/@axe-core/playwright |
| k6 | 0.53.x | https://k6.io/docs/ |
| Pact | 12.x | https://docs.pact.io/ |
| Testcontainers (.NET) | 3.x | https://dotnet.testcontainers.org/ |
| Postman | — | https://learning.postman.com/docs/introduction/overview/ |
| Newman | 6.x | https://learning.postman.com/docs/collections/using-newman-cli/ |
| WireMock | 3.x | https://wiremock.org/docs/ |
| xUnit | 2.x | https://xunit.net/docs/getting-started/netcore/cmdline |

---

## Regulatory & Standards (Phase 07)

| Standard | Document |
|----------|----------|
| UAE NESA Cybersecurity Framework | https://www.nesa.ae/standards |
| IMDG Code (Dangerous Goods) | https://www.imo.org/en/OurWork/Safety/Pages/DangerousGoods-default.aspx |
| ISO 27001 | https://www.iso.org/iso-27001-information-security.html |
| SOC 2 Type II | https://www.aicpa.org/resources/article/soc-2-reporting-on-an-examination-of-controls |
| WCAG 2.1 AA | https://www.w3.org/TR/WCAG21/ |
| PCI-DSS v4.0 | https://www.pcisecuritystandards.org/document_library/ |
| OpenAPI 3.1 | https://spec.openapis.org/oas/v3.1.0 |
| BPMN 2.0 | https://www.omg.org/spec/BPMN/2.0/ |

---

*shared/external-refs/external-references.md — AI Portal — v1.0*
