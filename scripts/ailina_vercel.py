"""Build the existing AiLina reader on Vercel, independently of GitHub Actions.

The public archive is carried forward from the last successful production
deployment. Without a DeepSeek key, the initial deployment migrates the old
archive only. Failed collection or archive retrieval never publishes a partial
replacement of the last good site.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit
from urllib.request import urlopen, Request

import bleach
import markdown

from scripts.ailina_postprocess import rewrite_digest
from scripts.ailina_previews import add_previews

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public"
POST = re.compile(r"(\d{4}-\d{2}-\d{2})-(summary|evening)-ru\.md")
MOSCOW = timezone(timedelta(hours=3))
MAX_ARCHIVE = 60 * 1024 * 1024


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def historical_posts():
    """Read original published issues, never require a write token."""
    command("git", "fetch", "--no-tags", "--depth=1", "origin", "gh-pages")
    paths = command("git", "ls-tree", "-r", "--name-only", "FETCH_HEAD", "_posts").splitlines()
    return {
        Path(path).name: command("git", "show", f"FETCH_HEAD:{path}")
        for path in paths if POST.fullmatch(Path(path).name)
    }


def previous_archive():
    base = os.environ.get("AILINA_ARCHIVE_URL", "").rstrip("/")
    if not base:
        if os.environ.get("DEEPSEEK_API_KEY") and os.environ.get("VERCEL_ENV") == "production":
            raise RuntimeError("Configure AILINA_ARCHIVE_URL with the first successful public Vercel site before enabling collection.")
        return {}
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or
        not parsed.hostname.endswith(".vercel.app") or parsed.path or
        parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("AILINA_ARCHIVE_URL must be the public Vercel production origin")
    request = Request(base + "/archive.json", headers={"User-Agent": "AiLinaArchive/1.0"})
    with urlopen(request, timeout=30) as response:
        if urlsplit(response.geturl()).hostname != parsed.hostname:
            raise RuntimeError("Archive redirect is not allowed")
        data = response.read(MAX_ARCHIVE + 1)
    if len(data) > MAX_ARCHIVE:
        raise RuntimeError("Archive exceeds safe size limit")
    archive = json.loads(data)
    if not isinstance(archive, dict) or archive.get("version") != 1 or not isinstance(archive.get("posts"), dict):
        raise ValueError("Invalid public archive manifest")
    posts = archive["posts"]
    if not posts or any(not POST.fullmatch(k) or not isinstance(v, str) or not v.startswith("---\n") for k,v in posts.items()):
        raise ValueError("Invalid archived issue")
    return posts


def collect(posts, now):
    today = now.strftime("%Y-%m-%d")
    filename = f"{today}-summary-ru.md"
    marker = (ROOT / "data/ailina-refresh-request.txt").read_text(encoding="utf-8")
    if os.environ.get("VERCEL_ENV") != "production" or not os.environ.get("DEEPSEEK_API_KEY"):
        print("Archive-only build: production collection is not enabled.")
        return
    if filename in posts:
        print("Today's issue already exists: skip DeepSeek.")
        return
    if today not in marker:
        print("Awaiting today's TAAFT refresh marker.")
        return
    # Horizon uses UTC for filenames; during the 08:00 Moscow collection
    # UTC and Moscow have the same calendar date.
    if datetime.now(timezone.utc).strftime("%Y-%m-%d") != today:
        raise RuntimeError("Daily collector is outside the supported morning window")
    subprocess.run(["uv", "run", "--no-sync", "horizon", "--config",
                    "data/config.ailina.json", "--hours", "24"],
                   cwd=ROOT, check=True, timeout=1200)
    generated = ROOT / "docs/_posts" / filename
    if not generated.is_file():
        raise RuntimeError("Collector did not generate the expected daily post")
    current = generated.read_text(encoding="utf-8")
    recent = [v for k,v in posts.items() if (now.date() - timedelta(days=3)).isoformat() <= k[:10] < today]
    revised, kept, removed = rewrite_digest(current, recent)
    if kept == 0 and removed == 0:
        raise RuntimeError("No parseable stories: keep the previous release")
    revised, count, found = add_previews(revised)
    posts[filename] = revised
    print(f"Daily issue: {kept} new, {removed} repeated, {found}/{count} publisher previews")


def issue_url(name):
    match = POST.fullmatch(name)
    day, part = match.groups()
    return "/" + day.replace("-", "/") + f"/{part}-ru.html"


def render_markdown(raw):
    front = re.match(r"\A---\n.*?\n---\n", raw, flags=re.S)
    body = raw[front.end():] if front else raw
    html = markdown.markdown(body, extensions=["tables", "fenced_code", "sane_lists"])
    return bleach.clean(html, tags={
        "h1","h2","h3","h4","h5","h6","p","br","hr","blockquote","ol","ul","li",
        "a","strong","b","em","i","code","pre","div","span","table","thead","tbody","tr",
        "td","th","details","summary","s","del","img",
    }, attributes={"a":["href","title","id","rel"],"div":["class","data-image"],
                   "span":["class"],"code":["class"],"img":["src","alt","title","loading"],
                   "ol":["start"],"h2":["id"],"h3":["id"]},
        protocols=["http","https","mailto"], strip=True)


def layout(title, content, issue=False):
    template = (ROOT / "docs/_layouts/ailina.html").read_text(encoding="utf-8")
    template = template.replace("{{ page.title | default: 'ИИ-радар' | escape }}", escape(title))
    template = template.replace("{% if page.date %}is-issue{% else %}is-archive{% endif %}", "is-issue" if issue else "is-archive")
    template = re.sub(r"\{\{\s*'([^']+)'\s*\|\s*relative_url\s*\}\}", lambda m:m[1], template)
    # Preserve the existing design, rather than exposing the Jekyll template.
    if "{{ content }}" not in template:
        raise ValueError("AiLina layout changed")
    return template.replace("{{ content }}", content)


def render(posts):
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "docs/assets", OUT / "assets", dirs_exist_ok=True)
    links = []
    for name in sorted(posts, key=lambda k:(k[:10], "evening" in k), reverse=True):
        day, part = POST.fullmatch(name).groups()
        url = issue_url(name)
        label = "Вечерний выпуск (архив)" if part == "evening" else "Ежедневный выпуск"
        ru_date = datetime.strptime(day,"%Y-%m-%d").strftime("%d.%m.%Y")
        links.append(f'<a class="issue-link" href="{url}"><span class="issue-date">{ru_date}</span>'
                     f'<span class="issue-name">{label}</span><span class="issue-arrow" aria-hidden="true">↗</span></a>')
        dest = OUT / url.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(layout(f"{label} · {ru_date}", render_markdown(posts[name]), True), encoding="utf-8")
    archive = ("<h2>Свежие выпуски</h2>"
               '<p class="archive-intro">Каждое утро Horizon отбирает новые модели, полезные инструменты и исследования. '
               'Новости получают оценки значимости и практичности.</p><div class="issue-list">'
               + "\n".join(links) + '</div><div class="mini-note">Сбор начинается в 08:00 МСК. '
               'Новый выпуск появляется после завершения обработки.</div>')
    page = layout("Ежедневные новости об ИИ", archive)
    (OUT / "ailina").mkdir(exist_ok=True)
    (OUT / "ailina/index.html").write_text(page, encoding="utf-8")
    (OUT / "index.html").write_text(page, encoding="utf-8")
    # Only already-public editorial markdown is persisted here, not raw Gmail,
    # provider secrets, storage databases, logs or the application source.
    (OUT / "archive.json").write_text(json.dumps({"version":1,"posts":posts},ensure_ascii=False),encoding="utf-8")
    # Keep the existing feed link usable with a standards-compliant public feed.
    from xml.etree import ElementTree as ET
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss,"channel")
    base = os.environ.get("AILINA_ARCHIVE_URL") or ("https://" + os.environ.get("VERCEL_PROJECT_PRODUCTION_URL",""))
    if not base.startswith("https://") or base == "https://":
        base = "https://seililinka.github.io/Horizon"
    ET.SubElement(channel,"title").text = "AiLina — ИИ-радар"
    ET.SubElement(channel,"link").text = base + "/ailina/"
    ET.SubElement(channel,"description").text = "Ежедневные новости ИИ"
    for name in sorted(posts, reverse=True)[:30]:
        item=ET.SubElement(channel,"item")
        ET.SubElement(item,"title").text=f"AiLina — {name[:10]}"
        ET.SubElement(item,"link").text=base+issue_url(name)
        ET.SubElement(item,"guid").text=base+issue_url(name)
    ET.ElementTree(rss).write(OUT/"feed.xml",encoding="utf-8",xml_declaration=True)
    print(f"Rendered {len(posts)} public archived issues")


def main():
    posts = historical_posts()
    posts.update(previous_archive())
    if not posts:
        raise RuntimeError("Original archive is unavailable")
    collect(posts, datetime.now(MOSCOW))
    render(posts)


if __name__ == "__main__":
    main()
