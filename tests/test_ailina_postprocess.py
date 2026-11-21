"""Regression tests: prior-day repeats must not displace fresh TAAFT stories."""
from scripts.ailina_postprocess import (
    Story, group_name, is_repeat, parse_stories, rewrite_digest,
)


def story(anchor: str, title: str, url: str, source="TAAFT") -> str:
    return (
        f'<a id="{anchor}"></a>\n'
        f'### [{title}]({url}) ⭐️ 7.0/10\n\n'
        f'Short news body.\n\nrss · {source} · Nov 21, 04:00\n\n'
        '**Практичность:** 8/10\n\n---\n\n'
    )


def digest(day: str, bodies: list[str]) -> str:
    toc = "\n".join(f"{i}. [Item](#item-ailina-{i})" for i in range(1, len(bodies) + 1))
    return (
        "---\nlayout: ailina\n"
        f"date: 2026-11-{day}\nlang: ru\n---\n\n"
        f"> Из 100 публикаций отобрано {len(bodies)} значимых новостей.\n\n"
        "---\n\n"
        "**AiLina — ИИ-радар**\n" + toc + "\n\n---\n\n"
        "## AiLina — ИИ-радар\n\n" + "".join(bodies)
    )


def test_removes_previous_story_by_exact_article_link():
    before = digest("20", [story("item-ailina-1", "Déta", "https://example.org/news")])
    now = digest("21", [
        story("item-ailina-1", "Другое название того же материала", "https://example.org/news"),
        story("item-ailina-2", "Новая полезная новость", "https://example.org/new")
    ])
    new, kept, removed = rewrite_digest(now, [before])
    assert (kept, removed) == (1, 1)
    assert "Другое название того же материала" not in new
    assert "Новая полезная новость" in new
    assert "Из TAAFT сегодня: 1" in new


def test_taaft_stories_with_same_issue_permalink_are_distinct():
    link = "https://newsletter.theresanaiforthat.com/p/claude-ignores-your-think-hard"
    before = digest("20", [story("item-ailina-1", "Промпт дня TAAFT: диагностика бытовой техники", link)])
    now = digest("21", [
        story("item-ailina-1", "Промпт дня TAAFT: ИИ для диагностики бытовой техники", link),
        story("item-ailina-2", "TAAFT: новое исследование архитектуры агентов", link),
    ])
    updated, kept, removed = rewrite_digest(now, [before])
    assert (kept, removed) == (1, 1)
    assert "диагностики бытовой техники" not in updated
    assert "новое исследование архитектуры агентов" in updated


def test_explicit_taaft_sections():
    now = digest("21", [
        story("item-ailina-1", "Uber запустил роботакси Zoox", "https://uber.com/story"),
        story("item-ailina-2", "Промпт дня TAAFT: обучаемся с ИИ", "https://newsletter.theresanaiforthat.com/"),
        story("item-ailina-3", "Google выпустил новую модель", "https://google.com/post"),
        story("item-ailina-4", "Обновление open source", "https://github.com/openai/example", source="GitHub"),
    ])
    updated, kept, removed = rewrite_digest(now, [])
    assert (kept, removed) == (4, 0)
    assert "## TAAFT · Устройства с ИИ" in updated
    assert "## TAAFT · Промпт дня" in updated
    assert "## TAAFT · Новости и инструменты" in updated
    assert "## Остальные новые новости" in updated
    assert len(parse_stories(updated)) == 4
    assert group_name(parse_stories(updated)[0]) == "TAAFT · Устройства с ИИ"


def test_dedup_title_variants_without_url():
    yesterday = Story("i1", "dettato: открытая модель для разбора трека на MIDI-дорожки",
                      "https://example.org/a", "",)
    today = Story("i2", "dettato: открытый инструмент для разбора трека на MIDI-дорожки",
                  "https://example.net/b", "")
    assert is_repeat(today, [yesterday])
