"""Offline report must be a faithful, fail-closed transform of source-backed Mezo evidence."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

THIS = Path(__file__).resolve()
BASE = THIS.parents[1]
SPEC = importlib.util.spec_from_file_location("mezo_report_generator", BASE / "scripts/build_sample_report.py")
import sys
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)


class OriginalSampleReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raws = [p.read_bytes() for p in (m.OLD, m.NEW, m.DIFF)]
        cls.orig = tuple(m.parse_json(b) for b in raws)
        cls.hashes = tuple(m.sha(b) for b in raws)

    def inputs(self):
        return copy.deepcopy(self.orig)

    def test_real_original_evidence_render(self):
        old, new, diff = self.inputs()
        html = m.render(old, new, diff, self.hashes)
        self.assertIn("PUBLIC SALES SAMPLE", html)
        self.assertIn("NOT COMMISSIONED", html)
        self.assertIn("no", html.lower())
        self.assertIn("CHAIN", html)
        self.assertIn("12,709,282", html)
        self.assertIn("12,709,416", html)
        self.assertIn("53,891", html)
        self.assertIn("19 USDC", html)
        self.assertNotIn("realized profit", html.lower())
        self.assertNotIn("guaranteed", html.lower())

    def test_wrong_chain_denied(self):
        old, new, diff = self.inputs()
        old["network"]["chainId"] = 1
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_wrong_pair_token_denied(self):
        old, new, diff = self.inputs()
        new["pools"][0]["token0"] = m.EXPECTED_ASSETS["MEZO"]
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_wrong_pair_name_denied(self):
        old, new, diff = self.inputs()
        new["pools"][0]["asset0"] = "mUSDC"
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_tampered_reported_pool_total_denied(self):
        old, new, diff = self.inputs()
        new["measuredPoolMUSDReserves"] = "1"
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_forged_runtime_flag_denied(self):
        old, new, diff = self.inputs()
        diff["contractsAndPools"][0]["runtimeChanged"] = True
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_missing_comparison_denied(self):
        old, new, diff = self.inputs()
        diff["contractsAndPools"].pop()
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_incomplete_source_denied(self):
        old, new, diff = self.inputs()
        del old["assets"]["MEZO"]["totalSupply"]
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_nonchronological_denied(self):
        old, new, diff = self.inputs()
        new["block"]["number"] = old["block"]["number"]
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_invalid_abi_data_sanitized(self):
        old, new, diff = self.inputs()
        old["assets"]["MUSD"]["totalSupply"] = "<script>alert(1)</script>"
        with self.assertRaises(m.InvalidEvidence):
            m.render(old, new, diff, self.hashes)

    def test_paid_offer_only_indicative(self):
        old, new, diff = self.inputs()
        html = m.render(old, new, diff, self.hashes)
        self.assertIn("seller-proposed", html)
        self.assertIn("NOT", html)
        self.assertIn("network calls", html.lower())
        self.assertIn("No real customer material", html)

    def test_file_exclusive_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.html"
            path, digest = m.build(out_path=p)
            self.assertEqual(path, p)
            self.assertEqual(len(digest), 64)
            data = p.read_bytes()
            with self.assertRaises(FileExistsError):
                m.build(out_path=p)
            self.assertEqual(data, p.read_bytes())


if __name__ == "__main__":
    unittest.main()
