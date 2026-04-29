---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend"]
---

# C# Coding Standards

## CS001 — Naming Conventions

- Classes, interfaces, methods, properties: **PascalCase**
- Private fields: `_camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Avoid abbreviations; prefer full descriptive names
- Interfaces must be prefixed with `I` (e.g. `IProjectRepository`)

## CS002 — Null Safety

- Enable `<Nullable>enable</Nullable>` in all `.csproj` files
- Use `ArgumentNullException.ThrowIfNull(param)` for public method guards
- Never suppress nullable warnings with `!` unless you have a proof comment
- Use `is null` / `is not null` instead of `== null` / `!= null`

## CS003 — SOLID Principles

- Each class must have a single responsibility (SRP)
- Depend on interfaces, not implementations (DIP)
- Inject dependencies via constructor only — no service locator pattern
- Keep constructors free of logic; use factories where initialisation is complex

## CS004 — Async Guidelines

- All I/O methods must be `async Task` or `async Task<T>`; no `.Result` or `.Wait()`
- Pass `CancellationToken` through all async call chains
- Use `ConfigureAwait(false)` in library code
- Suffix async methods with `Async` (e.g. `GetProjectAsync`)

## CS005 — Exception Handling

- Only catch specific exceptions; never `catch (Exception ex) {}` without re-throwing or logging
- Use custom domain exceptions derived from `DomainException` (not `ApplicationException`)
- Log at the boundary (API layer) — never swallow exceptions in domain/application layers
- Do not use exceptions for control flow

## CS006 — Code Organisation

- One public type per file; file name must match type name
- Use `file`-scoped namespaces (`namespace Foo;`)
- Organise using directives alphabetically; remove unused usings
- Maximum method length: 50 lines; maximum class length: 300 lines
- All public API surface must have XML doc comments
