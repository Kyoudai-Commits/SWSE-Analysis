from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from swse_scraper_gui import parse_url_text, retry_targets_from_report


class GuiUrlInputTests(unittest.TestCase):
    def test_parses_plain_and_markdown_urls_and_deduplicates(self) -> None:
        pasted = (
            "https://swse.miraheze.org/wiki/Introduction\n"
            "[Armor page](https://swse.miraheze.org/wiki/Armor_Proficiency_(Light))\n"
            "https://swse.miraheze.org/wiki/Introduction"
        )
        valid, invalid = parse_url_text(pasted)
        self.assertEqual(
            valid,
            [
                "https://swse.miraheze.org/wiki/Introduction",
                "https://swse.miraheze.org/wiki/Armor_Proficiency_(Light)",
            ],
        )
        self.assertEqual(invalid, [])

    def test_rejects_hosts_outside_supported_wikis(self) -> None:
        valid, invalid = parse_url_text(
            "https://www.w3.org/1999/xhtml\nhttps://swse.fandom.com/wiki/Technician"
        )
        self.assertEqual(valid, ["https://swse.fandom.com/wiki/Technician"])
        self.assertEqual(len(invalid), 1)
        self.assertIn("not in the allowed", invalid[0][1])

    def test_retry_targets_include_only_reported_failures(self) -> None:
        failed_seed = "https://swse.miraheze.org/wiki/Feats"
        failed_article = "https://swse.miraheze.org/wiki/Feat_A"
        report = {
            "discovery_seed_urls": [failed_seed],
            "errors": [
                {"url": failed_seed, "error": "timeout", "discovery_seed": True},
                {"url": failed_article, "error": "HTTP 503"},
                {"url": "https://www.w3.org/1999/xhtml", "error": "unsupported"},
            ],
        }
        urls, seeds = retry_targets_from_report(report)
        self.assertEqual(urls, [failed_seed, failed_article])
        self.assertEqual(seeds, {failed_seed})


if __name__ == "__main__":
    unittest.main()
