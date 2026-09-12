"""Canonical JSON and the five hashes everything else depends on (schematics §4.4)."""
import json
import uuid

import pytest
from sqlmodel import SQLModel  # noqa: F401  — registers the models used below

from app.domains.audit import service as audit
from app.core.json import jsonable, utc_iso
from app.core.hashing import (ZERO_HASH, audit_hash, canonical_json, complaint_hash, deliverable_hash, keccak_hex,
                                outcome_hash, scope_hash, sha256_hex)
from app.domains.audit.models import AuditEvent

SCOPE = {"rooms": 2, "coats": 2, "paint_included": True, "checklist": ["bedroom_1", "bedroom_2"]}


def test_canonical_json_sorts_keys_and_keeps_utf8():
    assert canonical_json({"b": 1, "a": "₦"}) == b'{"a":"\xe2\x82\xa6","b":1}'


def test_canonical_json_is_order_independent():
    assert canonical_json({"a": 1, "b": [1, 2]}) == canonical_json({"b": [1, 2], "a": 1})


@pytest.mark.parametrize("payload", [1.5, {"a": 1.0}, {"a": {"b": [0.1]}}, [2.5]])
def test_floats_are_refused_in_hashed_payloads(payload):
    with pytest.raises(TypeError):
        canonical_json(payload)


def test_scope_hash_changes_when_the_scope_changes():
    other = {**SCOPE, "rooms": 3}
    assert scope_hash(SCOPE) != scope_hash(other)
    assert scope_hash(SCOPE) == keccak_hex(canonical_json(SCOPE))
    assert len(scope_hash(SCOPE)) == 66


def test_deliverable_hash_does_not_depend_on_upload_order():
    a, b = sha256_hex(b"photo-1"), sha256_hex(b"photo-2")
    assert deliverable_hash([a, b]) == deliverable_hash([b, a])
    assert deliverable_hash([a]) != deliverable_hash([a, b])


def test_complaint_hash_covers_every_field():
    base = ("0x" + "22" * 32, "INCOMPLETE", "Second bedroom has one coat", [sha256_hex(b"p")])
    assert complaint_hash(*base) == complaint_hash(*base)
    assert complaint_hash(*base) != complaint_hash(base[0], "DAMAGE", base[2], base[3])
    assert complaint_hash(*base) != complaint_hash(base[0], base[1], "something else", base[3])


def test_outcome_hash_covers_the_whole_proposal():
    args = ("0x" + "22" * 32, str(uuid.uuid4()), "SPLIT_70_30", 7000, [sha256_hex(b"p")], "because", "m", "v1")
    assert outcome_hash(*args) == outcome_hash(*args)
    changed = list(args)
    changed[3] = 5000
    assert outcome_hash(*args) != outcome_hash(*changed)


def _chain(count: int) -> list[AuditEvent]:
    tx_id, prev, rows = str(uuid.uuid4()), ZERO_HASH, []
    for seq in range(1, count + 1):
        payload = {"n": seq}
        created = utc_iso()
        row = {"transaction_id": tx_id, "seq": seq, "actor": "system:test", "event": "NOTE", "from_state": "CREATED",
               "to_state": "CREATED", "payload": payload, "created_at": created}
        digest = audit_hash(prev, row)
        rows.append(AuditEvent(transaction_id=uuid.UUID(tx_id), seq=seq, actor="system:test", event="NOTE",
                               from_state="CREATED", to_state="CREATED", payload=payload, prev_hash=prev,
                               hash=digest, created_at=created))
        prev = digest
    return rows


def test_an_untouched_audit_chain_verifies():
    result = audit.verify_chain(_chain(5))
    assert result["verified"] is True and result["checked"] == 5


def test_editing_one_row_breaks_the_chain():
    rows = _chain(5)
    rows[2].payload = {"n": 99}
    result = audit.verify_chain(rows)
    assert result["verified"] is False and result["first_broken_seq"] == 3


def test_removing_a_row_breaks_the_chain():
    rows = _chain(5)
    del rows[1]
    assert audit.verify_chain(rows)["verified"] is False


def test_jsonable_keeps_hashes_stable_by_stringifying_floats():
    assert jsonable({"confidence": 0.78}) == {"confidence": "0.78"}
    canonical_json(jsonable({"confidence": 0.78}))     # must not raise
