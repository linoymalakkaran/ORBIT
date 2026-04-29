---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend", "devops"]
---

# API Design Guidelines

## Versioning

- All APIs are versioned with URI prefix: `/api/v1/`, `/api/v2/`
- New breaking changes require a new major version; non-breaking additions are backwards-compatible
- Deprecated versions emit `Deprecation` and `Sunset` response headers
- Minimum support window per version: 12 months after sunset announcement

## REST Conventions

- Resource names: **plural nouns** (`/projects`, `/artifacts`, `/skills`)
- Identifiers: UUIDs in path (`/projects/{projectId}`)
- Query parameters: `camelCase` for filtering, sorting, pagination
- Standard pagination: `?page=1&pageSize=20`; response includes `totalCount`, `page`, `pageSize`
- Do not nest resources more than 2 levels deep

## HTTP Methods

| Intent | Method | Success Code |
|---|---|---|
| Create | POST | 201 Created |
| Read single | GET | 200 OK |
| Read list | GET | 200 OK |
| Full replace | PUT | 200 OK |
| Partial update | PATCH | 200 OK |
| Delete | DELETE | 204 No Content |
| Async action | POST `/actions/` | 202 Accepted + `Location` header |

## Error Responses

All errors use [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807):

```json
{
  "type": "https://orbit.adports.ae/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Field 'name' is required",
  "traceId": "00-abc123-def456-00",
  "errors": { "name": ["The name field is required."] }
}
```

Standard error codes: `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`,
`404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`, `429 Too Many Requests`, `500 Internal Server Error`

## Security Headers

Every response must include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'self'`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

## OpenAPI / Documentation

- Every endpoint must have an OpenAPI 3.1 spec entry
- Use schema `$ref` — never inline complex schemas
- Include `operationId` (camelCase), `summary`, `description`, and example request/response
- Security scheme: `bearerAuth` (JWT from Keycloak) on all non-public endpoints

## Rate Limiting

- Default: 100 req/min per user, 1000 req/min per service account (Kong `rate-limiting` plugin)
- AI-generation endpoints: 10 req/min per user
- Return `429 Too Many Requests` with `Retry-After` header
