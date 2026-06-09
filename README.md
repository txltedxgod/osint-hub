# ◉ OSINT Hub v1

**OSINT Hub** — веб-приложение для поиска аккаунтов по имени пользователя сразу по сотням сайтов с помощью двух популярных движков — **Sherlock** и **Maigret**. Многопользовательская авторизация, история запросов, экспорт отчётов в PDF и запуск одной командой через Docker.

> ⚠️ \*\*Этичное использование.\*\* Инструмент работает только с публично доступной информацией. Используйте его только в рамках закона и только для данных, на исследование которых у вас есть права.

\---

## ✨ Функции

* 🔐 **Авторизация** — регистрация и вход, много пользователей, сессии на подписанных cookie, пароли хранятся как PBKDF2-HMAC-SHA256.
* 🔎 **Поиск username** — одно поле ввода, выбор движков, результаты сгруппированы по инструментам.
* 🕵️ **Sherlock** и 🧹 **Maigret** — запускаются параллельно как отдельные процессы; если движок не установлен — приложение не падает, а помечает его как offline.
* 📜 **История запросов** — каждый поиск сохраняется с найденными аккаунтами; просмотр, повторный доступ и удаление.
* 🗄️ **SQLite** — асинхронный доступ через SQLAlchemy 2.0 + aiosqlite.
* 📄 **Экспорт PDF** — аккуратный отчёт по любому запросу (reportlab).
* 🐳 **Docker** — `docker compose up -d --build`, и сервис готов.

\---

## 🧩 Стек

|Технология|Назначение|
|-|-|
|**Python 3.12+**|Язык разработки|
|**FastAPI + Uvicorn**|Веб-фреймворк и ASGI-сервер|
|**Jinja2**|Шаблоны (server-side rendering)|
|**SQLAlchemy 2.0 (async) + aiosqlite**|ORM и хранилище SQLite|
|**Starlette SessionMiddleware**|Сессии на подписанных cookie|
|**reportlab**|Генерация PDF|
|**Sherlock / Maigret**|Движки поиска username|
|**Docker / docker compose**|Контейнеризация|

\---

## 🚀 Быстрый старт (Docker)

```bash
# 1. Настройте окружение
cp .env.example .env
# Обязательно поменяйте SECRET\_KEY на длинную случайную строку:
#   python -c "import secrets; print(secrets.token\_hex(32))"

# 2. Соберите и запустите
docker compose up -d --build

# 3. Логи
docker compose logs -f web
```

Откройте **http://localhost:8000** → страница входа. Первый зарегистрированный аккаунт становится админом.

Остановить: `docker compose down` (данные в `./data` сохраняются).

\---

## 💻 Запуск без Docker (разработка)

```bash
python -m venv .venv \&\& source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env                                # поменяйте SECRET\_KEY
uvicorn app.main:app --reload
```

Таблицы SQLite создаются автоматически при первом запуске.

\---

## 🗺️ Структура проекта

```
osint-hub/
├── app/
│   ├── main.py              # точка входа FastAPI, middleware, lifespan
│   ├── config.py            # настройки (pydantic-settings)
│   ├── database.py          # асинхронный engine + сессии
│   ├── models.py            # User / Search / Result
│   ├── security.py          # хеширование паролей
│   ├── dependencies.py      # текущий пользователь
│   ├── templating.py        # общий Jinja2
│   ├── routers/             # auth, search, history
│   ├── services/            # osint (движки), search\_service, pdf\_service
│   ├── templates/           # base, login, register, dashboard, history…
│   └── static/styles.css    # тёмная тема
├── data/                    # SQLite-база и PDF-отчёты (volume)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

\---

## 🗜️ Схема базы данных

```mermaid
erDiagram
    USERS ||--o{ SEARCHES : runs
    SEARCHES ||--o{ RESULTS : contains

    USERS {
        int id PK
        string username
        string password\_hash
        string salt
        bool is\_admin
        datetime created\_at
    }
    SEARCHES {
        int id PK
        int user\_id FK
        string query
        string tools
        string status
        int total\_found
        datetime created\_at
    }
    RESULTS {
        int id PK
        int search\_id FK
        string tool
        string site\_name
        string url
    }
```

\---

## 🛣️ Маршруты

|Метод|Путь|Описание|
|-|-|-|
|GET/POST|`/register`|Регистрация|
|GET/POST|`/login`|Вход|
|GET|`/logout`|Выход|
|GET|`/`|Дашборд + форма поиска|
|POST|`/search`|Запуск поиска|
|GET|`/history`|Список запросов|
|GET|`/history/{id}`|Детали запроса|
|GET|`/history/{id}/pdf`|Экспорт PDF|
|POST|`/history/{id}/delete`|Удаление|

\---

## ⚙️ Переменные окружения

|Переменная|По умолчанию|Описание|
|-|-|-|
|`SECRET\_KEY`|—|Ключ подписи сессий (**обязательно смените**)|
|`DATABASE\_URL`|`sqlite+aiosqlite:///./data/osint\_hub.db`|Строка подключения|
|`REPORTS\_DIR`|`./data/reports`|Папка отчётов|
|`SHERLOCK\_TIMEOUT`|`180`|Таймаут Sherlock, сек|
|`MAIGRET\_TIMEOUT`|`240`|Таймаут Maigret, сек|
|`SITE\_TIMEOUT`|`15`|Таймаут на сайт, сек|
|`SESSION\_MAX\_AGE`|`604800`|Срок сессии, сек|
|`LOG\_LEVEL`|`INFO`|Уровень логов|

\---

## 📝 Лицензия

MIT — см. [LICENSE](LICENSE).

