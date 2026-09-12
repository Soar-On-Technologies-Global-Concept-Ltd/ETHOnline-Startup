# intentra-arc

Indexes `IntentraEscrow` on Arc so trust scores come from what happened on-chain, not from rows Intentra could edit.

```bash
npm install
# point the manifest at the deployed escrow first
sed -i "s/0x0000000000000000000000000000000000000000/$ESCROW_ADDRESS/;s/startBlock: 0/startBlock: $ESCROW_DEPLOY_BLOCK/" subgraph.yaml
npm run codegen && npm run build
npm run deploy      # Subgraph Studio; put the query URL in GRAPH_QUERY_URL
```

`abis/IntentraEscrow.json` is written by `python scripts/export_shared.py`, so the backend, the frontend and this
subgraph always decode the same events.
