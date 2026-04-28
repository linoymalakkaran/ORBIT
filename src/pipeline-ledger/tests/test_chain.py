"""Tests for ledger chain verification logic."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models import LedgerEntry


def _make_entry(prev_hash: str = "") -> LedgerEntry:
    e = LedgerEntry(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        event_type="test.event",
        occurred_at=datetime.now(timezone.utc),
        prev_hash=prev_hash,
    )
    e.entry_hash = e.compute_hash()
    return e


def test_chain_hash_changes_when_content_changes():
    e1 = _make_entry()
    e2 = _make_entry()
    assert e1.entry_hash != e2.entry_hash


def test_chain_prev_hash_links():
    e1 = _make_entry("")
    e2 = _make_entry(e1.entry_hash)
    assert e2.prev_hash == e1.entry_hash


def test_tampered_entry_detected():
    e = _make_entry("")
    original_hash = e.entry_hash
    e.event_type = "tampered.event"
    assert e.compute_hash() != original_hash


def test_empty_chain_prev_hash():
    e = _make_entry("")
    assert e.prev_hash == ""
