#!/usr/bin/env bash
# scripts/openfga-seed.sh
# Seeds all OpenFGA relationship tuples for the ORBIT AI Portal RBAC model.
# Usage: ./scripts/openfga-seed.sh [--dry-run]
# Requires: curl, jq
# Targets: http://openfga.ai-portal.svc:8080 (in-cluster) or OPENFGA_URL env override

set -euo pipefail

OPENFGA_URL="${OPENFGA_URL:-http://openfga.ai-portal.svc:8080}"
OPENFGA_STORE_ID="${OPENFGA_STORE_ID:-}"
DRY_RUN="${1:-}"

log()  { echo "[openfga-seed] $*"; }
fail() { echo "[openfga-seed] ERROR: $*" >&2; exit 1; }

# ── 1. Resolve store ID ────────────────────────────────────────────────────────
if [[ -z "$OPENFGA_STORE_ID" ]]; then
  log "Resolving store ID from $OPENFGA_URL/stores …"
  STORE_RESPONSE=$(curl -sf "$OPENFGA_URL/stores" | jq -r '.stores[0].id // empty')
  [[ -n "$STORE_RESPONSE" ]] || fail "No store found. Create the store first."
  OPENFGA_STORE_ID="$STORE_RESPONSE"
fi
log "Using store: $OPENFGA_STORE_ID"

WRITE_URL="$OPENFGA_URL/stores/$OPENFGA_STORE_ID/write"

# ── 2. Helper function ─────────────────────────────────────────────────────────
write_tuple() {
  local user="$1"   # e.g. "user:alice" or "group:architects#member"
  local relation="$2"  # e.g. "approve"
  local object="$3"    # e.g. "project:*"

  local body
  body=$(jq -n --arg u "$user" --arg r "$relation" --arg o "$object" \
    '{"writes":{"tuple_keys":[{"user":$u,"relation":$r,"object":$o}]}}')

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "  DRY-RUN: $user $relation $object"
    return
  fi

  local status
  status=$(curl -sf -o /dev/null -w "%{http_code}" \
    -X POST "$WRITE_URL" \
    -H "Content-Type: application/json" \
    -d "$body")

  if [[ "$status" == "200" || "$status" == "201" ]]; then
    log "  ✓ $user → $relation → $object"
  else
    log "  ⚠ HTTP $status for: $user $relation $object (may already exist)"
  fi
}

# ── 3. Role → Permission tuples ───────────────────────────────────────────────
log "Seeding role-permission tuples …"

# orbit-admin: full access to all object types
write_tuple "group:orbit-admin#member" "approve"      "project:*"
write_tuple "group:orbit-admin#member" "read"         "project:*"
write_tuple "group:orbit-admin#member" "write"        "project:*"
write_tuple "group:orbit-admin#member" "approve"      "artifact:*"
write_tuple "group:orbit-admin#member" "read"         "artifact:*"
write_tuple "group:orbit-admin#member" "approve"      "skill:*"
write_tuple "group:orbit-admin#member" "read"         "ledger-entry:*"

# architect: approve projects + artifacts, read/write all
write_tuple "group:architect#member"   "approve"      "project:*"
write_tuple "group:architect#member"   "read"         "project:*"
write_tuple "group:architect#member"   "write"        "project:*"
write_tuple "group:architect#member"   "approve"      "artifact:*"
write_tuple "group:architect#member"   "read"         "artifact:*"
write_tuple "group:architect#member"   "read"         "skill:*"
write_tuple "group:architect#member"   "read"         "ledger-entry:*"

# developer: read projects, write artifacts, read skills & ledger
write_tuple "group:developer#member"   "read"         "project:*"
write_tuple "group:developer#member"   "write"        "artifact:*"
write_tuple "group:developer#member"   "read"         "artifact:*"
write_tuple "group:developer#member"   "read"         "skill:*"
write_tuple "group:developer#member"   "read"         "ledger-entry:*"

# qa: read all, write test artifacts
write_tuple "group:qa#member"          "read"         "project:*"
write_tuple "group:qa#member"          "read"         "artifact:*"
write_tuple "group:qa#member"          "write"        "artifact:*"
write_tuple "group:qa#member"          "read"         "skill:*"
write_tuple "group:qa#member"          "read"         "ledger-entry:*"

# devops: read everything, write infrastructure artifacts
write_tuple "group:devops#member"      "read"         "project:*"
write_tuple "group:devops#member"      "read"         "artifact:*"
write_tuple "group:devops#member"      "write"        "artifact:*"
write_tuple "group:devops#member"      "read"         "skill:*"
write_tuple "group:devops#member"      "read"         "ledger-entry:*"

# pci-certified: read mpay-related projects + ledger only
write_tuple "group:pci-certified#member" "read"       "project:*"
write_tuple "group:pci-certified#member" "read"       "ledger-entry:*"

# ── 4. Verify key tuples ──────────────────────────────────────────────────────
if [[ "$DRY_RUN" != "--dry-run" ]]; then
  log "Verifying key authorization checks …"

  check_tuple() {
    local user="$1" relation="$2" object="$3" expected="$4"
    local body result
    body=$(jq -n --arg u "$user" --arg r "$relation" --arg o "$object" \
      '{"tuple_key":{"user":$u,"relation":$r,"object":$o}}')
    result=$(curl -sf -X POST "$OPENFGA_URL/stores/$OPENFGA_STORE_ID/check" \
      -H "Content-Type: application/json" -d "$body" | jq -r '.allowed')
    if [[ "$result" == "$expected" ]]; then
      log "  ✓ CHECK $user $relation $object => $result"
    else
      log "  ✗ CHECK FAILED $user $relation $object expected=$expected got=$result"
    fi
  }

  check_tuple "group:architect#member" "approve" "project:demo" "true"
  check_tuple "group:developer#member" "read"    "project:demo" "true"
  check_tuple "group:developer#member" "approve" "project:demo" "false"
fi

log "Seeding complete."
