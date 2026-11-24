"""Add lightweight, optional publisher previews to AiLina markdown posts.

No AI, image generation, image downloads, or external thumbnail service.
Only public HTTPS image URLs explicitly advertised by the article are used.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from html import escape, unescape
from html.parser import HTMLParser
import ipaddress
from pathlib import Path
import re
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from scripts.ailina_postprocess import parse_stories, TITLE

MAX_PREVIEWS = 15
MAX_HTML = 512 * 1024
GENERIC = {"newsletter.theresanaiforthat.com", "t.co", "bit.ly", "tinyurl.com"}
MARKER = re.compile(r'\n\n<div class="ailina-preview-data" data-image="[^"]*"></div>')


def public_url(value: str, *, image: bool = False) -> str | None:
    """Reject credentials, non-web schemes, local addresses and unsafe ports."""
    try:
        p = urlsplit(value.strip())
        host = p.hostname
        if not host or p.username or p.password or p.scheme not in ("http", "https"):
            return None
        if image and p.scheme != "https":
            return None
        if p.port not in (None, 80, 443) or "." not in host:
            return None
        addresses = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            return None
        return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
    except (ValueError, OSError, UnicodeError):
        return None


class PublicRedirect(HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe = public_url(newurl)
        if not safe:
            raise ValueError("Redirect to non-public URL")
        return super().redirect_request(req, fp, code, msg, headers, safe)


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}
        self.finished = False

    def handle_endtag(self, tag):
        if tag == "head":
            self.finished = True

    def handle_starttag(self, tag, attrs):
        if self.finished:
            return
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            value = a.get("content") or ""
            if key in ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src") and value:
                self.values.setdefault(key, value)
        elif tag == "link" and (a.get("rel") or "").lower() == "image_src":
            self.values.setdefault("image_src", a.get("href") or "")


def candidates(html: str, page_url: str) -> list[str]:
    parser = Metadata()
    parser.feed(html)
    return [
        urljoin(page_url, parser.values[k])
        for k in ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src", "image_src")
        if parser.values.get(k)
    ]


def find_preview(url: str) -> str:
    """Best effort: a missing or blocked preview never blocks news publication."""
    try:
        url = unescape(url)
        parsed = urlsplit(url)
        if (parsed.hostname or "").lower() in GENERIC or parsed.path in ("", "/"):
            return ""
        safe = public_url(url)
        if not safe:
            return ""
        opener = build_opener(ProxyHandler({}), PublicRedirect())
        req = Request(safe, headers={"User-Agent": "AiLinaPreview/1.0", "Accept": "text/html,application/xhtml+xml"})
        with opener.open(req, timeout=7) as response:
            if response.headers.get_content_type() not in ("text/html", "application/xhtml+xml"):
                return ""
            raw = response.read(MAX_HTML)
            html = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            final = response.geturl()
        for url in candidates(html, final):
            if len(url) <= 2048 and (safe_image := public_url(url, image=True)):
                return safe_image
    except Exception:
        pass
    return ""


def add_previews(markdown: str, lookup=find_preview, limit: int = MAX_PREVIEWS) -> tuple[str, int, int]:
    # Re-running a preview-only update must not create duplicate elements.
    markdown = MARKER.sub("", markdown)
    stories = parse_stories(markdown)[:limit]
    with ThreadPoolExecutor(max_workers=5) as pool:
        urls = list(pool.map(lookup, [s.url for s in stories]))
    by_anchor = dict(zip((s.anchor for s in stories), urls))
    anchor = re.compile(r'(?m)^<a id="(item-[A-Za-z0-9_-]+)"></a>\s*\n')
    parts = []
    last = 0
    for m in anchor.finditer(markdown):
        if m[1] not in by_anchor:
            continue
        heading = TITLE.match(markdown, m.end())
        if not heading:
            continue
        end = markdown.find("\n", heading.end())
        if end < 0:
            end = len(markdown)
        parts.append(markdown[last:end])
        parts.append('\n\n<div class="ailina-preview-data" data-image="' + escape(by_anchor[m[1]], quote=True) + '"></div>')
        last = end
    parts.append(markdown[last:])
    return "".join(parts), len(stories), sum(bool(url) for url in urls)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("post", type=Path)
    args = parser.parse_args()
    original = args.post.read_text(encoding="utf-8")
    updated, count, found = add_previews(original)
    args.post.write_text(updated, encoding="utf-8")
    print(f"AiLina previews: {found}/{count} publisher metadata images; {count-found} fallback cards.")


if __name__ == "__main__":
    main()
