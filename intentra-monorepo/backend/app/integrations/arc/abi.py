"""IntentraEscrow interface the backend codes against (schematics §12). The contracts owner's ABI must match."""
def _fn(name, inputs, mut="nonpayable"):
    return {"type": "function", "name": name, "stateMutability": mut, "inputs": [{"name": n, "type": t} for n, t in inputs], "outputs": []}


def _ev(name, inputs):
    return {"type": "event", "name": name, "anonymous": False,
            "inputs": [{"name": n, "type": t, "indexed": i} for n, t, i in inputs]}


ESCROW_ABI = [
    _fn("fund", [("txKey", "bytes32"), ("provider", "address"), ("amount", "uint256"), ("authorizationHash", "bytes32"),
                 ("disputeWindow", "uint64"), ("expiresAt", "uint64")]),
    _fn("anchorEvidence", [("txKey", "bytes32"), ("evidenceHash", "bytes32")]),
    _fn("submit", [("txKey", "bytes32"), ("deliverableHash", "bytes32")]),
    _fn("release", [("txKey", "bytes32")]),
    _fn("openDispute", [("txKey", "bytes32"), ("complaintHash", "bytes32")]),
    _fn("resolve", [("txKey", "bytes32"), ("providerBps", "uint16"), ("outcomeHash", "bytes32"), ("sigCustomer", "bytes"), ("sigProvider", "bytes")]),
    _fn("claimRefund", [("txKey", "bytes32")]),
    _ev("JobFunded", [("txKey", "bytes32", True), ("customer", "address", True), ("provider", "address", True), ("amount", "uint256", False),
                      ("authorizationHash", "bytes32", False), ("disputeWindow", "uint64", False), ("expiresAt", "uint64", False)]),
    _ev("EvidenceAnchored", [("txKey", "bytes32", True), ("evidenceHash", "bytes32", False)]),
    _ev("Submitted", [("txKey", "bytes32", True), ("deliverableHash", "bytes32", False), ("releaseAfter", "uint64", False)]),
    _ev("DisputeOpened", [("txKey", "bytes32", True), ("complaintHash", "bytes32", False)]),
    _ev("Released", [("txKey", "bytes32", True), ("amount", "uint256", False)]),
    _ev("Resolved", [("txKey", "bytes32", True), ("toProvider", "uint256", False), ("toCustomer", "uint256", False), ("outcomeHash", "bytes32", False)]),
    _ev("Refunded", [("txKey", "bytes32", True), ("amount", "uint256", False)]),
]

ERC20_APPROVE_ABI = [{"type": "function", "name": "approve", "stateMutability": "nonpayable",
                      "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
                      "outputs": [{"name": "", "type": "bool"}]}]

EVENT_NAMES = ["JobFunded", "EvidenceAnchored", "Submitted", "DisputeOpened", "Released", "Resolved", "Refunded"]
