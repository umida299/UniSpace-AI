# Contributing

Спасибо за интерес к UniSpace AI!

## Процесс

1. Сделайте fork и создайте ветку: `git checkout -b feat/short-name`.
2. Установите зависимости: `pip install -e ".[ai,dev]"`.
3. Внесите изменения и добавьте тесты (`tests/`).
4. Проверьте: `ruff check . && pytest`.
5. Откройте Pull Request по шаблону.

## Правила

- Учебная логика — в `services/` без импорта FastAPI.
- Любая AI-функция должна иметь офлайн-фолбэк.
- Время передавайте параметром (`today`), не вызывайте `date.today()` глубоко в логике.
- Коммиты в стиле Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.
- Не коммитьте ключи и `.env`.
