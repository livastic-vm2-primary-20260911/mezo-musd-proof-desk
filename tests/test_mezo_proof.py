import copy
from datetime import datetime, timezone
import io
import json
import tempfile
import unittest
from pathlib import Path

import mezo_proof as m


def word(n):
    return "0x" + format(n, "064x")


def address_word(addr):
    return "0x" + addr[2:].lower().rjust(64, "0")


class FakeRPC:
    def __init__(self):
        self.url = "https://mock-mainnet.invalid"
        self.counter = 0
        self.bad_chain = False
        self.bad_pool = False
        self.reorg = False
        self.big_decimals = False
        self.empty_code = False
        self.bad_reserves = False
        self.calls = []
        self.block_reads = 0
        self.tokens = [m.CONTRACTS["MUSD"], m.CONTRACTS["MEZO"],
                       m.CONTRACTS["mUSDC"], m.CONTRACTS["mUSDT"]]

    def call(self, name, params):
        self.counter += 1
        self.calls.append(name)
        if name == "eth_chainId":
            return "0x1" if self.bad_chain else hex(m.CHAIN_ID)
        if name == "eth_blockNumber":
            return "0x12345"
        if name == "eth_getBlockByNumber":
            self.block_reads += 1
            return {"number": "0x12345", "timestamp": "0x6adb731b",
                    "hash": "0x" + ("a" if self.reorg and self.block_reads > 1 else "b") * 64}
        if name == "eth_getCode":
            return "0x" if self.empty_code else "0x60006000"
        if name != "eth_call":
            raise AssertionError("unexpected RPC method " + name)
        call = params[0]
        addr, data = call["to"], call["data"]
        if data == m.SELECTORS["decimals"]:
            if self.big_decimals:
                return word(99)
            return word(6 if addr.lower() in {m.CONTRACTS["mUSDC"].lower(), m.CONTRACTS["mUSDT"].lower()} else 18)
        if data == m.SELECTORS["totalSupply"]:
            return word(500_000_000_000_000_000_000_000)
        for name, pool_addr, pair, _ in m.POOLS:
            if addr.lower() != pool_addr.lower():
                continue
            if data == m.SELECTORS["token0"]:
                return address_word(m.CONTRACTS[pair] if pair != "mUSDT" else m.CONTRACTS["MUSD"])
            if data == m.SELECTORS["token1"]:
                if self.bad_pool:
                    return address_word(m.CONTRACTS["MEZO"])
                return address_word(m.CONTRACTS["MUSD"] if pair != "mUSDT" else m.CONTRACTS[pair])
            if data == m.SELECTORS["getReserves"]:
                if self.bad_reserves:
                    return "0x1234"
                return "0x" + "".join(f"{v:064x}" for v in (12 * 10 ** 18, 34 * 10 ** 18, 1_700_000_000))
        if data.startswith(m.SELECTORS["balanceOf"]):
            return word(34 * 10 ** 18)
        raise AssertionError("unexpected call")


class DecoderTests(unittest.TestCase):
    def test_fmt_units_high_precision(self):
        self.assertEqual(m.fmt_units(123456789123456789, 18), "0.123456789123456789")

    def test_fmt_units_tiny_integer(self):
        self.assertEqual(m.fmt_units(5, 6), "0.000005")

    def test_fmt_units_reject_negative(self):
        with self.assertRaises(m.EvidenceError):
            m.fmt_units(-1, 18)

    def test_fmt_units_reject_large_decimals(self):
        with self.assertRaises(m.EvidenceError):
            m.fmt_units(12, 99)

    def test_decode_hex_reject_odd(self):
        with self.assertRaises(m.EvidenceError):
            m.decode_hex("0xf")

    def test_decode_hex_reject_text(self):
        with self.assertRaises(m.EvidenceError):
            m.decode_hex("privatekey")

    def test_decode_hex_reject_too_large(self):
        with self.assertRaises(m.EvidenceError):
            m.decode_hex("0x00" * 10, 4)

    def test_abi_address_valid(self):
        self.assertEqual(m.abi_address(address_word(m.CONTRACTS["MUSD"])), m.CONTRACTS["MUSD"].lower())

    def test_abi_address_reject_high_bits(self):
        with self.assertRaises(m.EvidenceError):
            m.abi_address("0xff" + "00" * 31)

    def test_abi_uint_reject_wrong_length(self):
        with self.assertRaises(m.EvidenceError):
            m.abi_uint("0x01")

    def test_padded_address(self):
        self.assertEqual(len(m.padded_address(m.CONTRACTS["MUSD"])), 64)
        with self.assertRaises(m.EvidenceError):
            m.padded_address("0x1234")


class SnapshotTests(unittest.TestCase):
    def test_snapshot_mezo_mainnet_pass(self):
        r = FakeRPC()
        data = m.snapshot(r)
        self.assertEqual(data["network"]["chainId"], 31612)
        self.assertEqual(data["block"]["number"], 74565)
        self.assertEqual(len(data["pools"]), 3)
        self.assertEqual(data["pools"][0]["asset0"], "BTC")
        self.assertEqual(data["pools"][1]["asset0"], "mUSDC")
        self.assertEqual(data["pools"][2]["asset0"], "MUSD")
        self.assertEqual(data["pools"][2]["asset1"], "mUSDT")
        self.assertIn("MUSD", data["assets"])
        self.assertFalse(data["signed"])
        self.assertLessEqual(r.counter, m.MAX_RPC)
        self.assertFalse(set(r.calls) - {"eth_chainId", "eth_blockNumber",
                                          "eth_getBlockByNumber", "eth_getCode", "eth_call"})

    def test_wrong_chain_fails_before_contract_calls(self):
        r = FakeRPC()
        r.bad_chain = True
        with self.assertRaisesRegex(m.EvidenceError, "wrong chain"):
            m.snapshot(r)
        self.assertEqual(r.calls, ["eth_chainId"])

    def test_pool_pair_changed_fails_closed(self):
        r = FakeRPC()
        r.bad_pool = True
        with self.assertRaisesRegex(m.EvidenceError, "token pair changed"):
            m.snapshot(r)

    def test_reorg_detected(self):
        r = FakeRPC()
        r.reorg = True
        with self.assertRaisesRegex(m.EvidenceError, "hash changed"):
            m.snapshot(r)

    def test_bad_decimals_rejected(self):
        r = FakeRPC()
        r.big_decimals = True
        with self.assertRaisesRegex(m.EvidenceError, "decimals"):
            m.snapshot(r)

    def test_missing_contract_code_rejected(self):
        r = FakeRPC()
        r.empty_code = True
        with self.assertRaisesRegex(m.EvidenceError, "bytecode"):
            m.snapshot(r)

    def test_wrong_reserves_length_rejected(self):
        r = FakeRPC()
        r.bad_reserves = True
        with self.assertRaises(m.EvidenceError):
            m.snapshot(r)

    def test_same_block_rechecked(self):
        r = FakeRPC()
        m.snapshot(r)
        self.assertEqual(r.block_reads, 2)


class RPCTests(unittest.TestCase):
    def test_rpc_reject_write_method(self):
        rpc = m.RPC()
        for name in ["eth_sendRawTransaction", "eth_sendTransaction", "personal_sign",
                     "eth_sign", "wallet_addEthereumChain", "eth_estimateGas"]:
            with self.assertRaises(m.EvidenceError):
                rpc.call(name, [])
        self.assertEqual(rpc.counter, 0)

    def test_https_only(self):
        for url in ["http://rpc.mezo.org", "https://guest:secret@example.org",
                    "https://rpc.example.org/?apiKey=secret"]:
            with self.assertRaises(m.EvidenceError):
                m.RPC(url)

    def test_response_integrity_and_hard_quota(self):
        class BadResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return b'{"jsonrpc":"2.0","id":99,"result":"0x7b7c"}'
        r = m.RPC(opener=lambda request, timeout: BadResponse())
        with self.assertRaisesRegex(m.EvidenceError, "inconsistent RPC"):
            r.call("eth_chainId", [])
        r.counter = m.MAX_RPC
        with self.assertRaisesRegex(m.EvidenceError, "maximum"):
            r.call("eth_chainId", [])


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.before = m.snapshot(FakeRPC())
        self.after = copy.deepcopy(self.before)
        self.after["block"]["number"] += 5
        self.after["block"]["hash"] = "0x" + "c" * 64

    def test_compare_valid(self):
        diff = m.compare(self.before, self.after)
        self.assertEqual(len(diff["contractsAndPools"]), 5)
        self.assertTrue(all(not x["runtimeChanged"] for x in diff["contractsAndPools"]))
        self.assertFalse(diff["priceOrSolvencyProven"])

    def test_compare_detect_runtime_change(self):
        self.after["assets"]["MUSD"]["runtime"]["sha256"] = "a" * 64
        diff = m.compare(self.before, self.after)
        self.assertTrue(diff["contractsAndPools"][0]["runtimeChanged"])

    def test_compare_order_enforced(self):
        self.after["block"]["number"] -= 5
        with self.assertRaises(m.EvidenceError):
            m.compare(self.before, self.after)

    def test_compare_identity_enforced(self):
        self.after["pools"][0]["address"] = self.after["pools"][1]["address"]
        with self.assertRaises(m.EvidenceError):
            m.compare(self.before, self.after)

    def test_compare_incomplete_enforced(self):
        self.after["pools"].pop()
        with self.assertRaises(m.EvidenceError):
            m.compare(self.before, self.after)

    def test_atomic_json_no_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.json"
            digest = m.atomic_json(p, self.before)
            self.assertEqual(len(digest), 64)
            original = p.read_bytes()
            with self.assertRaises(FileExistsError):
                m.atomic_json(p, self.after)
            self.assertEqual(original, p.read_bytes())


if __name__ == "__main__":
    unittest.main()
