"""The API, the browser and the contract must agree on the same bytes: shared/eip712.vectors.json."""
import json
import pathlib

import pytest
from eth_account import Account

from app.integrations.arc import eip712

VECTORS = pathlib.Path(__file__).resolve().parents[1] / "shared/eip712.vectors.json"


@pytest.fixture(scope="module")
def vectors() -> dict:
    if not VECTORS.exists():
        pytest.skip("run scripts/export_shared.py first")
    return json.loads(VECTORS.read_text())


def test_the_committed_vectors_still_sign_the_same(vectors: dict):
    for vector in vectors["vectors"]:
        signed = Account.sign_message(
            __import__("eth_account.messages", fromlist=["encode_typed_data"]).encode_typed_data(full_message=vector["typed_data"]),
            private_key=vectors["private_key"])
        assert "0x" + bytes(signed.signature).hex() == vector["signature"], vector["name"]
        assert "0x" + bytes(signed.message_hash).hex() == vector["digest"], vector["name"]


def test_struct_hash_is_the_authorization_hash(vectors: dict):
    authorization = next(v for v in vectors["vectors"] if v["name"] == "Authorization")
    assert eip712.struct_hash(authorization["typed_data"]) == authorization["struct_hash"]
    assert len(authorization["struct_hash"]) == 66


def test_recover_returns_the_signer(vectors: dict):
    for vector in vectors["vectors"]:
        assert eip712.recover(vector["typed_data"], vector["signature"]) == vectors["address"].lower()


def test_a_signature_for_other_data_does_not_recover(vectors: dict):
    authorization = next(v for v in vectors["vectors"] if v["name"] == "Authorization")
    tampered = json.loads(json.dumps(authorization["typed_data"]))
    tampered["message"]["maxAmount"] = 999_999_999
    assert eip712.recover(tampered, authorization["signature"]) != vectors["address"].lower()


def test_client_view_sends_large_numbers_as_strings():
    typed = eip712.authorization_typed_data("0x" + "22" * 32, "0x" + "11" * 20, "0x" + "33" * 20, 100_000_000,
                                            "0x" + "44" * 32, 1_757_707_200)
    assert eip712.for_client(typed)["message"]["maxAmount"] == "100000000"
    assert eip712.for_client(typed)["message"]["expiresAt"] == 1_757_707_200


def test_the_domain_is_the_one_the_contract_uses():
    domain = eip712.domain()
    assert domain["name"] == "Intentra" and domain["version"] == "1"
    assert domain["chainId"] == 5042002
