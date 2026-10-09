from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import scrape_swse_wiki as scraper


class TargetManifestTests(unittest.TestCase):
    def test_targets_and_discovery_directives_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target_file = Path(directory) / "targets.txt"
            target_file.write_text(
                "# sample\n"
                "https://swse.miraheze.org/wiki/Feats\n"
                "@discover https://swse.miraheze.org/wiki/Feats\n"
                "https://swse.fandom.com/wiki/Technician\n",
                encoding="utf-8",
            )
            targets, discovery = scraper.load_targets(target_file)

        self.assertEqual(
            targets,
            [
                "https://swse.miraheze.org/wiki/Feats",
                "https://swse.fandom.com/wiki/Technician",
            ],
        )
        self.assertEqual(discovery, {"https://swse.miraheze.org/wiki/Feats"})

    def test_manifest_rejects_unlisted_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target_file = Path(directory) / "targets.txt"
            target_file.write_text("https://www.w3.org/1999/xhtml\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not in the allowed"):
                scraper.load_targets(target_file)

    def test_normalize_removes_fragment_and_upgrades_http(self) -> None:
        self.assertEqual(
            scraper.normalize_url("http://swse.miraheze.org/wiki/Species#Human"),
            "https://swse.miraheze.org/wiki/Species",
        )
        self.assertEqual(
            scraper.normalize_url("https://swse.miraheze.org/wiki/Ter%C3%A4s"),
            scraper.normalize_url("https://swse.miraheze.org/wiki/Teräs"),
        )


class HtmlExtractionTests(unittest.TestCase):
    HTML = """<!doctype html>
    <html><head>
      <link rel="canonical" href="https://swse.miraheze.org/wiki/Example">
      <meta property="mw:revisionId" content="12345">
      <title>Example - SWSE Wiki</title>
    </head><body>
      <h1 id="firstHeading">Example</h1>
      <div id="mw-content-text"><div class="mw-parser-output">
        <div class="toc"><p>Contents navigation</p></div>
        <p>A rule with <a href="/wiki/Other_Page">a cross-reference</a>.</p>
        <h2><span class="mw-headline">Overview</span></h2>
        <ul><li>First item</li><li>Second item</li></ul>
        <table><tr><th>Value</th></tr><tr><td>Important table text</td></tr></table>
        <div class="navbox">Navigation-only content</div>
        <script>not article text</script>
      </div></div>
      <div id="mw-normal-catlinks"><a href="/wiki/Category:Rules">Rules</a></div>
    </body></html>"""

    def test_extracts_article_text_and_metadata(self) -> None:
        url = "https://swse.miraheze.org/wiki/Example"
        page = scraper.extract_page(self.HTML, url, url, {"ETag": '"abc"'})

        self.assertEqual(page.title, "Example")
        self.assertEqual(page.revision_id, "12345")
        self.assertEqual(page.categories, ["Rules"])
        self.assertEqual(page.etag, '"abc"')
        self.assertIn("# Overview", page.body_markdown)
        self.assertIn("First item", page.body_markdown)
        self.assertIn("Important table text", page.body_markdown)
        self.assertIn("https://swse.miraheze.org/wiki/Other_Page", page.body_markdown)
        self.assertNotIn("Contents navigation", page.body_markdown)
        self.assertNotIn("Navigation-only content", page.body_markdown)
        self.assertNotIn("not article text", page.body_markdown)

    def test_discovery_only_returns_same_wiki_content_pages(self) -> None:
        html = """<div id="mw-content-text"><div class="mw-parser-output">
        <a href="/wiki/Feat_A">Feat</a>
        <a href="/wiki/Category:Feats">Category</a>
        <a href="https://example.org/wiki/External">External</a>
        <a href="/wiki/File:Image.png">File</a>
        <a href="/w/index.php?title=Feat_B">Index route</a>
        </div></div>"""
        links = scraper.discover_links(html, "https://swse.miraheze.org/wiki/Feats")
        self.assertEqual(
            links,
            [
                "https://swse.miraheze.org/wiki/Feat_A",
                "https://swse.miraheze.org/w/index.php?title=Feat_B",
            ],
        )

    def test_document_frontmatter_is_validly_quoted(self) -> None:
        url = "https://swse.miraheze.org/wiki/Example"
        page = scraper.extract_page(self.HTML, url, url, {})
        document = scraper.render_document(page, "2026-10-09T00:00:00Z", "deadbeef")
        self.assertTrue(document.startswith("---\ntitle: \"Example\""))
        self.assertIn(f"source_url: \"{url}\"", document)
        self.assertIn("content_sha256: \"deadbeef\"", document)

    def test_unicode_title_gets_portable_slug(self) -> None:
        self.assertEqual(
            scraper.safe_slug("Teräs Käsi", "https://swse.miraheze.org/wiki/Teras"),
            "teras-kasi",
        )


if __name__ == "__main__":
    unittest.main()
