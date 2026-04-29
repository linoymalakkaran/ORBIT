---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend"]
---

# MPay Coding Standards

MPay services must comply with all general coding standards plus these additional rules.

## Data Handling

- **Never** log, print, or serialise raw PAN (Primary Account Number), CVV, or expiry date
- Use `[Sensitive]` attribute on DTO properties containing card data — triggers automatic redaction in logging middleware
- Tokenisation: replace PAN with `payment_token` (non-sensitive reference) immediately on receipt
- Use `ReadOnlySpan<char>` or `SecureString` when handling card data in memory; zero-out after use

```csharp
// ✓ Correct
var token = await _mpayGateway.TokeniseAsync(pan);
_logger.LogInformation("Payment tokenised: {Token}", token); // safe

// ✗ Forbidden
_logger.LogInformation("Payment received for card: {PAN}", pan); // NEVER
```

## Error Messages

- Never expose card data in error responses or exception messages
- Use generic error codes: `PAYMENT_DECLINED`, `CARD_INVALID`, `INSUFFICIENT_FUNDS`
- Do not reveal gateway timeout details to end users

## Service Communication

- MPay services must only communicate with the MPay gateway via the approved internal endpoint defined in Vault at `secret/data/orbit/mpay/gateway_url`
- All outbound connections use a dedicated `HttpClient` named `MPayGateway` with certificate pinning configured
- Retry policy: max 3 retries with exponential backoff; do not retry on `400`, `402`, `422`

## Idempotency

- All payment creation endpoints must accept an `Idempotency-Key` header (UUID)
- Store idempotency key + response in Redis with 24-hour TTL
- Return identical response for duplicate requests (HTTP 200, not 201)

```csharp
// Always check idempotency before processing
var cached = await _cache.GetAsync<PaymentResult>($"mpay:idem:{idempotencyKey}");
if (cached is not null) return cached;
```

## Testing

- Use Luhn-valid fake PANs for testing (e.g. `4111111111111111`)
- Never use real card numbers in test fixtures, even masked ones
- WireMock stubs must be used for all MPay gateway calls in integration tests
- Test both successful and declined transaction scenarios

## Deployment

- MPay services deploy to namespace `mpay-cde` — not `ai-portal`
- ArgoCD application: `mpay-cde` app in `gitops/apps/`
- Requires `pci-certified` Keycloak role to approve production deployments
- Gate-3 checklist includes PCI-DSS code review sign-off by certified team member
