# News Digest Bot

Telegram-бот для автоматической агрегации и саммаризации новостей из публичных Telegram-каналов.

## Стек

- **Bot**: aiogram 3.x
- **Scraper**: Pyrogram (userbot)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL
- **AI**: OpenRouter (Qwen)

## Полная инструкция по запуску

### 1. Подготовка

```bash
# Скопировать и заполнить .env
cp .env.example .env
```

Заполнить в `.env`:
- `BOT_TOKEN` — от @BotFather
- `API_ID`, `API_HASH`, `PHONE_NUMBER` — от [my.telegram.org](https://my.telegram.org)
- `OPENROUTER_API_KEY` — от [openrouter.ai](https://openrouter.ai)
- `POSTGRES_PASSWORD` — придумать

### 2. Создать Pyrogram сессию (один раз)

```bash
# Установить зависимости
uv sync

# Авторизоваться в Telegram
uv run python -m lib.scripts.auth_pyrogram
```

Ввести код из Telegram. Создастся файл `digest_bot.session`.

### 3. Запустить инфраструктуру

```bash
docker compose up -d postgres redis
```

### 4. Применить миграции

```bash
uv run python -m lib.scripts.migrate
```

### 5. Запустить всё

```bash
docker compose up -d --build
```

### 6. Проверить логи

```bash
docker-compose logs -f bot
docker-compose logs -f worker
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация и приветствие |
| `/set_channel <username>` | Установить канал для дайджеста |
| `/digest` | Получить дайджест сейчас |
| `/settings` | Настройки рассылки |

## Локальная разработка

```bash
# Запустить только БД и Redis
docker-compose up -d postgres redis

# Применить миграции
uv run python -m lib.scripts.migrate

# Запустить бота
uv run python -m lib.bot.main

# Запустить воркер (в отдельном терминале)
uv run celery -A lib.worker.celery_app worker --loglevel=info

# Запустить планировщик (в отдельном терминале)
uv run celery -A lib.worker.celery_app beat --loglevel=info
```
