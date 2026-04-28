# External References — Phase 02: Identity & Authorization

> Official documentation, RFCs, and third-party resources referenced by Phase 02.

---

## Keycloak

| Resource | URL | Version |
|----------|-----|---------|
| Official Documentation | https://www.keycloak.org/documentation | 25.x |
| Server Administration Guide | https://www.keycloak.org/docs/latest/server_admin/ | 25.x |
| Securing Applications (OIDC) | https://www.keycloak.org/docs/latest/securing_apps/ | 25.x |
| Keycloak REST API | https://www.keycloak.org/docs-api/25.0/rest-api/ | 25.x |
| Realm Export/Import | https://www.keycloak.org/docs/latest/server_admin/#admin-cli | 25.x |
| Helm Chart | https://github.com/bitnami/charts/tree/main/bitnami/keycloak | latest |

## OpenFGA

| Resource | URL | Notes |
|----------|-----|-------|
| Official Documentation | https://openfga.dev/docs | |
| ReBAC Concepts (Relations) | https://openfga.dev/docs/concepts | |
| OpenFGA DSL Reference | https://openfga.dev/docs/configuration-language | |
| .NET SDK | https://github.com/openfga/dotnet-sdk | |
| OpenFGA Playground | https://play.fga.dev | For testing authorization models |

## Standards & RFCs

| Resource | URL |
|----------|-----|
| OAuth 2.0 (RFC 6749) | https://datatracker.ietf.org/doc/html/rfc6749 |
| OpenID Connect Core 1.0 | https://openid.net/specs/openid-connect-core-1_0.html |
| JWT (RFC 7519) | https://datatracker.ietf.org/doc/html/rfc7519 |
| JWK (RFC 7517) | https://datatracker.ietf.org/doc/html/rfc7517 |
| PKCE (RFC 7636) | https://datatracker.ietf.org/doc/html/rfc7636 |

## .NET Packages

| Package | NuGet URL | Used For |
|---------|-----------|---------|
| `Microsoft.AspNetCore.Authentication.JwtBearer` | https://www.nuget.org/packages/Microsoft.AspNetCore.Authentication.JwtBearer | JWT validation |
| `OpenFga.Sdk` | https://www.nuget.org/packages/OpenFga.Sdk | OpenFGA .NET client |
| `Keycloak.AuthServices.Authentication` | https://www.nuget.org/packages/Keycloak.AuthServices.Authentication | Keycloak .NET integration |

---

*External References — Phase 02 — AD Ports AI Portal*
