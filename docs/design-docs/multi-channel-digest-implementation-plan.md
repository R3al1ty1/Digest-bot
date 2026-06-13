# План реализации: дайджест из нескольких каналов

## 1. Цель

Реализовать поддержку до 5 Telegram-каналов и до 5 пользовательских интересов/сфер. Дайджест должен собирать посты из всех активных каналов пользователя, группировать итог по интересам и сохранять ссылки на источники.

## 2. Принципы реализации

- Делать маленькими PR/коммитами: сначала данные, потом bot commands, потом worker/AI.
- Не удалять `users.target_channel`.
- Не добавлять callback UI, REST API, новые очереди или новый ORM-паттерн.
- Использовать текущие подходы проекта: aiogram handlers, SQLAlchemy models/repositories, `UnitOfWork`, Celery tasks, Pyrogram scraper, OpenRouter client.
- Лимиты фиксированные в коде: 5 каналов, 5 интересов.
- Частично доступные каналы в `/set_channels` сохранять: доступные в БД, недоступные в ответ пользователю.
- Моки внешних сервисов только в тестах.

## 3. Этапы работ

### Этап 1. Миграция БД и модели

Файлы:

- `migrations/[next]_multi_channel_digest.sql`
- `lib/db/models/models.py`

Задачи:

- Добавить таблицу `user_channels`.
- Добавить таблицу `digest_interests`.
- Добавить поля `digest_logs.channels_count`, `digest_logs.channels`, `digest_logs.interests`.
- Перенести существующие `users.target_channel` в `user_channels`.
- Добавить SQLAlchemy-модели `UserChannel` и `DigestInterest`.
- Добавить relationships от `User` к `user_channels` и `digest_interests`.
- Оставить `users.target_channel` без удаления.

Acceptance criteria:

- Миграция идемпотентна через `IF NOT EXISTS`.
- Существующий один канал пользователя сохраняется в `user_channels`.
- Старые поля `digest_logs.channel`, `users.target_channel` остаются рабочими.

Проверка:

```bash
rtk uv run python -m lib.scripts.migrate
```

### Этап 2. Репозитории и UnitOfWork

Файлы:

- `lib/db/repositories/user_channel.py`
- `lib/db/repositories/digest_interest.py`
- `lib/db/repositories/digest.py`
- `lib/core/uow.py`

Задачи:

- Создать `UserChannelRepository`.
- Создать `DigestInterestRepository`.
- Подключить оба репозитория в `UnitOfWork`.
- Расширить `DigestLogRepository.create` параметрами `channels`, `channels_count`, `interests`.
- Добавить выборку активных пользователей с активными каналами и интересами для scheduled flow.

Минимальные методы:

```python
class UserChannelRepository:
    async def list_active_by_user(self, user_id: int) -> list[UserChannel]: ...
    async def count_active_by_user(self, user_id: int) -> int: ...
    async def replace_for_user(self, user_id: int, channels: list[str]) -> list[UserChannel]: ...
    async def add_channel(self, user_id: int, channel: str) -> UserChannel: ...
    async def remove_channel(self, user_id: int, channel: str) -> bool: ...
    async def get_users_by_schedule_time(self, hour: int, minute: int) -> list[User]: ...


class DigestInterestRepository:
    async def list_by_user(self, user_id: int) -> list[DigestInterest]: ...
    async def replace_for_user(self, user_id: int, interests: list[str]) -> list[DigestInterest]: ...
```

Acceptance criteria:

- Репозитории не коммитят сами, если текущий `UnitOfWork` берет commit на себя.
- Методы возвращают plain model lists, без SQLAlchemy result leaking.
- Удаление канала затрагивает только текущего пользователя.

Проверка:

```bash
rtk uv run pytest
```

### Этап 3. Парсинг и сервисы настроек

Файлы:

- `lib/services/channels.py`
- `lib/services/interests.py`
- `lib/core/constants.py`

Задачи:

- Добавить константы `MAX_CHANNELS_PER_USER = 5`, `MAX_INTERESTS_PER_USER = 5`.
- Реализовать `normalize_channel_username`.
- Реализовать `parse_channel_list`.
- Реализовать `parse_interest_list`.
- Реализовать сервис добавления/удаления/замены каналов.
- Реализовать сервис замены интересов.

Правила:

- Канал хранится без `@`.
- Каналы dedupe по normalized username.
- Интересы trim, collapse whitespace, dedupe case-insensitive.
- `/set_channels` допускает частичный успех.
- `/set_interests` заменяет весь список интересов.

Acceptance criteria:

- Больше 5 каналов или интересов дает validation error.
- Пустой список не сохраняется.
- Недоступный канал не попадает в БД.

Проверка:

```bash
rtk uv run pytest
```

### Этап 4. Bot commands для каналов

Файлы:

- `lib/bot/handlers/channel.py`
- `lib/bot/handlers/__init__.py`
- `lib/bot/main.py`

Задачи:

- Обновить `/set_channel` или оставить как legacy alias на `/set_channels` с одним каналом.
- Добавить `/set_channels`.
- Добавить `/add_channel`.
- Добавить `/remove_channel`.
- Добавить `/channels`.
- Использовать `test_channel_access` для проверки доступности.
- Для `/set_channels` показать `saved_channels` и `skipped_channels`.

UX-сообщения:

- Если все каналы недоступны: "Не удалось получить доступ ни к одному каналу."
- Если часть сохранена: показать сохраненные и пропущенные списки.
- Если список пуст: показать пример `/set_channels @channel_one @channel_two`.

Acceptance criteria:

- Все команды работают только с `message.from_user.id`.
- `/set_channels` с 6 каналами не пишет в БД.
- `/remove_channel` чужой канал не трогает.

Проверка:

```bash
rtk uv run pytest
```

### Этап 5. Bot commands для интересов и help

Файлы:

- `lib/bot/handlers/interests.py`
- `lib/bot/handlers/help_cmd.py`
- `lib/bot/handlers/__init__.py`
- `lib/bot/main.py`

Задачи:

- Добавить `/set_interests`.
- Добавить `/interests`.
- Обновить `/help`.
- Зарегистрировать новый router.

Команды в `/help`:

- `/set_channels @channel_one @channel_two`
- `/add_channel @channel_three`
- `/remove_channel @channel_one`
- `/channels`
- `/set_interests финансы, технологии`
- `/interests`
- `/digest`

Acceptance criteria:

- Больше 5 интересов не сохраняются.
- `/digest` без интересов просит вызвать `/set_interests`.
- `/help` показывает команды настройки новой фичи.

Проверка:

```bash
rtk uv run pytest
```

### Этап 6. AI client и prompt

Файлы:

- `lib/services/reducer/ai_client.py`
- `lib/core/constants.py`

Задачи:

- Добавить `generate_interest_based_digest(posts_by_channel, interests)`.
- Сохранить текущий `generate_digest(posts)` для legacy/fallback.
- Формировать prompt с:
  - списком интересов пользователя;
  - постами, сгруппированными по каналам;
  - требованием группировать итог по интересам;
  - требованием сохранять ссылки на источники как сейчас.
- Ограничить размер входа: truncation постов оставить, общий лимит постов ввести в сервисе.

Acceptance criteria:

- Если посты пустые, возвращается текущий fallback.
- Ответ просит AI не группировать итог по каналам.
- Ссылки `https://t.me/...` остаются в prompt.

Проверка:

```bash
rtk uv run pytest
```

### Этап 7. Worker и digest flow

Файлы:

- `lib/bot/handlers/digest.py`
- `lib/worker/tasks.py`
- `lib/db/repositories/digest.py`

Задачи:

- Обновить `/digest`: загрузить каналы и интересы.
- Ставить Celery task с `user_id`, `channels`, `interests`.
- Обновить `generate_digest_task`.
- Обновить `_generate_digest_for_user`.
- Собирать посты по каждому каналу.
- Частичные ошибки каналов логировать, но не валить весь digest, если есть данные.
- Сохранять `digest_logs.channels`, `channels_count`, `interests`.
- Обновить `scheduled_digest_task`: выбирать пользователей с каналами и интересами.

Acceptance criteria:

- `/digest` без каналов просит настроить `/set_channels`.
- `/digest` без интересов просит настроить `/set_interests`.
- Успешный log содержит channels/interests.
- При ошибке одного канала digest строится по остальным.
- Отдельного status `partial_success` нет.

Проверка:

```bash
rtk uv run pytest
```

### Этап 8. Тесты

Файлы:

- `tests/`

Задачи:

- Добавить unit-тесты parser/service/repository.
- Добавить integration-тесты handlers с mocked `test_channel_access`.
- Добавить тест worker flow с mocked `fetch_channel_posts`, `generate_interest_based_digest`, Telegram send.
- Добавить migration smoke test, если текущий test setup это поддерживает.

Минимальный набор:

- `parse_channel_list`: дубли, `@`, пробелы, лимит 5.
- `parse_interest_list`: запятые, переносы строк, дубли, лимит 5.
- `replace_for_user`: replaces list, keeps order.
- `/set_channels`: partial success.
- `/set_interests`: saves exactly 5, rejects 6.
- `/digest`: requires channels and interests.
- `scheduled_digest_task`: skips users without interests.

Проверка:

```bash
rtk uv run pytest
rtk uv run ruff check .
```

### Этап 9. README и эксплуатация

Файлы:

- `README.md`

Задачи:

- Обновить список команд.
- Добавить пример настройки:
  - `/set_channels @channel_one @channel_two`
  - `/set_interests финансы, технологии`
  - `/digest`
- Указать лимиты: 5 каналов, 5 интересов.

Acceptance criteria:

- README не обещает callback UI или web UI.
- Команды совпадают с `/help`.

### Этап 10. Rollout

Задачи:

- Применить миграции.
- Выкатить bot + worker.
- Проверить, что старые пользователи получили канал в `user_channels`.
- Проверить `/channels` у старого пользователя.
- Проверить `/set_interests` и `/digest` на тестовом пользователе.
- Проверить worker logs.
- Мониторить ошибки Telegram send, Pyrogram access, OpenRouter rate limits.

Rollback:

- Вернуть код на предыдущую версию.
- Оставить новые таблицы как есть.
- Старый flow продолжит использовать `users.target_channel`.

## 4. Рекомендуемый порядок PR

1. `db-multi-channel-schema`: миграция, модели, репозитории, UoW, repository tests.
2. `bot-channel-commands`: commands для каналов, service/parser tests.
3. `bot-interest-commands`: commands для интересов, `/help`, tests.
4. `digest-worker-interest-flow`: AI prompt, worker, scheduled flow, digest tests.
5. `docs-and-rollout`: README, финальная проверка, rollout checklist.

## 5. Definition of Done

- Пользователь может сохранить до 5 каналов.
- Пользователь может сохранить до 5 интересов.
- `/channels` и `/interests` показывают текущие настройки.
- `/digest` генерирует дайджест по интересам, не по каналам.
- В пунктах дайджеста есть ссылки на источники.
- Scheduled digest работает только для пользователей с каналами и интересами.
- `digest_logs` содержит channels/interests.
- `users.target_channel` не удален.
- `rtk uv run pytest` проходит.
- `rtk uv run ruff check .` проходит.
