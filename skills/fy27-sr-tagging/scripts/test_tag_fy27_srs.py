#!/usr/bin/env python3
"""Fixture tests for tag_fy27_srs.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("tag_fy27_srs.py")
SPEC = importlib.util.spec_from_file_location("tag_fy27_srs", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


TABLE = """# Mapping
## SRs

| Company Name | SR Number | OppID | CPR | Status |
| --- | --- | --- | --- | --- |
| #Customer_Acme | #SR0001234567 | #A1B2C3 | #CPR_AdaLovelace | Assigned |
| #Customer_Blank |  |  | #CPR_GraceHopper | Need to make SR |
"""


class TaggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "Sales Team FY27"
        self.root.mkdir()
        self.table = self.root / "Tag and SRs.md"
        self.table.write_text(TABLE, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_skill(self, *extra: str) -> int:
        return MODULE.run(
            [
                "--sales-root",
                str(self.root),
                "--table",
                str(self.table),
                "--details-limit",
                "0",
                *extra,
            ]
        )

    def test_preview_then_write_is_idempotent_and_preserves_body(self) -> None:
        note = self.root / "meeting.md"
        original = (
            "#7-1-26 #FY27 #Customer_Acme #CPR_AdaLovelace \r\n"
            "## Executive Summary\r\nUnchanged body.\r\n"
        ).encode("utf-8")
        note.write_bytes(original)

        self.assertEqual(self.run_skill(), 0)
        self.assertEqual(note.read_bytes(), original)
        self.assertEqual(self.run_skill("--write"), 0)
        expected = (
            "#7-1-26 #FY27 #Customer_Acme #CPR_AdaLovelace "
            "#SR0001234567 #A1B2C3 \r\n"
            "## Executive Summary\r\nUnchanged body.\r\n"
        ).encode("utf-8")
        self.assertEqual(note.read_bytes(), expected)
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_bytes(), expected)

    def test_inline_tags_after_yaml_frontmatter_are_supported(self) -> None:
        note = self.root / "frontmatter.md"
        note.write_text(
            "---\ntitle: Example\n---\n\n"
            "#FY27 #Customer_Acme #CPR_AdaLovelace\nBody\n",
            encoding="utf-8",
        )
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertIn(
            "#Customer_Acme #CPR_AdaLovelace #SR0001234567 #A1B2C3\n",
            note.read_text(encoding="utf-8"),
        )

    def test_yaml_block_tag_list_is_updated_and_idempotent(self) -> None:
        note = self.root / "yaml-block.md"
        note.write_text(
            "---\n"
            "tags:\n"
            "  - FY27\n"
            "  - CPR_AdaLovelace\n"
            "  - Customer_Acme\n"
            "---\n\n"
            "## Executive Summary\n"
            "Unchanged body.\n",
            encoding="utf-8",
        )
        self.assertEqual(self.run_skill(), 0)
        self.assertNotIn("SR0001234567", note.read_text(encoding="utf-8"))
        self.assertEqual(self.run_skill("--write"), 0)
        expected = (
            "---\n"
            "tags:\n"
            "  - FY27\n"
            "  - CPR_AdaLovelace\n"
            "  - Customer_Acme\n"
            "  - SR0001234567\n"
            "  - A1B2C3\n"
            "---\n\n"
            "## Executive Summary\n"
            "Unchanged body.\n"
        )
        self.assertEqual(note.read_text(encoding="utf-8"), expected)
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_text(encoding="utf-8"), expected)

    def test_yaml_inline_tag_list_is_updated(self) -> None:
        note = self.root / "yaml-inline.md"
        note.write_text(
            "---\n"
            "tags: [FY27, Customer_Acme, CPR_AdaLovelace]\n"
            "title: Example\n"
            "---\n"
            "Body\n",
            encoding="utf-8",
        )
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(
            note.read_text(encoding="utf-8"),
            "---\n"
            "tags: [FY27, Customer_Acme, CPR_AdaLovelace, "
            "SR0001234567, A1B2C3]\n"
            "title: Example\n"
            "---\n"
            "Body\n",
        )

    def test_yaml_tag_list_with_wrong_cpr_is_not_modified(self) -> None:
        note = self.root / "yaml-wrong-owner.md"
        original = (
            "---\n"
            "tags:\n"
            "  - FY27\n"
            "  - Customer_Acme\n"
            "  - CPR_GraceHopper\n"
            "---\n"
            "Body\n"
        )
        note.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_text(encoding="utf-8"), original)

    def test_scalar_yaml_tags_property_is_not_modified(self) -> None:
        note = self.root / "yaml-scalar.md"
        original = "---\ntags: Customer_Acme\n---\nBody\n"
        note.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_text(encoding="utf-8"), original)

    def test_wrong_cpr_is_not_modified(self) -> None:
        note = self.root / "wrong-owner.md"
        original = "#FY27 #Customer_Acme #CPR_GraceHopper\nBody\n"
        note.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_text(encoding="utf-8"), original)

    def test_existing_sr_conflict_is_not_modified(self) -> None:
        note = self.root / "conflict.md"
        original = (
            "#FY27 #Customer_Acme #CPR_AdaLovelace "
            "#SR0009999999 #Z9Y8X7\nBody\n"
        )
        note.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_text(encoding="utf-8"), original)

    def test_conflicting_duplicate_source_rows_are_not_applied(self) -> None:
        with self.table.open("a", encoding="utf-8") as handle:
            handle.write(
                "| #Customer_Acme | #SR0007654321 | #Z1Y2X3 | "
                "#CPR_AdaLovelace | Assigned |\n"
            )
        note = self.root / "duplicate.md"
        original = "#FY27 #Customer_Acme #CPR_AdaLovelace\n"
        note.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_skill("--write"), 0)
        self.assertEqual(note.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
