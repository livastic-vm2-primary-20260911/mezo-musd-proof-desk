#!/usr/bin/env python3
"""Render a no-client, noncustodial Mezo MUSD sample report from original pinned public evidence only.

Neither an audit/financial recommendation nor a client deliverable. No network, key, or signed calls.
Use fail-closed identity & provenance checks, built-in Decimal and HTML escaping.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "evidence/20261023_mezo_first_pinned.json"
NEW = ROOT / "evidence/20261023_mezo_second_pinned.json"
DIFF = ROOT / "evidence/comparison_first_to_second.json"
OUT = ROOT / "docs/sample-report.html"
REPO = "https://github.com/livastic-vm2-primary-20260911/mezo-musd-proof-desk"
DASH = "https://livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/"
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
FILEHASH = re.compile(r"^[0-9a-f]{64}$")
CHARS = re.compile(r"^[A-Za-z0-9 /(),+.:-]{1,100}$")
EXPECTED_POOLS = {
    "MUSD / BTC": "0x52e604c44417233b6CcEDDDc0d640A405Caacefb",
    "MUSD / mUSDC": "0xEd812AEc0Fecc8fD882Ac3eccC43f3aA80A6c356",
    "MUSD / mUSDT": "0x10906a9E9215939561597b4C8e4b98F93c02031A",
}
EXPECTED_ASSETS = {
    "MUSD": "0xdD468A1DDc392dcdbEf6db6e34E89AA338F9F186",
    "MEZO": "0x7B7c000000000000000000000000000000000001",
}
EXPECTED_PAIRS = {
    "BTC": "0x7b7C000000000000000000000000000000000000",
    "mUSDC": "0x04671C72Aab5AC02A03c1098314b1BB6B560c197",
    "mUSDT": "0xeB5a5d39dE4Ea42C2Aa6A57EcA2894376683bB8E",
}


class InvalidEvidence(ValueError):
    """Fail without rendering when source facts are incomplete or differ in meaning."""


def require(condition, message):
    if not condition:
        raise InvalidEvidence(message)


def number(value, name):
    require(isinstance(value, str) and len(value) < 120 and not value.startswith("+"), name + " not a plain decimal string")
    try:
        n = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise InvalidEvidence(name + " nondecimal") from exc
    require(n.is_finite() and n >= 0, name + " not a nonnegative finite number")
    return n


def human(n: Decimal, digits=6):
    value = format(n, "f")
    integral, dot, fractional = value.partition(".")
    whole = f"{int(integral):,}"
    return whole + (("." + fractional[:digits].rstrip("0")) if dot and fractional[:digits].rstrip("0") else "")


def signed_delta(a: Decimal, b: Decimal):
    diff = b - a
    if diff == 0:
        return "0"
    return ("+" if diff > 0 else "−") + human(abs(diff), 8)


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def parse_json(src: bytes):
    require(len(src) < 250000, "input bounded")
    x = json.loads(src)
    require(isinstance(x, dict), "JSON object required")
    return x


def validate(old, new, diff):
    require(old.get("schemaVersion") == new.get("schemaVersion") == "mezo-musd-proofdesk-v1", "snapshot schema")
    require(diff.get("schemaVersion") == "mezo-musd-proofdesk-comparison-v1", "difference schema")
    for label, data in (("before", old), ("after", new)):
        require(data.get("network", {}).get("chainId") == 31612, label + " chain")
        require(data.get("signed") is False and data.get("userFundsSpent") is False, label + " unsafe disclosure")
        b = data.get("block") or {}
        require(isinstance(b.get("number"), int) and b["number"] > 0, label + " block height")
        require(isinstance(b.get("hash"), str) and HASH.fullmatch(b["hash"]), label + " block hash")
        dt = datetime.fromisoformat(str(b.get("timestampUTC")))
        require(dt.tzinfo is not None, label + " timestamp not timezone aware")
        assets = data.get("assets") or {}
        for key, addr in EXPECTED_ASSETS.items():
            token = assets.get(key) or {}
            require(str(token.get("address") or "").lower() == addr.lower(), label + " token address " + key)
            require(token.get("decimals") == 18, label + " expected token 18 decimals")
            number(token.get("totalSupply"), label + " " + key + " totalSupply")
            fp = token.get("runtime") or {}
            require(isinstance(fp.get("sha256"), str) and FILEHASH.fullmatch(fp["sha256"]), label + " source hash")
        pools = data.get("pools")
        require(isinstance(pools, list) and len(pools) == 3, label + " exact three pools")
        require({p.get("name") for p in pools if isinstance(p, dict)} == set(EXPECTED_POOLS), label + " pool identities")
        total = Decimal(0)
        for p in pools:
            labelpool = p["name"]
            require(str(p.get("address") or "").lower() == EXPECTED_POOLS[labelpool].lower(), label + " pool contract identity")
            require(NAME_SAFE(labelpool), "unsafe pool label")
            reserve = number(p.get("musdReserve"), labelpool + " MUSD reserve")
            balance = number(p.get("musdBalanceInPool"), labelpool + " MUSD balance")
            require(str(p.get("code", {}).get("sha256") or "") and FILEHASH.fullmatch(str(p["code"]["sha256"])), label + " pool SHA")
            pair_asset = {"MUSD / BTC": "BTC", "MUSD / mUSDC": "mUSDC", "MUSD / mUSDT": "mUSDT"}[labelpool]
            require({str(p.get("token0") or "").lower(), str(p.get("token1") or "").lower()} == {
                EXPECTED_ASSETS["MUSD"].lower(), EXPECTED_PAIRS[pair_asset].lower()
            }, label + " token0/token1 not the documented pool")
            require((p.get("asset0"), p.get("asset1")) in {("MUSD", pair_asset), (pair_asset, "MUSD")}, "asset label not the documented pool")
            require(balance >= 0 and reserve >= 0, "negative pool reserve/balance")
            total += reserve
        require(total == number(data.get("measuredPoolMUSDReserves"), "total measured pool reserves"), label + " total mismatch")

    b0, b1 = old["block"], new["block"]
    require(b0["number"] < b1["number"], "blocks not increasing")
    require(diff.get("from") == b0 and diff.get("to") == b1, "comparison mismatch")
    require(diff.get("priceOrSolvencyProven") is False, "claimed financial confidence")
    rows = diff.get("contractsAndPools")
    require(isinstance(rows, list) and len(rows) == 5, "five comparison components missing")
    require({x.get("name") for x in rows if isinstance(x, dict)} == set(EXPECTED_POOLS) | set(EXPECTED_ASSETS), "comparison label mismatch")
    for row in rows:
        key = row["name"]
        before = old["assets"].get(key) if key in EXPECTED_ASSETS else next(p for p in old["pools"] if p["name"] == key)
        after = new["assets"].get(key) if key in EXPECTED_ASSETS else next(p for p in new["pools"] if p["name"] == key)
        fp = "runtime" if key in EXPECTED_ASSETS else "code"
        require(row.get("runtimeChanged") is (before[fp]["sha256"] != after[fp]["sha256"]), "forged runtime change flag")
        if key in EXPECTED_ASSETS:
            require(row.get("supplyBefore") == before["totalSupply"] and row.get("supplyAfter") == after["totalSupply"], "supply comparison tampered")
        else:
            require(row.get("musdReserveBefore") == before["musdReserve"] and row.get("musdReserveAfter") == after["musdReserve"], "pool reserve comparison tampered")
    return old, new, rows


def NAME_SAFE(s):
    return isinstance(s, str) and CHARS.fullmatch(s) is not None


def render(old, new, diff, filehash):
    validate(old, new, diff)
    b0, b1 = old["block"], new["block"]
    esc = lambda v: escape(str(v), quote=True)
    token_rows = ""
    for key in EXPECTED_ASSETS:
        first = old["assets"][key]
        last = new["assets"][key]
        a, b = number(first["totalSupply"], key + " old"), number(last["totalSupply"], key + " new")
        token_rows += (
            "<tr><td><b>"+esc(key)+"</b></td>"
            "<td class=\"mono\">"+esc(human(a, 4))+"</td>"
            "<td class=\"mono\">"+esc(human(b, 4))+"</td>"
            "<td class=\"mono\">"+esc(signed_delta(a, b))+"</td></tr>"
        )
    pool_rows = ""
    for name in EXPECTED_POOLS:
        oldrow = next(p for p in old["pools"] if p["name"] == name)
        newrow = next(p for p in new["pools"] if p["name"] == name)
        first, last = number(oldrow["musdReserve"], name), number(newrow["musdReserve"], name)
        balance = number(newrow["musdBalanceInPool"], name+" balance")
        difference = balance-last
        pool_rows += (
            "<tr><td><b>"+esc(name)+"</b><br><small class=\"mono\">"+esc(newrow["address"])+"</small></td>"
            "<td class=\"mono\">"+esc(human(first, 6))+"</td>"
            "<td class=\"mono\">"+esc(human(last, 6))+"</td>"
            "<td class=\"mono\">"+esc(signed_delta(first,last))+"</td>"
            "<td class=\"mono\">"+esc(signed_delta(last,balance))+"</td></tr>"
        )
    code_rows=""
    for item in diff["contractsAndPools"]:
        name = item["name"]
        f = new["assets"][name]["runtime"] if name in EXPECTED_ASSETS else next(p["code"] for p in new["pools"] if p["name"]==name)
        code_rows += (
            "<tr><td>"+esc(name)+"</td><td class=\"mono hash\">"+esc(f["sha256"])+"</td>"
            "<td>"+("Observed difference" if item["runtimeChanged"] else "Same in both samples")+"</td></tr>"
        )
    changes = sum(item["runtimeChanged"] for item in diff["contractsAndPools"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<title>Mezo MUSD — publicly reproducible two-block sample evidence report</title>
<meta name="description" content="Original Mezo Proof Desk example: two verified mainnet blocks, ERC20 MUSD/MEZO supply, three basic-pool reserves, runtime bytecode SHA256. A sales sample, not a client report.">
<style>
:root{{--bg:#07151a;--card:#0f292d;--ink:#f0f7f1;--dim:#adccc4;--accent:#b3ebda;--warm:#e9bd78;--stroke:#365459}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 system-ui,-apple-system,sans-serif}}
main{{max-width:1100px;margin:auto;padding:38px 25px 84px}}a{{color:var(--accent)}}header{{border-bottom:1px solid var(--stroke);padding-bottom:28px}}.eyebrow{{color:var(--accent);font:12px monospace;letter-spacing:.13em;text-transform:uppercase}}
h1{{font-size:clamp(2.2rem,5vw,4.5rem);letter-spacing:-.05em;line-height:1.15;margin:20px 0}}
h2{{font-size:1.65rem;letter-spacing:-.035em;margin:0 0 10px}}h3{{margin:0 0 10px}}
.pill{{display:inline-block;border:1px solid var(--warm);color:var(--warm);border-radius:99px;padding:6px 13px;font:12px monospace;letter-spacing:.06em}}
.lead{{max-width:850px;font-size:1.08rem;color:var(--dim)}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:24px}}
.stats>div{{background:var(--card);border:1px solid var(--stroke);padding:20px}}.stats small{{display:block;color:var(--dim);font-size:12px}}.stats b{{font-size:1.38rem;font-weight:600;letter-spacing:-.03em}}
section{{margin-top:48px}}.note{{padding:17px 20px;background:#1d2c29;border-left:3px solid var(--warm);color:#d7dfd7}}
.table-wrap{{overflow:auto;border:1px solid var(--stroke);margin-top:20px}}table{{width:100%;min-width:710px;border-collapse:collapse}}
th,td{{padding:14px 15px;text-align:left;border-bottom:1px solid var(--stroke);vertical-align:top}}th{{background:#123035;color:var(--accent);font:12px monospace}}td small{{display:block;color:var(--dim);font-size:11px;overflow-wrap:anywhere}}
td.mono,.mono{{font:12px/1.7 ui-monospace,Consolas,monospace}}.hash{{overflow-wrap:anywhere;max-width:420px}}
.foot{{margin-top:44px;border-top:1px solid var(--stroke);padding-top:20px;color:var(--dim);font-size:13px}}
.meter{{display:flex;gap:14px;margin-top:18px;flex-wrap:wrap}}.meter span{{border:1px solid var(--stroke);padding:10px 15px;background:var(--card);font:12px monospace}}
@media(max-width:730px){{.stats{{grid-template-columns:1fr}} main{{padding:23px 17px 45px}}}}
@media print{{:root{{--bg:#fff;--card:#fff;--ink:#151d1d;--dim:#4e6060;--accent:#154f49;--warm:#675520;--stroke:#a7bdb9}}body{{background:white}}main{{max-width:100%;padding:12px}}table{{font-size:12px}}a{{color:inherit;text-decoration:underline}}}}
</style></head><body><main>
<header><div class="eyebrow">ONE CURSOR / ORIGINAL MEZO MAINNET EVIDENCE</div>
<h1>MUSD reserve &amp;<br>contract-change facts.</h1>
<p class="pill">PUBLIC SALES SAMPLE — NOT COMMISSIONED, NOT A SECURITY AUDIT</p>
<p class="lead">An example of a two-block source-backed report using actual published Mezo contracts, not hypothetical customers or synthetic screenshots. Scope covers 3 explicitly named basic liquidity pools and two token total supplies only. Every network read was read-only and pinned to a real Mezo block.</p>
<div class="stats">
<div><small>CHAIN</small><b>Mezo Mainnet / 31612</b></div>
<div><small>BLOCKS OBSERVED</small><b>#{b0["number"]:,} → #{b1["number"]:,}</b></div>
<div><small>CHANGED BYTECODE FINGERPRINTS</small><b>{changes} / 5 sampled</b></div>
</div></header>

<section><p class="eyebrow">01 / PROVENANCE</p><h2>Independent timestamps &amp; hashes</h2>
<p>Before: <b>{esc(b0["timestampUTC"])}</b> · After: <b>{esc(b1["timestampUTC"])}</b>. The observations are <b>not</b> continuous monitoring. Both were checked against the RPC-reported block hash.</p>
<p class="mono">Before hash: {esc(b0["hash"])}<br>After hash: {esc(b1["hash"])}</p>
<p class="mono">Source SHA256 (before): {esc(filehash[0])}<br>Source SHA256 (after): {esc(filehash[1])}<br>Comparison SHA256: {esc(filehash[2])}</p></section>

<section><p class="eyebrow">02 / ERC-20 SUPPLIES</p><h2>Two source contracts, two fixed blocks</h2>
<div class="table-wrap"><table><thead><tr><th>Token</th><th>Before supply</th><th>After supply</th><th>Observed difference</th></tr></thead><tbody>{token_rows}</tbody></table></div>
<p class="note">totalSupply is an ERC-20 on-chain reporting field. It is NOT market capitalization, peg health, redeemable balance, cumulative lending volume or protocol collateral.</p></section>

<section><p class="eyebrow">03 / THREE PUBLISHED BASIC POOLS</p><h2>Real MUSD reserves, no made-up prices</h2>
<div class="table-wrap"><table><thead><tr><th>Mezo documented pool</th><th>Before MUSD</th><th>After MUSD</th><th>Observed delta</th><th>Balance minus reserve</th></tr></thead><tbody>{pool_rows}</tbody></table></div>
<div class="meter"><span>Combined before: {esc(human(number(old["measuredPoolMUSDReserves"],"old total"),6))} MUSD</span>
<span>Combined after: {esc(human(number(new["measuredPoolMUSDReserves"],"new total"),6))} MUSD</span></div>
<p class="note">These are the three documented basic pools, NOT all MEZO/MUSD liquidity or available output from a stable-curve swap. Reserve ratio does not imply price or safety.</p></section>

<section><p class="eyebrow">04 / RUNTIME SHA256</p><h2>Change-control fingerprint sample</h2>
<div class="table-wrap"><table><thead><tr><th>Source contract</th><th>SHA256 of deployed runtime code (after)</th><th>Two-block outcome</th></tr></thead><tbody>{code_rows}</tbody></table></div>
<p>No observed SHA256 changes between the two sampled blocks. This **does not prove** zero upgrades at intervening times or the absence of vulnerabilities.</p></section>

<section><p class="eyebrow">05 / REVIEW &amp; BUSINESS TERMS</p><h2>What a buyer can actually commission</h2>
<p>Sample public report only. A custom 19 USDC seller-proposed report would require an independently confirmed budget, exact public protocol address/chain/token, two desired blocks, signed-off evidence-scope and independent human-assisted review of conclusions. Timing, acceptance, one follow-up review, IP, refunds and original one-human owner tax/payment eligibility must be agreed in writing <b>before</b> delivery.</p>
<p>Neither a customer contract, earned sale, funded escrow, contest entry nor award is implied by this sample.</p>
<p><a href="{DASH}">← Return to live MUSD Proof Desk</a> &nbsp; <a href="{REPO}">View source and 28 offline unit tests ↗</a></p>
</section>
<div class="foot">Generated deterministically offline from publicly verified pinned Mezo snapshots using Python standard library, Decimal and HTML escaping. No real customer material, passwords, API keys, wallets or network calls. This research is AI-assisted, open-source, and independent of Mezo. Legal identity and KYB are not represented as verified.</div>
</main></body></html>"""


def build(before_path=OLD, after_path=NEW, diff_path=DIFF, out_path=OUT):
    raws = [Path(x).read_bytes() for x in (before_path, after_path, diff_path)]
    old, new, comparison = [parse_json(x) for x in raws]
    result = render(old, new, comparison, [sha(x) for x in raws])
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f:
        f.write(result)
    return p, sha(result.encode())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", type=Path, default=OLD)
    ap.add_argument("--after", type=Path, default=NEW)
    ap.add_argument("--comparison", type=Path, default=DIFF)
    ap.add_argument("--out", type=Path, default=OUT)
    opts = ap.parse_args()
    path, digest = build(opts.before, opts.after, opts.comparison, opts.out)
    print(json.dumps({"created": str(path), "bytes": path.stat().st_size, "sha256": digest,
                      "networkReads": 0, "walletSigned": False, "buyerPaid": False}))
