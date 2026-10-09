from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from swse_scraper_gui import parse_url_text


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


if __name__ == "__main__":
    unittest.main()
