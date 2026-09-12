"""The canonical IntentraEscrow interface.

The ABI is vendored from `intentra-monorepo/contracts/exports/intentra-contracts.ts`, which the contracts team
publishes. Nothing here is hand-written: if the contract changes, re-copy the export and the tests will tell us
whether anything the backend calls or decodes has moved.
"""
import json
import pathlib

_ABI_PATH = pathlib.Path(__file__).resolve().parents[3] / "shared" / "abi" / "IntentraEscrow.json"
ESCROW_ABI = json.loads(_ABI_PATH.read_text())

# The calls the backend builds for a wallet, or sends with the arbitrator key.
CUSTOMER_CALLS = ("createIntent", "fundIntent", "raiseDispute", "executeWithSignatures", "escalateAppeal")
ARBITRATOR_CALLS = ("submitAIProposal", "executeWithSignatures", "executeAbandonment")

# The events the watcher decodes, in lifecycle order.
EVENT_NAMES = ["IntentCreated", "IntentFunded", "DisputeRaised", "AIProposalSubmitted", "AppealEscalated",
               "IntentResolved", "AbandonmentExecuted"]

ERC20_ABI = [
    {"type": "function", "name": "approve", "stateMutability": "nonpayable",
     "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"type": "function", "name": "allowance", "stateMutability": "view",
     "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "balanceOf", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
]
ERC20_APPROVE_ABI = ERC20_ABI          # kept for the shared export script
