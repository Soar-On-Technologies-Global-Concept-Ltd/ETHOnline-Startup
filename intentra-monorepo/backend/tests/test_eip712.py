"""The API, the browser and the contract must agree on the same bytes.

`ResolveIntent` is the canonical contract's own type — `executeWithSignatures` recovers signers against it — so the
type string here is checked against the contract's `RESOLVE_INTENT_TYPEHASH` preimage.
"""
import json
import pathlib

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from app.integrations.arc import eip712

VECTORS = pathlib.Path(__file__).resolve().parents[1] / "shared/eip712.vectors.json"
CONTRACT_TYPE_STRING = b"ResolveIntent(uint256 intentId,uint256 customerAmount,uint256 providerAmount)"


@pytest.fixture(scope="module")
def vectors() -> dict:
    if not VECTORS.exists():
        pytest.skip("run scripts/export_shared.py first")
    return json.loads(VECTORS.read_text())


def test_the_resolve_intent_type_matches_the_deployed_contract():
    """If this drifts, executeWithSignatures rejects every signature the backend collects."""
    fields = ",".join(f'{f["type"]} {f["name"]}' for f in eip712.RESOLVE_INTENT_TYPE)
    assert f"ResolveIntent({fields})".encode() == CONTRACT_TYPE_STRING
    assert keccak(CONTRACT_TYPE_STRING).hex() == keccak(f"ResolveIntent({fields})".encode()).hex()


def test_the_contract_domain_is_the_one_the_escrow_builds():
    """IntentraEscrow.sol constructs EIP712("IntentraEscrow", "1")."""
    domain = eip712.contract_domain()
    assert domain["name"] == "IntentraEscrow" and domain["version"] == "1"
    assert domain["chainId"] == 5042002


def test_the_mandate_domain_is_separate_from_the_contract_one():
    """The authorization is Intentra's own record; keeping the domain distinct stops the two being confused."""
    assert eip712.mandate_domain()["name"] == "Intentra"
    assert eip712.mandate_domain()["name"] != eip712.contract_domain()["name"]


def test_the_committed_vectors_still_sign_the_same(vectors: dict):
    for vector in vectors["vectors"]:
        signed = Account.sign_message(encode_typed_data(full_message=vector["typed_data"]),
                                      private_key=vectors["private_key"])
        assert "0x" + bytes(signed.signature).hex() == vector["signature"], vector["name"]
        assert "0x" + bytes(signed.message_hash).hex() == vector["digest"], vector["name"]


def test_recover_returns_the_signer(vectors: dict):
    for vector in vectors["vectors"]:
        assert eip712.recover(vector["typed_data"], vector["signature"]) == vectors["address"].lower()


def test_a_signature_for_other_amounts_does_not_recover(vectors: dict):
    resolution = next(v for v in vectors["vectors"] if v["name"] == "ResolveIntent")
    tampered = json.loads(json.dumps(resolution["typed_data"]))
    tampered["message"]["providerAmount"] = 99_000_000            # the resolver tries to keep more
    assert eip712.recover(tampered, resolution["signature"]) != vectors["address"].lower()


def test_a_signature_for_another_intent_does_not_recover(vectors: dict):
    resolution = next(v for v in vectors["vectors"] if v["name"] == "ResolveIntent")
    tampered = json.loads(json.dumps(resolution["typed_data"]))
    tampered["message"]["intentId"] = 8                           # replayed onto a different job
    assert eip712.recover(tampered, resolution["signature"]) != vectors["address"].lower()


def test_struct_hash_is_stable(vectors: dict):
    authorization = next(v for v in vectors["vectors"] if v["name"] == "Authorization")
    assert eip712.struct_hash(authorization["typed_data"]) == authorization["struct_hash"]
    assert len(authorization["struct_hash"]) == 66


def test_client_view_sends_large_numbers_as_strings():
    typed = eip712.resolution_typed_data(7, 30_000_000, 70_000_000)
    message = eip712.for_client(typed)["message"]
    assert message == {"intentId": "7", "customerAmount": "30000000", "providerAmount": "70000000"}
