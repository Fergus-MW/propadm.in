"""Protect reproducible sources, referential integrity and withheld audit data."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

EVAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EVAL))

from portfolio.build import build  # noqa: E402 -- standalone unittest discovery
from portfolio.check import read_pack  # noqa: E402
from portfolio.io import read_json  # noqa: E402


class PortfolioDataTests(unittest.TestCase):
    def test_same_seed_has_same_sources_and_changed_seed_changes_portfolio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = build(root / "first", properties=3)
            second = build(root / "second", properties=3)
            changed = build(root / "changed", properties=3, seed=42)
            self.assertEqual(first, second)
            self.assertNotEqual(first["sources_sha256"], changed["sources_sha256"])
            self.assertEqual(sum(first["repair_variants"].values()), 12)
            self.assertEqual(len(first["repair_variants"]), 12)
            read_pack(root / "first")
            with self.assertRaises(FileExistsError):
                build(root / "first", properties=1)
            with self.assertRaises(ValueError):
                build(root / "ANSWERS", properties=1)

    def test_tampered_source_is_rejected_before_ingestion(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "pack"
            build(pack, properties=1)
            source = pack / "sources/properties/SYN-P0001/bank.csv"
            source.write_text(source.read_text().replace("Rent payment", "Different evidence"))
            with self.assertRaisesRegex(ValueError, "Source hash mismatch"):
                read_pack(pack)

    def test_every_property_has_two_tenants_valid_ownership_and_private_money_oracle(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "pack"
            build(pack, properties=12)
            _, indexes = read_pack(pack)
            for group in indexes[1:]:
                ref = group["sources"][0]["shard"]
                oracle = read_json(pack / "evaluator-only" / f"{ref}.json")
                self.assertEqual(sum(r["attributes"]["share_pct"] for r in oracle["owners"]), 100)
                self.assertEqual(len(oracle["tenant_ids"]), 2)
                self.assertEqual(len(oracle["repairs"]), 4)
                for source in group["sources"]:
                    self.assertNotIn("evaluator-only", source["path"])
                    self.assertNotIn("balances", source["upload"])
            self.assertGreater(read_json(pack / "evaluator-only/SYN-P0007.json")["balances"]["tenant_balance_minor"], 0)
            self.assertGreater(read_json(pack / "evaluator-only/SYN-P0010.json")["balances"]["tenant_balance_minor"], 0)
            unknown = (pack / "sources/properties/SYN-P0012/unallocated.ofx").read_text()
            self.assertNotIn("SYN-P0012", unknown)
            self.assertEqual(read_json(pack / "evaluator-only/SYN-P0012.json")["unallocated_count"], 1)

    def test_supplied_crm_records_do_not_assign_derived_balances_or_unearned_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "pack"
            build(pack, properties=3)
            _, indexes = read_pack(pack)
            forbidden = {"tenant_balance_minor", "landlord_balance_minor", "deposit_held_minor",
                         "rating", "jobs_completed", "avg_job_cost_minor", "first_time_fix_rate"}
            for group in indexes:
                for source in group["sources"]:
                    if source["upload"]["mime"] != "application/json":
                        continue
                    for record in json.loads((pack / source["path"]).read_text()):
                        self.assertFalse(set(record["fields"]) & forbidden)
                        for email in record["fields"].get("emails", []):
                            self.assertTrue(email.endswith("@portfolio.example.test"))


if __name__ == "__main__":
    unittest.main()
