# Mezo MUSD Proof Desk

**An independent, read-only MUSD/MEZO on-chain proof desk.** AI-assisted and operated by one real human economic owner. Original design adapted from our public TapeOut Upgrade Guard; no affiliation with Mezo.

Live dashboard: https://livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/

Source: https://github.com/livastic-vm2-primary-20260911/mezo-musd-proof-desk

## What it actually does

- Reads chain ID 31612, block number/hash/time, contract bytecode fingerprints via public HTTPS read-only Mezo Mainnet RPC.
- Pins EVERY contract read to the same named block and re-checks its block hash before finishing. Stops on the wrong network, absent source, unexpected token pair, invalid ABI, missing code, RPC errors, or changing block.
- Reads ERC-20 totalSupply and decimals for published MUSD and MEZO contracts; reads token0/token1/getReserves and ERC-20 MUSD balanceOf for the three official MUSD/BTC, MUSD/mUSDC, MUSD/mUSDT basic pools.
- Renders independent timestamped JSON in a website with exact source links; browser NEVER calls blockchain RPC or wallet APIs.
- Compares two chronologically pinned captures for contract SHA256 fingerprint changes, displayed supply and three MUSD reserve values. No RPC calls in comparison mode.

**Official source of truth:**

- Token addresses: https://mezo.org/docs/users/resources/contracts-reference
- Pools and fee architecture: https://mezo.org/docs/developers/features/mezo-pools
- Chain ID, network, public RPC: https://testnet.mezo.org/docs/users/getting-started/connect

**Evidence limitations:** Measured pool reserves are NOT a stablecoin backing audit, executable swap quote, USD price, collateral solvency check, peg proof, bridge inventory, DeFi liquidation safety statement, APY or investment recommendation. The three published pools are not all possible markets. Cross-chain token supplies may contain locked and minted representations and must not be summed as independent backing. MEZO totalSupply is not dollar market capitalization. Bytecode SHA256 identity is NOT a code audit or security guarantee. This evidence is a historical snapshot, not a real-time oracle.

## Reproduce (Python 3.11+ standard library, no key/seed)

    python3 -B -m unittest discover -s tests -q
    python3 -B mezo_proof.py snapshot --out evidence/my_pinned_mezo.json
    python3 -B mezo_proof.py compare --left evidence/20261023_mezo_first_pinned.json --right evidence/20261023_mezo_second_pinned.json --out evidence/my_diff.json
    python3 -m http.server 8000 --directory docs

Open http://localhost:8000. Original public snapshot evidence under evidence/ is immutable through exclusive-create output; the site uses only the committed docs/latest.json. RPC default https://mezo-mainnet.boar.network from Mezo first-party docs. Any optional alternate HTTPS RPC is still constrained to chain 31612 and prohibits credentials/URL query. NO automatic retries, provider-switches, private keys, wallet connection, user funds or transactions.

**Strict RPC allowlist:** eth_chainId, eth_blockNumber, eth_getBlockByNumber, eth_getCode, eth_getStorageAt, eth_call. Hard cap 40 calls/run. No signing, gas, approval, swap, bridge, borrowing, lending, deposits, transfers or public-chain penetration testing.

28 offline regression tests exercise wrong-chain fail-before-read, token-pair source validation, pinned hash reorg, malformed ABI, decimals limits, absent code, unsafe RPC method refusal, response integrity, chronological changes and no-clobber JSON writes. Offline tests do not establish safety of any production contract.

## Original project, buyer terms and contest status

The original live read-only MUSD/MEZO integration is offered as an open MIT-licensed demo. An optional bespoke human-reviewed two-block comparison memo is **seller quoted at 19 Circle Base USDC only as a price proposal**, not a sale, existing client approval, or completed payment. Before starting a paid pilot the independent buyer and one actual South Korea-based human owner must agree in writing on price, AI assistance, scope, source-only access, accepted chain/token/public payee, delivery/revisions, IP, tax/fees and cancellation/refund. No wallet signature or private contract access is required. Contact onecursor1@gmail.com. **Confirmed paid buyers = 0; sales = 0.**

Official Mezo Buildathon (https://mezo.org/blog/mezo-buildathon-is-underway/) permits extensions to existing projects. Wave 1 ends October 26, 2026. Rewards advertised as 7,000 USD equivalent of MEZO token across two waves, NOT cash earned, not an audited liquid price or guaranteed payout. An AKINDO authenticated original one-owner application with truthful eligibility and sponsor confirmation is still required. This GitHub project is **not itself a contest entry**, merely a legitimate original candidate. Do not fabricate nationality, legal ID, age, GitHub account, wallet signature or participation.

© 2026 One Cursor, original human-operated AI-assisted research. MIT License.
