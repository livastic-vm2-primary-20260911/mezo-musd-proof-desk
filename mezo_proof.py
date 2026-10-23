#!/usr/bin/env python3
"""Mezo MUSD Proof Desk — strictly read-only, pinning all reads to one block.

Reads official public Mezo MUSD/MEZO contract addresses and three published
MUSD basic pools. NO signing, transactions, gas, approvals, trading, pricing,
APY, escrow, collateral-risk claims, wallet access, RPC retry or fallbacks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

CHAIN_ID = 31612
RPC_URL = "https://mezo-mainnet.boar.network"
HEX = re.compile(r"^0x[0-9a-fA-F]*$")
ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
# https://mezo.org/docs/users/resources/contracts-reference
# https://mezo.org/docs/developers/features/mezo-pools
# https://testnet.mezo.org/docs/users/getting-started/connect
CONTRACTS = {
    "MUSD": "0xdD468A1DDc392dcdbEf6db6e34E89AA338F9F186",
    "MEZO": "0x7B7c000000000000000000000000000000000001",
    "BTC": "0x7b7C000000000000000000000000000000000000",
    "mUSDC": "0x04671C72Aab5AC02A03c1098314b1BB6B560c197",
    "mUSDT": "0xeB5a5d39dE4Ea42C2Aa6A57EcA2894376683bB8E",
}
POOLS = [
    ("MUSD / BTC", "0x52e604c44417233b6CcEDDDc0d640A405Caacefb", "BTC", "volatile"),
    ("MUSD / mUSDC", "0xEd812AEc0Fecc8fD882Ac3eccC43f3aA80A6c356", "mUSDC", "stable"),
    ("MUSD / mUSDT", "0x10906a9E9215939561597b4C8e4b98F93c02031A", "mUSDT", "stable"),
]
IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
SELECTORS = {
    "decimals": "0x313ce567",
    "totalSupply": "0x18160ddd",
    "balanceOf": "0x70a08231",
    "token0": "0x0dfe1681",
    "token1": "0xd21220a7",
    "getReserves": "0x0902f1ac",
}
MAX_RPC = 40
ERRORS = (
    "Point-in-time block evidence, not consensus verification or a full audit.",
    "Pool reserves and MUSD balances are neither USD prices nor collateral backing.",
    "The measured pools are NOT all possible MUSD venues or bridged supplies.",
    "No buy, trade, withdrawal, approval, liquidation, or gas operation is performed.",
    "Prices, pegs, profit, APY, asset custody and user deposits are NOT verified.",
)


class EvidenceError(RuntimeError):
    pass


def decode_hex(value: object, max_bytes: int = 262144) -> bytes:
    if not isinstance(value, str) or not HEX.fullmatch(value) or len(value) % 2:
        raise EvidenceError("invalid or noncanonical hex")
    out = bytes.fromhex(value[2:])
    if len(out) > max_bytes:
        raise EvidenceError("unbounded RPC response")
    return out


def abi_uint(value: object) -> int:
    b = decode_hex(value, max_bytes=32)
    if len(b) != 32:
        raise EvidenceError("expected one ABI uint256")
    return int.from_bytes(b, "big")


def abi_address(value: object) -> str:
    b = decode_hex(value, max_bytes=32)
    if len(b) != 32 or any(b[:12]):
        raise EvidenceError("invalid ABI encoded address")
    return "0x" + b[12:].hex()


def fmt_units(raw: int, decimals: int) -> str:
    if raw < 0 or decimals < 0 or decimals > 36:
        raise EvidenceError("invalid token units")
    return format(Decimal(raw) / (Decimal(10) ** decimals), "f")


def padded_address(value: str) -> str:
    if not ADDR.fullmatch(value):
        raise EvidenceError("invalid address")
    return value[2:].lower().rjust(64, "0")


class RPC:
    def __init__(self, url=RPC_URL, opener=None, timeout=13):
        if not url.startswith("https://") or "@" in url or "#" in url or "?" in url:
            raise EvidenceError("HTTPS RPC URL must be explicit without credentials or query")
        self.url = url
        self.opener = opener or urllib.request.urlopen
        self.timeout = timeout
        self.counter = 0

    def call(self, name: str, args: list):
        if name not in {"eth_chainId", "eth_blockNumber", "eth_getBlockByNumber",
                        "eth_getCode", "eth_getStorageAt", "eth_call"}:
            raise EvidenceError("read-only RPC calls only")
        self.counter += 1
        if self.counter > MAX_RPC:
            raise EvidenceError("hard maximum RPC call count exceeded")
        data = json.dumps({"jsonrpc": "2.0", "id": self.counter,
                           "method": name, "params": args},
                          separators=(",", ":")).encode()
        req = urllib.request.Request(self.url, data=data, method="POST",
                                     headers={"Accept": "application/json",
                                              "Content-Type": "application/json",
                                              "User-Agent": "OneCursor-MezoMUSD-ProofDesk-ReadOnly/0.1"})
        try:
            with self.opener(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise EvidenceError("unexpected RPC HTTP status")
                body = response.read(1000001)
                if len(body) > 1000000:
                    raise EvidenceError("RPC JSON exceeds 1 MB")
                out = json.loads(body)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise EvidenceError("RPC unavailable; no retry: " + type(exc).__name__) from None
        if (not isinstance(out, dict) or
            out.get("id") != self.counter or
            out.get("jsonrpc") != "2.0" or
            "error" in out or "result" not in out):
            raise EvidenceError("inconsistent RPC response; no retry")
        return out["result"]


def block_info(rpc, number: int) -> dict:
    block = rpc.call("eth_getBlockByNumber", [hex(number), False])
    if not isinstance(block, dict) or block.get("number") != hex(number):
        raise EvidenceError("missing or wrong pinned block")
    h = block.get("hash")
    if not isinstance(h, str) or len(decode_hex(h, 32)) != 32:
        raise EvidenceError("invalid pinned block hash")
    ts = block.get("timestamp")
    if not isinstance(ts, str) or not HEX.fullmatch(ts):
        raise EvidenceError("invalid block timestamp")
    dt = datetime.fromtimestamp(int(ts, 16), timezone.utc)
    return {"number": number, "hash": h.lower(), "timestampUTC": dt.isoformat(timespec="seconds")}


def read_code(rpc, addr, tag):
    code = decode_hex(rpc.call("eth_getCode", [addr, tag]))
    if not code:
        raise EvidenceError("expected deployed contract bytecode at documented address")
    return {"bytes": len(code), "sha256": hashlib.sha256(code).hexdigest()}


def eth_uint(rpc, addr, selector, tag):
    return abi_uint(rpc.call("eth_call", [{"to": addr, "data": selector}, tag]))


def eth_address(rpc, addr, selector, tag):
    return abi_address(rpc.call("eth_call", [{"to": addr, "data": selector}, tag]))


def balances(rpc, token, holder, block):
    data = SELECTORS["balanceOf"] + padded_address(holder)
    return eth_uint(rpc, token, data, block)


def read_reserves(rpc, pool, tag):
    data = decode_hex(rpc.call("eth_call", [{"to": pool, "data": SELECTORS["getReserves"]}, tag]), 96)
    if len(data) != 96:
        raise EvidenceError("expected 3 reserve words from official basic pool")
    return [int.from_bytes(data[i:i + 32], "big") for i in (0, 32, 64)]


def snapshot(rpc) -> dict:
    chain = rpc.call("eth_chainId", [])
    if not isinstance(chain, str) or not HEX.fullmatch(chain) or int(chain, 16) != CHAIN_ID:
        raise EvidenceError("wrong chain; refusing all contract calls")
    latest = rpc.call("eth_blockNumber", [])
    if not isinstance(latest, str) or not HEX.fullmatch(latest):
        raise EvidenceError("invalid head number")
    number = int(latest, 16)
    if number <= 0:
        raise EvidenceError("invalid chain height")
    block = block_info(rpc, number)
    tag = hex(number)

    decimals = {}
    for key in ("MUSD", "MEZO", "mUSDC", "mUSDT"):
        dec = eth_uint(rpc, CONTRACTS[key], SELECTORS["decimals"], tag)
        if not 0 <= dec <= 36:
            raise EvidenceError("unexpected token decimals")
        decimals[key] = dec
    # Mezo native BTC is a chain asset, not an ERC-20, and never called as one.
    decimals["BTC"] = 18
    musd_supply = eth_uint(rpc, CONTRACTS["MUSD"], SELECTORS["totalSupply"], tag)
    mezo_supply = eth_uint(rpc, CONTRACTS["MEZO"], SELECTORS["totalSupply"], tag)
    code = {k: read_code(rpc, CONTRACTS[k], tag) for k in ("MUSD", "MEZO")}

    pools = []
    total_musd = 0
    for name, addr, paired_asset, market_kind in POOLS:
        token0 = eth_address(rpc, addr, SELECTORS["token0"], tag)
        token1 = eth_address(rpc, addr, SELECTORS["token1"], tag)
        expected = {CONTRACTS["MUSD"].lower(), CONTRACTS[paired_asset].lower()}
        if token0 == token1 or {token0, token1} != expected:
            raise EvidenceError("official pool token pair changed; manual review required")
        reserve0, reserve1, last_time = read_reserves(rpc, addr, tag)
        musd_index = 0 if token0 == CONTRACTS["MUSD"].lower() else 1
        pool_balance = balances(rpc, CONTRACTS["MUSD"], addr, tag)
        musd_reserve = (reserve0, reserve1)[musd_index]
        total_musd += musd_reserve
        pools.append({
            "name": name, "kind": market_kind,
            "address": addr, "code": read_code(rpc, addr, tag),
            "token0": token0, "token1": token1,
            "asset0": "MUSD" if musd_index == 0 else paired_asset,
            "asset1": "MUSD" if musd_index == 1 else paired_asset,
            "reserve0Raw": str(reserve0), "reserve1Raw": str(reserve1),
            "reserve0": fmt_units(reserve0, decimals["MUSD" if musd_index == 0 else paired_asset]),
            "reserve1": fmt_units(reserve1, decimals["MUSD" if musd_index == 1 else paired_asset]),
            "musdReserve": fmt_units(musd_reserve, decimals["MUSD"]),
            "musdBalanceInPool": fmt_units(pool_balance, decimals["MUSD"]),
            "reserveTimestampUnix": last_time,
            "reserveBalanceDifference": fmt_units(pool_balance - musd_reserve, decimals["MUSD"]) if pool_balance >= musd_reserve else "-" + fmt_units(musd_reserve - pool_balance, decimals["MUSD"]),
        })

    end = block_info(rpc, number)
    if end["hash"] != block["hash"]:
        raise EvidenceError("pinned block hash changed during snapshot")
    return {
        "schemaVersion": "mezo-musd-proofdesk-v1",
        "generatedUTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "network": {"chainId": CHAIN_ID, "name": "Mezo Mainnet",
                    "rpcURL": rpc.url, "gasAsset": "BTC"},
        "block": block,
        "assets": {
            "MUSD": {"address": CONTRACTS["MUSD"], "decimals": decimals["MUSD"],
                     "totalSupply": fmt_units(musd_supply, decimals["MUSD"]),
                     "totalSupplyRaw": str(musd_supply), "runtime": code["MUSD"]},
            "MEZO": {"address": CONTRACTS["MEZO"], "decimals": decimals["MEZO"],
                     "totalSupply": fmt_units(mezo_supply, decimals["MEZO"]),
                     "totalSupplyRaw": str(mezo_supply), "runtime": code["MEZO"]},
        },
        "pools": pools,
        "measuredPoolMUSDReserves": fmt_units(total_musd, decimals["MUSD"]),
        "sources": [
            "https://mezo.org/docs/users/resources/contracts-reference",
            "https://mezo.org/docs/developers/features/mezo-pools",
            "https://testnet.mezo.org/docs/users/getting-started/connect",
        ],
        "method": "One chain-verified pinned block; contract ERC-20 totalSupply/decimals/balanceOf, official basic-pool token0/token1/getReserves and code SHA256",
        "limitations": list(ERRORS),
        "signed": False, "userFundsSpent": False,
    }


def compare(left, right):
    if left.get("schemaVersion") != right.get("schemaVersion") or left.get("schemaVersion") != "mezo-musd-proofdesk-v1":
        raise EvidenceError("snapshot schema mismatch")
    if left.get("network", {}).get("chainId") != CHAIN_ID or right.get("network", {}).get("chainId") != CHAIN_ID:
        raise EvidenceError("network mismatch")
    if left.get("block", {}).get("number", 0) >= right.get("block", {}).get("number", 0):
        raise EvidenceError("snapshots must be chronological distinct blocks")
    if len(left.get("pools", [])) != len(POOLS) or len(right.get("pools", [])) != len(POOLS):
        raise EvidenceError("incomplete pool comparison")
    changed = []
    for label in ("MUSD", "MEZO"):
        a, b = left["assets"][label], right["assets"][label]
        if a["address"].lower() != b["address"].lower():
            raise EvidenceError("contract identity mismatch")
        changed.append({"name": label, "runtimeChanged": a["runtime"]["sha256"] != b["runtime"]["sha256"],
                        "supplyBefore": a["totalSupply"], "supplyAfter": b["totalSupply"]})
    for old, new in zip(left["pools"], right["pools"]):
        if old["address"].lower() != new["address"].lower() or old["token0"] != new["token0"] or old["token1"] != new["token1"]:
            raise EvidenceError("pool identity mismatch")
        changed.append({"name": old["name"],
                        "runtimeChanged": old["code"]["sha256"] != new["code"]["sha256"],
                        "musdReserveBefore": old["musdReserve"], "musdReserveAfter": new["musdReserve"]})
    return {"schemaVersion": "mezo-musd-proofdesk-comparison-v1",
            "from": left["block"], "to": right["block"],
            "contractsAndPools": changed,
            "priceOrSolvencyProven": False,
            "comment": "Change evidence only; does not attest liquidity safety, prices, or independent earnings."}


def atomic_json(path: Path, data: dict):
    # Do not silently overwrite an existing evidence or expose credentials.
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(payload)
    return hashlib.sha256(payload).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    get = sub.add_parser("snapshot", help="capture one mainnet pinned public proof; no wallets")
    get.add_argument("--out", required=True, type=Path)
    get.add_argument("--rpc", default=RPC_URL, help="HTTPS read-only Mezo RPC (chain id pinned)")
    comp = sub.add_parser("compare", help="compare two local proof JSON files only")
    comp.add_argument("--left", required=True, type=Path)
    comp.add_argument("--right", required=True, type=Path)
    comp.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    try:
        if a.action == "snapshot":
            data = snapshot(RPC(a.rpc))
        else:
            data = compare(json.loads(a.left.read_text()), json.loads(a.right.read_text()))
        sha = atomic_json(a.out, data)
        print(json.dumps({"status": "saved", "path": str(a.out), "sha256": sha,
                          "chain": data.get("network", {}).get("chainId"),
                          "block": data.get("block", data.get("to", {})).get("number"),
                          "rpcWrites": 0, "walletSigned": False}, ensure_ascii=False))
        return 0
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as ex:
        print("STOP_FAIL_CLOSED: " + type(ex).__name__ + ": " + str(ex)[:220], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
