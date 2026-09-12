"""Writes the interfaces the backend, the frontend and the subgraph must agree on:
shared/abi/IntentraEscrow.json, shared/eip712.json and shared/eip712.vectors.json (a fixed key and its expected signature).

    python scripts/export_shared.py
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

os.environ.setdefault("ESCROW_ADDRESS", "0x00000000000000000000000000000000000E5C70")
os.environ.setdefault("ENV", "dev")

from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402

from app.integrations.arc.abi import ERC20_APPROVE_ABI, ESCROW_ABI  # noqa: E402
from app.integrations.arc.eip712 import (AUTHORIZATION_TYPE, DOMAIN_TYPE, RESOLUTION_TYPE,  # noqa: E402
                                            authorization_typed_data, resolution_typed_data)

ROOT = pathlib.Path(__file__).resolve().parents[1]
VECTOR_KEY = "0x" + "11" * 32          # test key, never used anywhere real
TX_KEY = "0x" + "22" * 32
SCOPE_HASH = "0x" + "33" * 32
OUTCOME_HASH = "0x" + "44" * 32


def write(path: pathlib.Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


def main() -> None:
    write(ROOT / "shared/abi/IntentraEscrow.json", ESCROW_ABI)
    write(ROOT / "shared/abi/ERC20.json", ERC20_APPROVE_ABI)
    write(ROOT / "subgraph/intentra-arc/abis/IntentraEscrow.json", ESCROW_ABI)
    write(ROOT / "shared/eip712.json", {
        "domain": {"name": "Intentra", "version": "1", "chainId": 5042002, "verifyingContract": "<ESCROW_ADDRESS>"},
        "types": {"EIP712Domain": DOMAIN_TYPE, "Authorization": AUTHORIZATION_TYPE, "Resolution": RESOLUTION_TYPE},
    })

    account = Account.from_key(VECTOR_KEY)
    authorization = authorization_typed_data(TX_KEY, account.address, "0x" + "55" * 20, 100_000_000, SCOPE_HASH, 1_757_707_200)
    resolution = resolution_typed_data(TX_KEY, 7000, OUTCOME_HASH)
    vectors = {"note": "Sign these with the private key below; the web and API test suites check the same bytes.",
               "private_key": VECTOR_KEY, "address": account.address, "vectors": []}
    for name, typed in (("Authorization", authorization), ("Resolution", resolution)):
        signable = encode_typed_data(full_message=typed)
        signed = Account.sign_message(signable, private_key=VECTOR_KEY)
        vectors["vectors"].append({"name": name, "typed_data": typed,
                                   "struct_hash": "0x" + bytes(signable.body).hex(),
                                   "digest": "0x" + bytes(signed.message_hash).hex(),
                                   "signature": "0x" + bytes(signed.signature).hex()})
    write(ROOT / "shared/eip712.vectors.json", vectors)


if __name__ == "__main__":
    main()
