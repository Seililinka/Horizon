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
    assert "TAAFT — 1" in new


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
    assert any(group_name(story) == "TAAFT · Устройства с ИИ" for story in parse_stories(updated))


def test_dedup_title_variants_without_url():
    yesterday = Story("i1", "dettato: открытая модель для разбора трека на MIDI-дорожки",
                      "https://example.org/a", "7.0/10", "source content",)
    today = Story("i2", "dettato: открытый инструмент для разбора трека на MIDI-дорожки",
                  "https://example.net/b", "7.0/10", "source content")
    assert is_repeat(today, [yesterday])


def test_karpathy_and_anthropic_have_visible_sections_when_fresh():
    current = digest("21", [
        story("item-ailina-1", "Новый метод Карпаты", "https://karpathy.bearblog.dev/a", source="Andrej Karpathy — Bearblog"),
        story("item-ailina-2", "Новая работа Anthropic", "https://www.anthropic.com/research/example", source="Anthropic Research"),
    ])
    updated, kept, removed = rewrite_digest(current, [])
    assert kept == 2 and removed == 0
    assert "## Андрей Карпаты · Блог" in updated
    assert "## Anthropic · Исследования и релизы" in updated
    assert "Карпаты — 1, Anthropic — 1" in updated


def test_evening_publishes_separate_edition_without_overwriting_morning(tmp_path, monkeypatch):
    import sys
    from scripts.ailina_postprocess import main

    today = "2026-11-22"
    history = tmp_path / "history"
    history.mkdir()
    morning = digest("22", [
        story("item-ailina-1", "Morning AI story", "https://example.org/ai/morning"),
    ])
    (history / f"{today}-summary-ru.md").write_text(morning, encoding="utf-8")
    generated = tmp_path / f"{today}-summary-ru.md"
    generated.write_text(digest("22", [
        story("item-ailina-1", "Morning AI story", "https://example.org/ai/morning"),
        story("item-ailina-2", "New evening AI story", "https://example.org/ai/evening"),
    ]), encoding="utf-8")
    evening = tmp_path / f"{today}-evening-ru.md"
    monkeypatch.setattr(sys, "argv", [
        "ailina_postprocess", "--current", str(generated),
        "--output", str(evening), "--edition", "evening",
        "--history-dir", str(history),
    ])
    main()
    assert not generated.exists()
    result = evening.read_text(encoding="utf-8")
    assert "edition: evening" in result
    import re
    assert re.search(r"date: 2026-11-22 \d{2}:\d{2}:\d{2} \+0300", result) is not None
    assert 'title: "AiLina — вечерние новости ИИ за 2026-11-22"' in result
    assert len(parse_stories(result)) == 1
    assert "New evening AI story" in result
    assert "Morning AI story" not in result
    assert (history / f"{today}-summary-ru.md").read_text(encoding="utf-8") == morning


def test_evening_with_no_new_items_publishes_empty_status(tmp_path, monkeypatch):
    import sys
    from scripts.ailina_postprocess import main

    history = tmp_path / "history"
    history.mkdir()
    (history / "2026-11-22-summary-ru.md").write_text(
        digest("22", [story("item-ailina-1", "Existing", "https://example.org/repeated")]),
        encoding="utf-8",
    )
    generated = tmp_path / "2026-11-22-summary-ru.md"
    generated.write_text(
        digest("22", [story("item-ailina-1", "Existing", "https://example.org/repeated")]),
        encoding="utf-8",
    )
    output = tmp_path / "2026-11-22-evening-ru.md"
    monkeypatch.setattr(sys, "argv", [
        "ailina_postprocess", "--current", str(generated),
        "--output", str(output), "--edition", "evening",
        "--history-dir", str(history),
    ])
    main()
    assert not generated.exists()
    assert "новых материалов, прошедших отбор, нет" in output.read_text(encoding="utf-8")


def test_morning_filters_stories_from_yesterday_evening(tmp_path, monkeypatch):
    import sys
    from scripts.ailina_postprocess import main

    history = tmp_path / "history"
    history.mkdir()
    (history / "2026-11-21-evening-ru.md").write_text(
        digest("21", [story("item-ailina-1", "Already last evening", "https://example.org/old")]),
        encoding="utf-8",
    )
    generated = tmp_path / "2026-11-22-summary-ru.md"
    generated.write_text(digest("22", [
        story("item-ailina-1", "Already last evening", "https://example.org/old"),
        story("item-ailina-2", "New for this morning", "https://example.org/new"),
    ]), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "ailina_postprocess", "--current", str(generated),
        "--history-dir", str(history), "--edition", "morning",
    ])
    main()
    result = generated.read_text(encoding="utf-8")
    assert "New for this morning" in result
    assert "Already last evening" not in result


def test_workflow_runs_one_daily_edition_with_morning_retries():
    from pathlib import Path
    workflow = Path(".github/workflows/ailina-digest.yml").read_text(encoding="utf-8")
    assert workflow.count("- cron:") == 2
    assert "cron: '45 5 * * *'" in workflow
    assert "cron: '15 6 * * *'" in workflow
    assert "name=morning" in workflow
    assert "hours=24" in workflow
    assert "edition=evening" not in workflow
    assert "steps.edition.outputs.post" in workflow
    assert "steps.published.outputs.skip" in workflow
    assert "github.event_name == 'schedule'" not in workflow
    assert "git show" in workflow
    assert "cancel-in-progress: false" in workflow
