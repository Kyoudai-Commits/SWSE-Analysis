#!/usr/bin/env python3
"""Fetch selected SWSE MediaWiki pages and export clean, attributable Markdown.

The target list is deliberately explicit. Lines beginning with ``@discover``
are index pages whose same-wiki links should be added one level deep; discovered
pages are never crawled recursively.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Lock, local
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import (
    parse_qs,
    quote,
    unquote,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = ROOT / "targets.txt"
DEFAULT_OUTPUT = ROOT / "swse_wiki_export"
ALLOWED_HOSTS = {"swse.miraheze.org", "swse.fandom.com"}
REDIRECT_CODES = {301, 302, 303, 307, 308}
RETRYABLE_CODES = {408, 425, 429, 500, 502, 503, 504}


@dataclass
class ScrapedPage:
    requested_url: str
    final_url: str
    canonical_url: str
    host: str
    title: str
    revision_id: str
    categories: list[str]
    body_markdown: str
    etag: str
    last_modified: str


class ScrapeError(RuntimeError):
    """An expected fetch or extraction problem for one page."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_url(raw_url: str, *, base_url: str | None = None) -> str:
    """Normalize an HTTP(S) MediaWiki URL and reject unsupported hosts."""
    raw_url = raw_url.strip()
    absolute = urljoin(base_url, raw_url) if base_url else raw_url
    parts = urlsplit(absolute)
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"URL must use http or https: {raw_url}")
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Host is not in the allowed SWSE wiki list: {host or raw_url}")
    if parts.username or parts.password:
        raise ValueError("URLs containing credentials are not accepted")
    if parts.port not in (None, 80, 443):
        raise ValueError("Non-standard URL ports are not accepted")

    # Upgrade the two known public wikis to HTTPS. Ignore fragments because they
    # identify a section in a page, not a distinct document.
    scheme = "https"
    path = quote(unquote(parts.path or "/"), safe="/:@!$&'()*+,;=-._~")
    query = ""
    if path.endswith("index.php") and parts.query:
        query_values = parse_qs(parts.query, keep_blank_values=True)
        if "title" in query_values:
            query = urlencode({"title": query_values["title"][0]})
    return urlunsplit((scheme, host, path, query, ""))


def load_targets(path: Path) -> tuple[list[str], set[str]]:
    """Read direct URLs and @discover URLs from a line-oriented manifest."""
    if not path.is_file():
        raise FileNotFoundError(f"Target list not found: {path}")

    targets: list[str] = []
    discovery_seeds: set[str] = set()
    seen: set[str] = set()
    for line_number, original_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = original_line.strip()
        if not line or line.startswith("#"):
            continue
        discover = False
        if line.startswith("@discover"):
            pieces = line.split(None, 1)
            if len(pieces) != 2:
                raise ValueError(f"{path}:{line_number}: expected '@discover URL'")
            line = pieces[1].strip()
            discover = True

        try:
            url = normalize_url(line)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if url not in seen:
            targets.append(url)
            seen.add(url)
        if discover:
            discovery_seeds.add(url)

    if not targets:
        raise ValueError(f"No target URLs found in {path}")
    return targets, discovery_seeds


def is_discoverable_wiki_link(url: str, *, base_url: str) -> str | None:
    """Return a clean same-wiki article URL, or None for non-article links."""
    try:
        normalized = normalize_url(url, base_url=base_url)
    except ValueError:
        return None
    parts = urlsplit(normalized)
    if parts.path.startswith("/wiki/"):
        title = parts.path[len("/wiki/"):]
    elif parts.path.endswith("index.php") and parts.query:
        title = parse_qs(parts.query).get("title", [""])[0]
    else:
        return None

    title = title.strip("/")
    if not title:
        return None
    # Index links should expand into content pages, not site-maintenance or
    # discussion namespaces. A category landing page can be explicitly listed
    # in targets.txt, but categories found while expanding are skipped.
    namespace = title.split(":", 1)[0].casefold() if ":" in title else ""
    if namespace in {
        "category", "file", "image", "special", "talk", "user", "user talk",
        "template", "template talk", "help", "mediawiki", "module", "portal",
        "forum", "thread", "media",
    }:
        return None
    if title.casefold() in {"main_page", "main page"}:
        return None
    return normalized


def discover_links(html: str, page_url: str) -> list[str]:
    """Find unique, same-wiki /wiki/ links inside the article body only."""
    soup = BeautifulSoup(html, "html.parser")
    content = find_article_container(soup)
    if content is None:
        return []
    links: list[str] = []
    seen: set[str] = set()
    for anchor in content.select("a[href]"):
        candidate = is_discoverable_wiki_link(anchor.get("href", ""), base_url=page_url)
        if candidate and candidate not in seen:
            links.append(candidate)
            seen.add(candidate)
    return links


def find_article_container(soup: BeautifulSoup) -> Tag | None:
    # Miraheze and Fandom both render MediaWiki content inside this structure.
    return (
        soup.select_one("#mw-content-text .mw-parser-output")
        or soup.select_one(".mw-parser-output")
        or soup.select_one("#mw-content-text")
    )


def extract_revision_id(soup: BeautifulSoup) -> str:
    for selector, attribute in (
        ('meta[property="mw:revisionId"]', "content"),
        ('meta[name="mw:revisionId"]', "content"),
        ("[data-mw-revid]", "data-mw-revid"),
    ):
        node = soup.select_one(selector)
        if node is not None:
            value = node.get(attribute)
            if value:
                return str(value).strip()

    # MediaWiki history links often preserve the revision identifier in oldid.
    for link in soup.select('#ca-history a[href*="oldid="], a[href*="oldid="]'):
        query = parse_qs(urlsplit(link.get("href", "")).query)
        if query.get("oldid"):
            return query["oldid"][0]
    return ""


def extract_categories(soup: BeautifulSoup) -> list[str]:
    categories: list[str] = []
    for anchor in soup.select("#mw-normal-catlinks a, #catlinks a"):
        label = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        if label and "Category:" in href and label not in categories:
            categories.append(label)
    return categories


def clean_markdown(markdown: str) -> str:
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    markdown = markdown.replace("\u00a0", " ").replace("\u200b", "")
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def extract_page(html: str, requested_url: str, final_url: str, response_headers: dict[str, str]) -> ScrapedPage:
    soup = BeautifulSoup(html, "html.parser")
    content = find_article_container(soup)
    if content is None:
        page_title = soup.title.get_text(" ", strip=True) if soup.title else "unknown page"
        raise ScrapeError(
            f"Could not find MediaWiki article content (page title: {page_title!r}); "
            "the site may have returned a consent, error, or anti-bot page"
        )

    heading = soup.select_one("#firstHeading") or soup.find("h1")
    title = heading.get_text(" ", strip=True) if heading else ""
    if not title:
        title = soup.title.get_text(" ", strip=True) if soup.title else urlsplit(final_url).path.rsplit("/", 1)[-1]
    title = re.sub(r"\s+", " ", title).strip()

    # Remove presentation-only chrome while retaining infoboxes, tables,
    # reference lists, captions, formulas, and semantic headings.
    for node in content.select(
        "script, style, noscript, iframe, .mw-editsection, .mw-indicators, "
        ".mw-jump-link, .toc, .navbox, .vertical-navbox, .printfooter, "
        ".catlinks, .mw-normal-catlinks, .noprint, .mw-empty-elt"
    ):
        node.decompose()

    # Make links portable when pages are read outside the source wiki.
    for anchor in content.select("a[href]"):
        anchor["href"] = urljoin(final_url, anchor.get("href", ""))

    body = clean_markdown(markdownify(str(content), heading_style="ATX", bullets="-"))
    if not body:
        raise ScrapeError("Article container was found, but contained no readable text")

    canonical_node = soup.select_one('link[rel="canonical"]')
    canonical_url = final_url
    if canonical_node and canonical_node.get("href"):
        candidate = urljoin(final_url, canonical_node["href"])
        try:
            canonical_url = normalize_url(candidate)
        except ValueError:
            # Do not follow or use a canonical URL on an unrelated host.
            canonical_url = final_url

    return ScrapedPage(
        requested_url=requested_url,
        final_url=final_url,
        canonical_url=canonical_url,
        host=(urlsplit(final_url).hostname or "").lower(),
        title=title,
        revision_id=extract_revision_id(soup),
        categories=extract_categories(soup),
        body_markdown=body,
        etag=response_headers.get("ETag", ""),
        last_modified=response_headers.get("Last-Modified", ""),
    )


def yaml_string(value: str) -> str:
    # JSON string literals are valid YAML double-quoted scalars.
    return json.dumps(value, ensure_ascii=False)


def render_document(page: ScrapedPage, fetched_at: str, content_hash: str) -> str:
    categories = json.dumps(page.categories, ensure_ascii=False)
    frontmatter = [
        "---",
        f"title: {yaml_string(page.title)}",
        f"source_url: {yaml_string(page.requested_url)}",
        f"canonical_url: {yaml_string(page.canonical_url)}",
        f"source_host: {yaml_string(page.host)}",
        f"revision_id: {yaml_string(page.revision_id)}",
        f"retrieved_at_utc: {yaml_string(fetched_at)}",
        f"content_sha256: {yaml_string(content_hash)}",
        f"categories: {categories}",
        "---",
        "",
        f"# {page.title}",
        "",
        f"> Source: [{page.canonical_url}]({page.canonical_url}) · Retrieved {fetched_at}.",
        "",
        page.body_markdown,
        "",
    ]
    return "\n".join(frontmatter)


def safe_slug(title: str, fallback_url: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_title).strip(".-_").lower()
    slug = re.sub(r"[-_]{2,}", "-", slug)
    if not slug:
        slug = hashlib.sha256(fallback_url.encode("utf-8")).hexdigest()[:12]
    return slug[:120]


def load_state(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: ignoring unreadable cache state {path}: {exc}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(text, encoding="utf-8", newline="\n")
    temp_path.replace(path)


def content_exists(output_dir: Path, record: dict[str, Any] | None) -> bool:
    if not record or not record.get("path"):
        return False
    return (output_dir / record["path"]).is_file()


class WikiClient:
    def __init__(self, user_agent: str, delay: float, timeout: float, retries: int):
        self.user_agent = user_agent
        self.delay = max(0.0, delay)
        self.timeout = timeout
        self.retries = retries
        self.last_request_at = 0.0
        self._rate_lock = Lock()
        self._thread_local = local()

    def _session(self) -> requests.Session:
        # requests.Session is not guaranteed thread-safe. Reuse one connection
        # pool per worker thread rather than sharing mutable session state.
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
            })
            self._thread_local.session = session
        return session

    def _request(self, url: str, headers: dict[str, str]) -> requests.Response:
        # Optional global start-rate limit. With the default zero delay, the
        # --workers limit controls parallel in-flight requests.
        with self._rate_lock:
            wait = self.delay - (time.monotonic() - self.last_request_at)
            if wait > 0:
                time.sleep(wait)
            self.last_request_at = time.monotonic()
        return self._session().get(url, headers=headers, timeout=self.timeout, allow_redirects=False)

    def fetch(self, url: str, cached: dict[str, Any] | None, force: bool = False) -> tuple[requests.Response | None, str, bool]:
        """Fetch a page, validating each redirect stays on an allowed host.

        Returns (response, final_url, not_modified). On a 304 response the
        response is None and the caller should reuse its cached record.
        """
        headers: dict[str, str] = {}
        if cached and not force:
            if cached.get("etag"):
                headers["If-None-Match"] = cached["etag"]
            if cached.get("last_modified"):
                headers["If-Modified-Since"] = cached["last_modified"]

        current_url = url
        visited: set[str] = set()
        for redirect_count in range(6):
            if current_url in visited:
                raise ScrapeError("Redirect loop detected")
            visited.add(current_url)
            last_error: Exception | None = None
            response: requests.Response | None = None
            for attempt in range(self.retries + 1):
                try:
                    response = self._request(current_url, headers if redirect_count == 0 else {})
                except requests.RequestException as exc:
                    last_error = exc
                    if attempt >= self.retries:
                        raise ScrapeError(f"Network request failed: {exc}") from exc
                    time.sleep(min(60.0, 2.0 ** attempt))
                    continue

                if response.status_code in RETRYABLE_CODES and attempt < self.retries:
                    retry_after = response.headers.get("Retry-After", "")
                    response.close()
                    try:
                        wait = min(60.0, max(0.0, float(retry_after)))
                    except ValueError:
                        wait = min(60.0, 2.0 ** attempt)
                    time.sleep(wait)
                    continue
                break

            if response is None:
                raise ScrapeError(f"Network request failed: {last_error or 'no response'}")
            if response.status_code == 304:
                response.close()
                return None, current_url, True
            if response.status_code in REDIRECT_CODES:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise ScrapeError("Server returned a redirect without a Location header")
                next_url = urljoin(current_url, location)
                try:
                    current_url = normalize_url(next_url)
                except ValueError as exc:
                    raise ScrapeError(f"Redirect destination rejected: {exc}") from exc
                continue
            if response.status_code >= 400:
                status = response.status_code
                response.close()
                raise ScrapeError(f"HTTP {status}")
            return response, current_url, False
        raise ScrapeError("Too many redirects")


def make_page_path(page: ScrapedPage, url: str, existing_paths: dict[str, str]) -> str:
    host_dir = page.host.replace(".", "-")
    slug = safe_slug(page.title, url)
    relative = f"pages/{host_dir}/{slug}.md"
    previous_owner = existing_paths.get(relative)
    if previous_owner and previous_owner != url:
        suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
        relative = f"pages/{host_dir}/{slug}-{suffix}.md"
    return relative


def write_index(output_dir: Path, state: dict[str, dict[str, Any]]) -> int:
    records: list[dict[str, Any]] = []
    for url, cached in state.items():
        relpath = cached.get("path", "")
        if not relpath or not (output_dir / relpath).is_file():
            continue
        records.append({
            "title": cached.get("title", ""),
            "source_url": cached.get("source_url", url),
            "canonical_url": cached.get("canonical_url", url),
            "source_host": cached.get("source_host", urlsplit(url).hostname or ""),
            "revision_id": cached.get("revision_id", ""),
            "retrieved_at_utc": cached.get("retrieved_at_utc", ""),
            "path": relpath,
            "content_sha256": cached.get("content_sha256", ""),
            "character_count": cached.get("character_count", 0),
            "categories": cached.get("categories", []),
        })
    records.sort(key=lambda item: (item["source_host"], item["title"].casefold(), item["source_url"]))
    text = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in records)
    atomic_write(output_dir / "index.jsonl", text)
    return len(records)


def scrape_one(
    url: str,
    client: WikiClient,
    output_dir: Path,
    state: dict[str, dict[str, Any]],
    existing_paths: dict[str, str],
    state_lock: Any,
    force: bool,
    collect_links: bool,
) -> tuple[dict[str, Any] | None, list[str], str]:
    with state_lock:
        previous = state.get(url)
    response, final_url, not_modified = client.fetch(url, previous, force=force)
    if not_modified:
        if content_exists(output_dir, previous):
            cached_links = previous.get("discovered_links", []) if collect_links else []
            return previous, cached_links, "not-modified"
        # A stale cache entry without its Markdown body is not useful. Retry once
        # without conditional headers instead of claiming the page was saved.
        response, final_url, not_modified = client.fetch(url, None, force=True)
        if not_modified or response is None:
            raise ScrapeError("Received 304 but the cached Markdown file is missing")

    assert response is not None
    try:
        html = response.text
        page = extract_page(html, url, final_url, dict(response.headers))
        links = discover_links(html, final_url) if collect_links else []
    finally:
        response.close()

    content_hash = sha256_text(page.body_markdown)
    fetched_at = utc_now()
    if previous and previous.get("content_sha256") == content_hash:
        fetched_at = previous.get("retrieved_at_utc") or fetched_at

    record: dict[str, Any]
    with state_lock:
        relpath = make_page_path(page, url, existing_paths)
        document = render_document(page, fetched_at, content_hash)
        atomic_write(output_dir / relpath, document)
        record = {
            "source_url": url,
            "canonical_url": page.canonical_url,
            "source_host": page.host,
            "title": page.title,
            "revision_id": page.revision_id,
            "retrieved_at_utc": fetched_at,
            "path": relpath,
            "content_sha256": content_hash,
            "character_count": len(page.body_markdown),
            "categories": page.categories,
            "discovered_links": links if collect_links else (previous or {}).get("discovered_links", []),
            "etag": page.etag,
            "last_modified": page.last_modified,
        }
        state[url] = record
        existing_paths[relpath] = url
    return record, links, "downloaded"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export selected SWSE wiki pages as attributable, AI-friendly Markdown."
    )
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS,
                        help=f"one URL per line; default: {DEFAULT_TARGETS}")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"export directory; default: {DEFAULT_OUTPUT}")
    parser.add_argument("--workers", type=int, default=25,
                        help="concurrent page requests, from 1 to 50 (default: 25)")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="minimum seconds between request starts across workers (default: 0)")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="HTTP timeout in seconds (default: 30)")
    parser.add_argument("--retries", type=int, default=3,
                        help="retries for network/temporary server errors (default: 3)")
    parser.add_argument("--max-pages", type=int, default=2000,
                        help="safety limit including discovered pages (default: 2000)")
    parser.add_argument("--user-agent", default=os.environ.get(
        "SWSE_SCRAPER_USER_AGENT",
        "SWSE-Wiki-Reference-Exporter/1.0 (personal research; contact: set SWSE_SCRAPER_USER_AGENT)",
    ), help="identify this client; can also be set with SWSE_SCRAPER_USER_AGENT")
    parser.add_argument("--refresh", action="store_true",
                        help="ignore ETag/Last-Modified cache validators and fetch every target")
    parser.add_argument("--skip-discovery", action="store_true",
                        help="fetch only the explicit URLs; do not expand @discover entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and summarize the manifest without making requests")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if (
        not 1 <= args.workers <= 50
        or args.delay < 0
        or args.timeout <= 0
        or args.retries < 0
        or args.max_pages <= 0
    ):
        print(
            "Error: workers must be 1-50; delay must be >= 0; timeout/max-pages must be > 0; retries must be >= 0",
            file=sys.stderr,
        )
        return 2

    try:
        targets, discovery_seeds = load_targets(args.targets)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"Manifest: {args.targets}")
        print(f"Explicit pages: {len(targets)}")
        print(f"One-level discovery pages: {len(discovery_seeds) if not args.skip_discovery else 0}")
        print(f"Concurrent workers: {args.workers} (maximum 50)")
        print(f"Request-start delay: {args.delay} seconds")
        print(f"Allowed hosts: {', '.join(sorted(ALLOWED_HOSTS))}")
        print(f"Output: {args.output}")
        return 0

    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / ".scraper-state.json"
    state = load_state(state_path)
    existing_paths = {
        record.get("path", ""): url
        for url, record in state.items()
        if record.get("path")
    }
    client = WikiClient(args.user_agent, args.delay, args.timeout, args.retries)
    state_lock = Lock()

    # Keep explicit targets ahead of any discovered links if the safety cap is hit.
    if len(targets) > args.max_pages:
        print(
            f"Warning: {len(targets) - args.max_pages} explicit pages omitted due to --max-pages={args.max_pages}",
            file=sys.stderr,
        )
        targets = targets[:args.max_pages]

    errors: list[dict[str, str]] = []
    counts = {"downloaded": 0, "not_modified": 0, "failed": 0}
    discovered_pages_queued = 0
    started_at = utc_now()
    print(f"Downloading {len(targets)} explicit pages with up to {args.workers} concurrent workers.")
    if args.delay:
        print(f"Global request-start delay: {args.delay:g} seconds.")

    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="swse-wiki") as executor:
        def download_batch(batch: list[str]) -> dict[str, tuple[dict[str, Any] | None, list[str], str]]:
            results: dict[str, tuple[dict[str, Any] | None, list[str], str]] = {}
            if not batch:
                return results
            futures = {
                executor.submit(
                    scrape_one,
                    url,
                    client,
                    output_dir,
                    state,
                    existing_paths,
                    state_lock,
                    args.refresh,
                    not args.skip_discovery and url in discovery_seeds,
                ): url
                for url in batch
            }
            total = len(futures)
            for completed, future in enumerate(as_completed(futures), 1):
                url = futures[future]
                print(f"[{completed}/{total}] {url}")
                try:
                    result = future.result()
                    results[url] = result
                    record, _links, status = result
                    if status == "downloaded":
                        counts["downloaded"] += 1
                        print(f"  saved: {record['path']}")
                    elif status == "not-modified":
                        counts["not_modified"] += 1
                        print("  unchanged (HTTP 304)")
                except Exception as exc:  # Keep the batch moving; include failures in report.
                    counts["failed"] += 1
                    errors.append({"url": url, "error": str(exc)})
                    print(f"  failed: {exc}", file=sys.stderr)
            return results

        # The first phase downloads exact targets. Discovery is limited to
        # one-hop links from the explicitly marked index pages.
        direct_results = download_batch(targets)
        discovery_queue: list[str] = []
        queued_set = set(targets)
        if not args.skip_discovery:
            for seed_url in targets:
                seed_result = direct_results.get(seed_url)
                if seed_url not in discovery_seeds or seed_result is None:
                    continue
                _record, links, _status = seed_result
                for link in links:
                    if link not in queued_set:
                        queued_set.add(link)
                        discovery_queue.append(link)

        remaining = max(0, args.max_pages - len(targets))
        discovered_targets = discovery_queue[:remaining]
        discovered_pages_queued = len(discovered_targets)
        if len(discovery_queue) > remaining:
            print(
                f"Warning: omitted {len(discovery_queue) - remaining} discovered links due to --max-pages",
                file=sys.stderr,
            )
        if discovered_targets:
            print(
                f"\nDownloading {len(discovered_targets)} linked pages with up to {args.workers} concurrent workers."
            )
            download_batch(discovered_targets)

    state["_meta"] = {"last_run_utc": utc_now(), "targets_file": str(args.targets)}
    # Keep the private request cache out of the checked-in corpus; the public
    # index is intentionally regenerated from page records only.
    state_without_meta = {key: value for key, value in state.items() if not key.startswith("_")}
    atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    indexed_pages = write_index(output_dir, state_without_meta)
    report = {
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "targets_file": args.targets.name,
        "output_directory": output_dir.name,
        "counts": counts,
        "workers": args.workers,
        "request_start_delay_seconds": args.delay,
        "indexed_pages": indexed_pages,
        "discovery_seeds": len(discovery_seeds) if not args.skip_discovery else 0,
        "discovered_pages_queued": discovered_pages_queued,
        "errors": errors,
    }
    atomic_write(output_dir / "report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    print("\nFinished.")
    print(f"  downloaded:    {counts['downloaded']}")
    print(f"  unchanged:      {counts['not_modified']}")
    print(f"  failed:         {counts['failed']}")
    print(f"  indexed pages:  {indexed_pages}")
    print(f"  export:         {output_dir}")
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
