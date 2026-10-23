# Mezo MUSD Proof Desk — optional Wave 1 project notes (not submitted)

Official organizer: https://mezo.org/blog/mezo-buildathon-is-underway/
Official platform: https://app.akindo.io/wave-hacks/OVOO0gdrVU8379D10
Wave 1 deadline: October 26, 2026 (official AKINDO shows Oct27 00:00 local).
Reward: judged POINT-BASED fraction of $2,000 USD equivalent in MEZO for Wave 1, but KYB before receiving tokens and tax/KYC documentation required. Not revenue until won and independently settled.

## Accurate application fields ready for original real human to review

Project: Mezo MUSD Proof Desk
Category (3-5 words): MUSD DeFi reserve discovery
Track: 2 — Access & Distribution for MUSD/MEZO
Tagline: A chain-pinned public inventory of on-chain MUSD/MEZO supply and MUSD reserves in Mezo's three documented basic pools, with reproducible contract code fingerprints.
How: Python 3.11+ standard library, HTTPS eth_chainId, eth_getBlockByNumber, eth_getCode, eth_call to official chain31612. All calls pinned to one block. Read ERC20 totalSupply, decimals, balanceOf; pool token0/token1/getReserves; SHA256 runtime bytecode; fail closed mismatched pair or changed block hash. Serve only static committed verified evidence to client.
Target users: Solo Bitcoin DeFi builders, risk-research operators and release QA teams who need public inventory with reproducibility before selecting an actual swap or liquidity route. Not customers of a managed portfolio or investment advisory.
Stack: Python standard library, unittest (28 offline PASS), Mezo Mainnet JSON-RPC, ERC20 and Aerodrome-style Mezo pools, JavaScript/CSS static site and GitHub Pages.
Source: https://github.com/livastic-vm2-primary-20260911/mezo-musd-proof-desk
Working public deployment: https://livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/
Demo video (104 seconds, captioned silent): https://livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/demo.mp4
Exact mainnet proof: /latest.json on that website, plus both historic JSON under evidence/.
Product status: **New original product published during this buildathon, fully functioning browser dashboard and pinned mainnet read-only integration.** No onchain transactions, no user wallet connection or deposits; if judges REQUIRE state-changing onchain deployment, eligibility is not established and must not be misrepresented.
Evidence: MUSD/MEZO runtime and ERC20 supply, BTC/MUSD and MUSD/mUSDC and MUSD/mUSDT onchain reserves; code fingerprints unchanged across two sampled blocks.
Honest limitation: NO market price or TWAP, proof of backing, collateral risk, wallet ownership, APY or solvency claim. This is discovery/inventory evidence, not DEX execution.
Business use: publicly free data, optional independently commissioned 19 native Base CircleUSDC human-reviewed pinned two-block release comparison after budget and AI/IP/payee negotiation. **No independent paid buyer contract or sale.**
Next milestones: (1) a trusted second provider's source timestamp independently validated without bypassing any existing RPC refusal, (2) chain/account-integrated historical proofs and optional noncustodial alerts, (3) user testing with actual independent sponsor-approved scope before implementing any write/trade route.
IP: One Cursor original human-operated, AI-assisted, MIT licensed, no Mezo affiliation.
Team: ONE real human economic owner; same one human controls VM1, VM2, VM3, VM5, VM6. No second independent human team member can be inferred from VM count.

## Mandatory verified-person fields not supplied / cannot truthfully auto-fill

- Full legal name: ORIGINAL OWNER MUST PROVIDE OR VERIFY.
- Date of birth or actual 18+ age proof: ORIGINAL OWNER MUST VERIFY.
- Nationality and location: nationality not inferred from Korean residence.
- Telegram handle: OWNER MUST PROVIDE.
- Discord handle / verified Mezo Developer role: OWNER MUST PROVIDE.
- AKINDO original Google/Email account session: NOT SIGNED IN in VM2 Chrome on 2026-10-24.
- Owner legal human ID and eventual KYB/W8-BEN or business documentation: requires lawful original person.
- Confirmation that AKINDO accepts a read-only MUSD-integrated deployed dashboard as a track2 onchain deployment: NOT CONFIRMED.
- Two-minute demo has SILENT CAPTIONS; narration not promised.
- Original actual EVM MetaMask receiving wallet supports Ethereum and Base public 0x4e31...D98E but exact MEZO-token disbursement chain and payout ability still need sponsor verification.

DO NOT submit dummy personal details, pretend an AI agent has a human legal identity, join another team/alias under the same owner, enter from another VM account to avoid restriction, sign a wallet, or claim prize. A public repo and video are NOT an accepted contest submission or awarded cash.
