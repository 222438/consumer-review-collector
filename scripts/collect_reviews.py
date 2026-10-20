"""Collect review-like records from a public HTML page or local fixture.

This standard-library collector supports JSON-LD review objects and common
itemprop/class-marked HTML. It does not automate a browser or bypass access
controls. Keep page limits and delays small for live public pages.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_module
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

FIELDS = ["brand", "product", "rating", "review", "review_id", "reviewer", "review_date", "source_url"]
SPACE_RE = re.compile(r"\s+")
RATING_RE = re.compile(r"(?<!\d)([1-5](?:\.\d+)?)\s*(?:/\s*5|out of 5|stars?|分)", re.I)
REVIEW_RE = re.compile(r"review|comment|testimonial|feedback", re.I)


def clean(value: Any) -> str:
    return SPACE_RE.sub(" ", html_module.unescape(str(value or ""))).strip()


def rating_value(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("ratingValue") or value.get("value")
    text = clean(value)
    match = RATING_RE.search(text) or re.search(r"(?<!\d)([1-5](?:\.\d+)?)\s*$", text)
    if not match:
        return ""
    number = float(match.group(1))
    return str(int(number)) if number.is_integer() else str(number)


def stable_id(row: dict[str, str]) -> str:
    if row.get("review_id"):
        return row["review_id"]
    material = "|".join(row.get(key, "") for key in ("brand", "product", "rating", "review", "review_date"))
    return "local-" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


class ReviewHTMLParser(HTMLParser):
    """Extract text and metadata from common review markup."""

    def __init__(self, source_url: str):
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.jsonld: list[str] = []
        self.next_url: str | None = None
        self._stack: list[dict[str, Any]] = []
        self._records: list[dict[str, str]] = []

    @staticmethod
    def attrs_map(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): (value or "") for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = self.attrs_map(attrs)
        lowered_tag = tag.lower()
        rel = attrs_map.get("rel", "").lower().split()
        if lowered_tag == "link" and "next" in rel and attrs_map.get("href"):
            self.next_url = urljoin(self.source_url, attrs_map["href"])
        if lowered_tag == "a" and not self.next_url:
            label = clean(attrs_map.get("aria-label") or attrs_map.get("title") or "")
            if re.search(r"\b(next|older|more reviews?)\b", label, re.I) and attrs_map.get("href"):
                self.next_url = urljoin(self.source_url, attrs_map["href"])
        if lowered_tag == "script" and attrs_map.get("type", "").lower().split(";")[0] == "application/ld+json":
            self._stack.append({"kind": "json", "tag": "script", "attrs": attrs_map, "text": []})
            return
        itemprop = attrs_map.get("itemprop", "")
        classes = " ".join(attrs_map.get(name, "") for name in ("class", "id", "data-testid"))
        # Only capture the outermost generic review container. Nested classes
        # such as ``comment`` and ``rating`` belong to the same row and would
        # otherwise become duplicate partial records.
        has_html_parent = any(frame["kind"] == "html" for frame in self._stack)
        if itemprop or (REVIEW_RE.search(classes) and not has_html_parent):
            self._stack.append({"kind": "html", "tag": lowered_tag, "attrs": attrs_map, "text": []})

    def handle_endtag(self, tag: str) -> None:
        if not self._stack or self._stack[-1]["tag"] != tag.lower():
            return
        current = self._stack.pop()
        text = clean(" ".join(current["text"]))
        if current["kind"] == "json":
            self.jsonld.append("".join(current["text"]))
            return
        attrs = current["attrs"]
        itemprop = attrs.get("itemprop", "")
        record: dict[str, str] = {}
        if itemprop == "reviewBody":
            record["review"] = text
        elif itemprop in {"ratingValue", "reviewRating"}:
            record["rating"] = rating_value(text)
        elif itemprop == "author":
            record["reviewer"] = text
        elif itemprop == "datePublished":
            record["review_date"] = text
        elif text and REVIEW_RE.search(" ".join(attrs.get(name, "") for name in ("class", "id", "data-testid"))):
            match = RATING_RE.search(text)
            record["rating"] = rating_value(match.group(0)) if match else ""
            record["review"] = text
        if record:
            self._records.append(record)

    def handle_data(self, data: str) -> None:
        if self._stack:
            self._stack[-1]["text"].append(data)

    def records(self) -> list[dict[str, str]]:
        return self._records


def json_reviews(value: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(value, list):
        for child in value:
            found.extend(json_reviews(child))
    elif isinstance(value, dict):
        if isinstance(value.get("review"), (dict, list)):
            reviews = value["review"] if isinstance(value["review"], list) else [value["review"]]
            brand = value.get("brand", {})
            brand_name = brand.get("name") if isinstance(brand, dict) else brand
            for review in reviews:
                if not isinstance(review, dict):
                    continue
                author = review.get("author", {})
                found.append({
                    "brand": clean(brand_name),
                    "product": clean(value.get("name")),
                    "rating": rating_value(review.get("reviewRating")),
                    "review": clean(review.get("reviewBody")),
                    "review_id": clean(review.get("@id") or review.get("identifier")),
                    "reviewer": clean(author.get("name") if isinstance(author, dict) else author),
                    "review_date": clean(review.get("datePublished")),
                })
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.extend(json_reviews(child))
    return found


def fetch(source: str, timeout: float) -> tuple[str, str]:
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        request = Request(source, headers={"User-Agent": "consumer-review-collector/1.0 (public-page research)"})
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit user URL
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace"), response.geturl()
    path = Path(source).expanduser().resolve()
    return path.read_text(encoding="utf-8"), str(path)


def collect(source: str, max_pages: int, delay: float, timeout: float, brand: str, product: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows: list[dict[str, str]] = []
    seen_pages: set[str] = set()
    seen_ids: set[str] = set()
    current = source
    pages = 0
    duplicate_count = 0
    empty_review_count = 0
    while current and pages < max_pages and current not in seen_pages:
        if pages and delay:
            time.sleep(delay)
        seen_pages.add(current)
        document, resolved = fetch(current, timeout)
        parser = ReviewHTMLParser(resolved)
        parser.feed(document)
        raw_rows = list(parser.records())
        json_rows: list[dict[str, str]] = []
        for blob in parser.jsonld:
            try:
                json_rows.extend(json_reviews(json.loads(blob)))
            except json.JSONDecodeError:
                continue
        # JSON-LD is structured and usually mirrors visible markup. Prefer it
        # when present so one review is not emitted twice from two encodings.
        if json_rows:
            raw_rows = json_rows
        for raw in raw_rows:
            row = {field: clean(raw.get(field)) for field in FIELDS}
            row["brand"] = row["brand"] or brand or "unknown"
            row["product"] = row["product"] or product or "unknown"
            row["source_url"] = resolved
            row["review_id"] = stable_id(row)
            if not row["review"] and not any(row.get(key) for key in ("review_id", "reviewer", "review_date")):
                empty_review_count += 1
                continue
            if row["review_id"] in seen_ids:
                duplicate_count += 1
                continue
            seen_ids.add(row["review_id"])
            rows.append(row)
        current = parser.next_url
        pages += 1
    return rows, {"pages_visited": pages, "rows_extracted": len(rows), "duplicates_removed": duplicate_count, "empty_reviews_skipped": empty_review_count, "next_url": current or ""}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public review-like records from HTML into CSV")
    parser.add_argument("--source", required=True, help="Public http(s) URL or local HTML file")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--brand", default="")
    parser.add_argument("--product", default="")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    if args.max_pages < 1 or args.delay < 0:
        parser.error("--max-pages must be >= 1 and --delay must be >= 0")
    rows, stats = collect(args.source, args.max_pages, args.delay, args.timeout, args.brand, args.product)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"output": str(args.output.resolve()), **stats}, ensure_ascii=False, indent=2))
    if not rows:
        print("No review rows were extracted; inspect the page layout or use a local fixture.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
