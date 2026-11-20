# AiLina Horizon: запуск с iPhone

Персональная версия Horizon с русскоязычным ежедневным AI-дайджестом. Новости собираются из открытых источников, **не публикуются автоматически в Telegram**.

## 1. Включить Actions в форке

Откройте [Actions](https://github.com/Seililinka/Horizon/actions). Если GitHub предлагает включить workflows для форка, подтвердите разрешение.

## 2. Добавить API-ключ DeepSeek

1. Создайте ключ в [DeepSeek Platform](https://platform.deepseek.com/api_keys). Доступность и стоимость зависят от поставщика.
2. Откройте [Actions secrets](https://github.com/Seililinka/Horizon/settings/secrets/actions).
3. Нажмите **New repository secret**.
4. **Name:** `DEEPSEEK_API_KEY` (именно этот Repository secret читает GitHub Actions).
5. **Secret:** вставьте ключ и нажмите **Add secret**.

**Никогда не вставляйте ключ в файлы репозитория, публичные комментарии или чат.** GitHub Secrets скрывает его от публичного исходного кода.

## 3. Первый запуск

[Actions → AiLina — Daily AI Digest](https://github.com/Seililinka/Horizon/actions/workflows/ailina-digest.yml) → **Run workflow** → **Run workflow**. Откройте результат, убедитесь, что шаги зелёные. При ошибке смотрите лог конкретного шага. GitHub автоматически выполняет запланированные задачи с возможной задержкой.

## 4. Включить GitHub Pages

Откройте [Settings → Pages](https://github.com/Seililinka/Horizon/settings/pages): **Deploy from a branch**, ветка **gh-pages**, папка **/(root)**. Ветка gh-pages появится после первого успешного развёртывания сайта.

Страница русских подборок: https://seililinka.github.io/Horizon/ailina/

## Настройки

- `data/config.ailina.json` — источники, модель, лимит 9 новостей, фильтры.
- `profiles/ailina/` — правила русскоязычной редакции, оценки и кратких объяснений.
- `.github/workflows/ailina-digest.yml` — автоматический запуск в 06:00 UTC (09:00 по Москве).
- `docs/ailina.md` — стартовая страница русских выпусков.

**Примечание:** без `DEEPSEEK_API_KEY` workflow завершается с ошибкой; при недействительном ключе виден HTTP 401. Оплата API у DeepSeek отдельно от подписки ChatGPT.

## Приоритетные новости TAAFT

- Отдельный RSS-источник в `data/config.ailina.json`: `https://raw.githubusercontent.com/Seililinka/Horizon/main/data/taaft-feed.xml`.
- Публичный сайт рассылки TAAFT блокирует автоматические запросы GitHub (HTTP 403). Поэтому RSS-источник собирается из **подключённого Gmail** через отдельную запланированную задачу ChatGPT (08:20 по Москве), а не скачивается напрямую с Beehiiv.
- Публикуются только краткие самостоятельные пересказы 3–6 новостей из выпуска; без полного текста писем, личных данных и отслеживающих ссылок. Если свежего письма нет, старый RSS не изменяется.
- Рейтинг TAAFT получает **+1,5 балла только при отборе**. Оценка значимости от DeepSeek не изменяется. До трёх новостей TAAFT попадают в отдельный приоритетный раздел, общий лимит — 9.
- GitHub Actions запускает Horizon ежедневно в **09:00 по Москве** и читает актуальный RSS. Если задача ChatGPT не смогла обновить RSS, в Horizon будут доступные прежние записи (в пределах окна свежести).
- Источники и издательские утверждения нуждаются в проверке перед публикацией в Telegram.
