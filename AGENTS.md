# AGENTS.md

## Структура проекта

Основной код находится в `genesis_core/`; сервисы и API сгруппированы по доменам (`user_api/`, `compute/`, `network/`, `agent/`).
Тесты разделены на `genesis_core/tests/unit/` и `genesis_core/tests/functional/`. Документация хранится в `docs/`, конфигурация MkDocs — в `mkdocs.yml`. Миграции лежат в `migrations/`, локальная инфраструктура для тестов — в `docker-compose.yml`.

## Команды разработки, проверки и документации

Используйте `tox` с `tox-uv`:

```bash
tox -e develop                 # создать dev-окружение
source .tox/develop/bin/activate
tox -e py312                   # unit tests
tox -e py312-functional        # functional tests
tox -e ruff-check              # только lint
tox -e ruff                    # format + autofix
tox -e mypy                    # type checking
tox -e docs                    # локальный MkDocs на :8181
tox -e mdlint                  # lint Markdown
```

Для функциональных тестов поднимите Postgres:

```bash
docker compose up -d postgres
export DATABASE_URI="postgresql://genesis_core:genesis_core@127.0.0.1:5432/genesis_core"
export ADMIN_PASSWORD="admin"
export DEFAULT_CLIENT_SECRET="GenesisCoreSecret"
export GLOBAL_SALT="FOy/2kwwdn0ig1QOq7cestqe"
export HS256_KEY="secret"
```

## Стиль кода и тесты

Python-стиль задаётся через Ruff: 4 пробела, двойные кавычки, максимальная длина строки `88`, целевая версия — `py310`. Для нового production-кода добавляйте type hints: `mypy` запускается как `mypy -p genesis_core`, а `disallow_untyped_defs = true`.

Имена тестов — `test_*.py`, сами тесты держите рядом с соответствующим доменом. Быстрые сценарии кладите в `tests/unit`, интеграционные и REST/API — в `tests/functional`.

## Коммиты и Pull Request

История проекта использует короткие сообщения в повелительном стиле, например: `Add IAM permissions and roles documentation`, `validate exports/imports (#290)`. Пишите один ясный subject, при необходимости добавляйте номер issue/PR в скобках.

PR должен содержать описание изменения, влияние на API/схемы/документацию, список прогнанных проверок и ссылку на issue. Если меняете поведение API или права доступа, обновите `docs/` и функциональные тесты. Запрашивайте review у владельцев из `CODEOWNERS` (`@gmelikov`, `@phantomii`, `@akremenetsky`, `@slashburygin`).
