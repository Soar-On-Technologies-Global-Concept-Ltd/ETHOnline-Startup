# shared/abi

`IntentraEscrow.json` is vendored verbatim from `intentra-monorepo/contracts/exports/IntentraEscrow.abi.json`,
which the contracts team publishes. The escrow itself lives in `intentra-monorepo/contracts/`; the Solidity that
used to sit under `backend/contracts/` was superseded by it and has been deleted.

## Live on Arc testnet (chain 5042002)

| | |
|---|---|
| IntentraEscrow | `0xeF3a099CC877F6e274b037847A6ee44C4d62648D` |
| USDC (6 dp, verified on-chain) | `0xFa5a5744898B71c93fF80F179d95184864143190` |
| Deploy block | `61719028` |
| `aiArbitrator` | `0x0376AAc07Ad725E01357B1725B5ceC61aE10473c` |
| `owner` (human oracle) | `0x8f4e2891eCFfD5e39BD8F87d01442F6027062e55` |
| `appealFee` | 0.01 ETH · `APPEAL_TIMELOCK` 48 h · `ABANDONMENT_TIMEOUT` 14 d |

**`RESOLVER_PRIVATE_KEY` must be the key for `aiArbitrator` above.** Any other key can neither submit an AI
proposal nor provide the arbitrator half of a 2-of-3 resolution.

Checked against the deployed contract: its `domainSeparator()` equals the one the backend builds, and its
`RESOLVE_INTENT_TYPEHASH` equals `keccak256("ResolveIntent(uint256 intentId,uint256 customerAmount,"
`"uint256 providerAmount)")` — so signatures collected by the API verify on-chain.
