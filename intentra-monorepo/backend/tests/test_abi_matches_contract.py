"""The ABI the backend decodes with must match the contract that will actually be deployed.

The compiled artifact is not committed, so these skip unless `forge build` has been run in contracts/.
They are the guard against the quietest failure in the system: a contract whose events or arguments drifted
from `shared/abi/IntentraEscrow.json`, which the watcher would decode into silence.
"""
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPILED = ROOT / "contracts/out/IntentraEscrow.sol/IntentraEscrow.json"
SHARED = ROOT / "shared/abi/IntentraEscrow.json"
DOCUMENTED_CALLS = {"fund", "anchorEvidence", "submit", "release", "openDispute", "resolve", "claimRefund"}


def signature(entry: dict) -> str:
    return f"{entry['type']}:{entry.get('name', '')}({','.join(i['type'] for i in entry.get('inputs', []))})"


@pytest.fixture(scope="module")
def compiled() -> list[dict]:
    if not COMPILED.exists():
        pytest.skip("run `forge build` in contracts/ first")
    return json.loads(COMPILED.read_text())["abi"]


@pytest.fixture(scope="module")
def shared() -> list[dict]:
    return json.loads(SHARED.read_text())


def test_every_call_the_backend_makes_exists_on_the_contract(compiled, shared):
    have = {signature(e) for e in compiled if e["type"] == "function"}
    want = {signature(e) for e in shared if e["type"] == "function"}
    assert want <= have, f"the contract does not expose {sorted(want - have)}"


def test_every_event_the_watcher_decodes_exists_on_the_contract(compiled, shared):
    have = {signature(e) for e in compiled if e["type"] == "event"}
    want = {signature(e) for e in shared if e["type"] == "event"}
    assert want <= have, f"the contract does not emit {sorted(want - have)}"


def test_the_indexed_fields_agree(compiled, shared):
    """Topics are decoded by position: an indexed flag that differs breaks the watcher without an error."""
    by_name = {e["name"]: e for e in compiled if e["type"] == "event"}
    for event in (e for e in shared if e["type"] == "event"):
        theirs = by_name[event["name"]]
        assert [(i["name"], i["type"], i["indexed"]) for i in event["inputs"]] == \
               [(i["name"], i["type"], i["indexed"]) for i in theirs["inputs"]], f"{event['name']} inputs differ"


def test_the_contract_moves_money_only_through_the_documented_calls(compiled):
    """A state-changing function the backend has never heard of is a hole in the story it tells."""
    mutating = {e["name"] for e in compiled if e["type"] == "function"
                and e.get("stateMutability") not in ("view", "pure")}
    assert mutating == DOCUMENTED_CALLS, f"undocumented state-changing functions: {sorted(mutating - DOCUMENTED_CALLS)}"


def test_the_contract_cannot_receive_bare_value(compiled):
    """No payable fallback or receive: the escrow holds USDC, never native currency."""
    assert not [e for e in compiled if e["type"] in ("receive", "fallback")]
    assert not [e for e in compiled if e.get("stateMutability") == "payable"]
