---
layout: ailina
title: Ежедневные новости об ИИ
permalink: /ailina/
lang: ru
---

## Свежие выпуски

<p class="archive-intro">Дважды в день, утром и вечером, Horizon отбирает новые модели, полезные инструменты и исследования. Новости получают две оценки: значимость и практичность. Выбирай тему, которую хочется попробовать или обсудить.</p>

{% assign ru_posts = site.posts | where: "lang", "ru" %}
<div class="issue-list">
{% for post in ru_posts limit:30 %}
  <a class="issue-link" href="{{ post.url | relative_url }}">
    <span class="issue-date">{{ post.date | date: "%d.%m.%Y" }}</span>
    <span class="issue-name">{% if post.edition == 'evening' %}Вечернее обновление · 19:00{% else %}Утренний выпуск · 09:00{% endif %}</span>
    <span class="issue-arrow" aria-hidden="true">↗</span>
  </a>
{% else %}
  <p>Первый выпуск готовится. Когда он появится, ссылка отобразится здесь.</p>
{% endfor %}
</div>

<details>
  <summary>Как Horizon оценивает новости</summary>
  <p>Сначала DeepSeek выставляет оценку значимости от 0 до 10. Отдельно определяется практичность: можно ли применить идею в работе или повседневной жизни.</p>
  <p>При отборе практичные новости получают до <strong>+1,5 балла</strong>, материалы TAAFT — ещё <strong>+1,5 балла</strong>. Исходные оценки не подменяются. Просмотры и реакции Telegram помогают оценить интерес аудитории, но сами по себе не подтверждают достоверность.</p>
</details>

<div class="mini-note">Обновления запускаются ежедневно около 09:00 и 19:00 по Москве. Время публикации зависит от выполнения GitHub Actions. Публикации — редакторская подборка для проверки, а не автоматические посты в Telegram.</div>
