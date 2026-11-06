# 🎓 UniSpace AI

Интеллектуальная образовательная платформа для студентов: AI-тьютор, персональные учебные планы, интерактивные тесты, умные карточки, анализ материалов, учёт успеваемости и дедлайнов.

Бэкенд на **FastAPI**. Вся учебная логика вынесена в чистые Python-сервисы без зависимости от веб-фреймворка, поэтому её легко тестировать и переиспользовать (в боте, CLI или веб-интерфейсе).

## Возможности

| Модуль | Что делает | Как работает |
|---|---|---|
| **AI Tutor** | Отвечает на вопросы, опираясь на ваш конспект | Сократовский стиль через Claude (`ANTHROPIC_API_KEY`); без ключа — офлайн-подсказки |
| **Учебные планы** | Расписание занятий на 1–90 дней | Детерминированный алгоритм: вес предмета = (6 − уровень) × срочность экзамена |
| **Тесты** | Интерактивные тесты по тексту | LLM генерирует вопросы; без LLM — cloze-вопросы с пропусками |
| **Карточки** | Умное запоминание | Алгоритм интервальных повторений SM-2; авто-генерация карточек из материала |
| **Анализ материалов** | Резюме, ключевые слова, время чтения | Экстрактивное резюме и частотный анализ (ru/en), без внешних зависимостей |
| **Успеваемость** | Средние баллы, тренды, слабые места | Рекомендации по каждому предмету |
| **Дедлайны** | Приоритизация задач | Срочность = приоритет × близость срока, просрочки — первыми |

## Быстрый старт

```bash
git clone https://github.com/<your-name>/unispace-ai.git
cd unispace-ai
python -m venv .venv && source .venv/bin/activate
pip install -e ".[ai,dev]"
cp .env.example .env            # впишите ANTHROPIC_API_KEY (необязательно)
uvicorn unispace.api.app:create_app --factory --reload
```

Документация API (Swagger): <http://localhost:8000/docs>

Через Docker:

```bash
docker compose up --build
```

## Конфигурация

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `ANTHROPIC_API_KEY` | Ключ для AI Tutor и LLM-генерации тестов | не задан → офлайн-режим |
| `UNISPACE_MODEL` | Модель Claude | `claude-sonnet-5-5` |
| `UNISPACE_DATA_FILE` | JSON-файл для хранения данных | не задан → данные в памяти |
| `UNISPACE_CORS_ORIGINS` | Разрешённые origin через запятую | `http://localhost:3000,http://localhost:5173` |

## API (префикс `/api/v1`)

| Метод и путь | Назначение |
|---|---|
| `POST /materials` · `GET /materials` · `GET/DELETE /materials/{id}` | Загрузка и анализ материалов |
| `POST /tutor/ask` | Вопрос AI Tutor (опционально с `material_id` и историей) |
| `POST /plans` · `GET /plans` · `GET/DELETE /plans/{id}` | Учебные планы |
| `POST /quizzes/generate` · `GET /quizzes/{id}` · `POST /quizzes/{id}/submit` | Тесты (ответы скрыты до сдачи) |
| `POST /flashcards` · `POST /flashcards/generate` · `GET /flashcards/due` · `POST /flashcards/{id}/review` | Карточки и повторения |
| `POST /progress` · `GET /progress` · `GET /progress/summary` | Оценки и аналитика |
| `POST /deadlines` · `GET /deadlines` · `PATCH /deadlines/{id}` · `POST /deadlines/{id}/complete` | Дедлайны |
| `GET /dashboard` | Сводка: карточки к повторению, ближайшие дедлайны, успеваемость |

Пример:

```bash
curl -X POST localhost:8000/api/v1/plans -H 'content-type: application/json' -d '{
  "goal": "Сдать сессию",
  "hours_per_week": 12,
  "subjects": [
    {"name": "Математика", "level": 2, "exam_date": "2026-12-20"},
    {"name": "История", "level": 4}
  ]
}'
```

## Структура

```
src/unispace/
├── models.py        # Pydantic-модели
├── storage.py       # хранилище (память + JSON-файл)
├── ai/              # LLM-клиенты и AI Tutor
├── services/        # учебная логика (без FastAPI)
└── api/             # FastAPI-приложение и роутеры
tests/               # pytest
docs/                # архитектура и роадмап
```

Подробнее: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ROADMAP.md](docs/ROADMAP.md)

## Разработка

```bash
pytest          # тесты
ruff check .    # линтер
```

## Публикация на GitHub

```bash
git init -b main
git add -A && git commit -m "feat: initial UniSpace AI scaffold"
gh repo create unispace-ai --public --source=. --push
```

## Ограничения текущей версии

- Нет аутентификации и многопользовательского режима — все данные общие.
- Хранилище — in-memory с сохранением в JSON; для продакшена нужна БД.
- Офлайн-анализ текста не использует морфологию: русские словоформы считаются разными словами.
- Загрузка PDF/DOCX пока не реализована — материалы передаются текстом.

## Лицензия

[MIT](LICENSE)
