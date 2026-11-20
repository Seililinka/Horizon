---
layout: default
title: AiLina — ИИ-радар
permalink: /ailina/
---

# AiLina — ежедневный ИИ-радар

Короткие новости об ИИ на русском: модели, инструменты, агенты, исследования и практическое применение. Каждый материал содержит ссылку на первоисточник, оценку значимости и идею для поста.

> Подборка обновляется по расписанию, только если в GitHub Actions настроен ключ DeepSeek. Это черновики для проверки, **не автоматическая публикация** в Telegram.

## Свежие подборки

{% assign ru_posts = site.posts | where: "lang", "ru" %}
{% for post in ru_posts limit:30 %}
- [{{ post.date | date: "%d.%m.%Y" }} — новости ИИ]({{ post.url | relative_url }})
{% else %}
Пока нет готовых выпусков. После первого успешного запуска они появятся здесь.
{% endfor %}

---

[Репозиторий и настройки](https://github.com/Seililinka/Horizon) · [Запуск вручную](https://github.com/Seililinka/Horizon/actions/workflows/ailina-digest.yml)
