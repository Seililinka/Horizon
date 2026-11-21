"""Make AiLina's daily Russian digest fresh, with TAAFT clearly separated.

Runs after the normal Horizon pipeline and before GitHub Pages publication.
Uses only already-published prior digests, never private user data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
from urllib.parse import urlsplit


ANCHOR = re.compile(r'(?m)^<a id="(?P<anchor>item-[A-Za-z0-9_-]+)"></a>\s*\n')
TITLE = re.compile(r'(?m)^### \[(?P<title>.+?)\]\((?P<url>https?://[^)]+)\) ⭐️ (?P<score>[\d.]+/10)')
HEAD_COUNT = re.compile(r"Из (\d+) публикаций отобрано \d+ [^\n]+")
GENERIC_HOSTS = {"newsletter.theresanaiforthat.com"}
DEVICE_WORDS = (
    "роботакси", "дрон", "гаджет", "устройств", "очки", "наушник",
    "носим", "диктофон", "смарт-час", "умн", "робот-пылесос",
    "доставка дронами",
)


@dataclass(frozen=True)
class Story:
    anchor: str
    title: str
    url: str
    score: str
    text: str

    @property
    def taaft(self) -> bool:
        return bool(re.search(r"(?m)^rss · TAAFT ·", self.text))


def parse_stories(markdown: str) -> list[Story]:
    anchors = list(ANCHOR.finditer(markdown))
    stories: list[Story] = []
    for i, a in enumerate(anchors):
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(markdown)
        body = markdown[a.start():end]
        # The generated digest separates each item with a Markdown divider.
        body = re.split(r"(?m)^---\s*$", body, maxsplit=1)[0].strip()
        heading = TITLE.search(body)
        if heading:
            stories.append(Story(
                anchor=a["anchor"],
                title=heading["title"],
                url=heading["url"],
                score=heading["score"],
                text=body,
            ))
    return stories


def title_key(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def normalized_url(url: str) -> str | None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not host or host in GENERIC_HOSTS:
        # Different TAAFT stories may share an issue or homepage permalink.
        return None
    if host.startswith("www."):
        host = host[4:]
    return f"{host}{parts.path.rstrip('/').casefold()}"


def is_repeat(current: Story, history: list[Story]) -> bool:
    curr_title = title_key(current.title)
    curr_url = normalized_url(current.url)
    for earlier in history:
        if curr_url and curr_url == normalized_url(earlier.url):
            return True
        previous_title = title_key(earlier.title)
        if curr_title == previous_title:
            return True
        if len(curr_title) >= 27 and len(previous_title) >= 27:
            if SequenceMatcher(None, curr_title, previous_title).ratio() >= 0.78:
                return True
    return False


def group_name(story: Story) -> str:
    if re.search(r"(?m)^rss · Andrej Karpathy", story.text):
        return "Андрей Карпаты · Блог"
    if re.search(r"(?m)^rss · Anthropic ", story.text):
        return "Anthropic · Исследования и релизы"
    if not story.taaft:
        return "Остальные новые новости"
    title = title_key(story.title)
    if "промпт дня" in title or "практический промпт" in title:
        return "TAAFT · Промпт дня"
    if any(word in title for word in DEVICE_WORDS):
        return "TAAFT · Устройства с ИИ"
    return "TAAFT · Новости и инструменты"


GROUP_ORDER = (
    "TAAFT · Новости и инструменты",
    "TAAFT · Устройства с ИИ",
    "TAAFT · Промпт дня",
    "Андрей Карпаты · Блог",
    "Anthropic · Исследования и релизы",
    "Остальные новые новости",
)


def rewrite_digest(current: str, previous: list[str]) -> tuple[str, int, int]:
    all_stories = parse_stories(current)
    if not all_stories:
        return current, 0, 0
    history = [story for markdown in previous for story in parse_stories(markdown)]
    kept = [story for story in all_stories if not is_repeat(story, history)]
    removed = len(all_stories) - len(kept)

    front_match = re.match(r"\A(---\n.*?\n---\n)", current, flags=re.S)
    front = front_match.group(1) if front_match else ""
    total_match = HEAD_COUNT.search(current)
    fetched = int(total_match.group(1)) if total_match else len(all_stories)
    date_match = re.search(r"(?m)^date: (\d{4}-\d{2}-\d{2})$", front)
    date_label = date_match.group(1) if date_match else "сегодня"

    groups = {name: [] for name in GROUP_ORDER}
    for story in kept:
        groups[group_name(story)].append(story)

    taaft_count = sum(story.taaft for story in kept)
    karpathy_count = len(groups["Андрей Карпаты · Блог"])
    anthropic_count = len(groups["Anthropic · Исследования и релизы"])
    parts = [
        front,
        f"\n> Из {fetched} публикаций отобрано {len(kept)} новых тем. "
        f"Повторы предыдущих выпусков исключены ({removed}).\n\n",
        f"**AiLina — свежие новости · {date_label}**\n\n",
        f"**Источники дня:** TAAFT — {taaft_count}, "
        f"Карпаты — {karpathy_count}, Anthropic — {anthropic_count}. "
        "Показаны только новости, прошедшие отбор; "
        "если у источника не было свежих материалов, раздел не заполняется старыми.\n\n",
        "---\n\n",
        "## Содержание выпуска\n\n",
    ]
    index = 0
    for name in GROUP_ORDER:
        if not groups[name]:
            continue
        parts.append(f"**{name}**\n\n")
        for story in groups[name]:
            index += 1
            parts.append(f"{index}. [{story.title}](#{story.anchor}) ⭐️ {story.score}\n")
        parts.append("\n")
    parts.append("---\n\n")
    for name in GROUP_ORDER:
        if not groups[name]:
            continue
        parts.append(f"## {name}\n\n")
        for story in groups[name]:
            parts.append(story.text.rstrip() + "\n\n---\n\n")
    return "".join(parts), len(kept), removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--history-dir", required=True, type=Path)
    args = parser.parse_args()
    if not args.current.is_file():
        raise SystemExit(f"Missing current digest: {args.current}")
    previous = [
        path.read_text(encoding="utf-8")
        for path in sorted(args.history_dir.glob("*-summary-ru.md"))
    ] if args.history_dir.is_dir() else []
    original = args.current.read_text(encoding="utf-8")
    revised, kept, removed = rewrite_digest(original, previous)
    if kept:
        args.current.write_text(revised, encoding="utf-8")
    print(f"AiLina freshness filter: {kept} new stories, {removed} prior-issue repeats removed; "
          f"{len(previous)} prior digests checked.")


if __name__ == "__main__":
    main()
