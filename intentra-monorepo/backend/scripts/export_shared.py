"""Writes the interfaces the backend, the frontend and the subgraph must agree on.

The ABI itself is *not* generated here: it is vendored from `intentra-monorepo/contracts/exports/intentra-contracts.ts`,
which the contracts team owns. This script copies that vendored file where the subgraph needs it and writes the
EIP-712 definitions and signing vectors that both test suites check.

    python scripts/export_shared.py
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

ROOT = pathlib.Path(__file__).resolve().parents[1]
ESCROW = "0xeF3a099CC877F6e274b037847A6ee44C4d62648D"        # live on Arc testnet
USDC = "0xFa5a5744898B71c93fF80F179d95184864143190"
os.environ.setdefault("ESCROW_ADDRESS", ESCROW)
os.environ.setdefault("USDC_ADDRESS", USDC)
os.environ.setdefault("ENV", "dev")

from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402

from app.integrations.arc.eip712 import (AUTHORIZATION_TYPE, DOMAIN_TYPE, RESOLVE_INTENT_TYPE,  # noqa: E402
                                         authorization_typed_data, resolution_typed_data)

VECTOR_KEY = "0x" + "11" * 32          # test key, never used anywhere real
TX_KEY = "0x" + "22" * 32
SCOPE_HASH = "0x" + "33" * 32


def write(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


def main() -> None:
    abi = json.loads((ROOT / "shared/abi/IntentraEscrow.json").read_text())
    write(ROOT / "subgraph/intentra-arc/abis/IntentraEscrow.json", abi)

    write(ROOT / "shared/eip712.json", {
        "note": "ResolveIntent is the contract's own type and must match IntentraEscrow.sol. Authorization is "
                "Intentra's off-chain mandate: the escrow never sees it.",
        "addresses": {"escrow": ESCROW, "usdc": USDC, "chainId": 5042002},
        "domains": {
            "contract": {"name": "IntentraEscrow", "version": "1", "chainId": 5042002, "verifyingContract": ESCROW},
            "mandate": {"name": "Intentra", "version": "1", "chainId": 5042002, "verifyingContract": ESCROW},
        },
        "types": {"EIP712Domain": DOMAIN_TYPE, "Authorization": AUTHORIZATION_TYPE,
                  "ResolveIntent": RESOLVE_INTENT_TYPE},
    })

    account = Account.from_key(VECTOR_KEY)
    vectors = {"note": "Sign these with the private key below; the web and API test suites check the same bytes.",
               "private_key": VECTOR_KEY, "address": account.address, "vectors": []}
    for name, typed in (("Authorization", authorization_typed_data(TX_KEY, account.address, "0x" + "55" * 20,
                                                                   100_000_000, SCOPE_HASH, 1_757_707_200)),
                        ("ResolveIntent", resolution_typed_data(7, 30_000_000, 70_000_000))):
        signable = encode_typed_data(full_message=typed)
        signed = Account.sign_message(signable, private_key=VECTOR_KEY)
        vectors["vectors"].append({"name": name, "typed_data": typed,
                                   "struct_hash": "0x" + bytes(signable.body).hex(),
                                   "digest": "0x" + bytes(signed.message_hash).hex(),
                                   "signature": "0x" + bytes(signed.signature).hex()})
    write(ROOT / "shared/eip712.vectors.json", vectors)


if __name__ == "__main__":
    main()
