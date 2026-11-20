# VectorStartUp

> **Операционная платформа для управления стартапами и растущими компаниями.**  
> **Python + Django + HTML5 + CSS3**.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)
![HTML5 & CSS3](https://img.shields.io/badge/UI-HTML5%20%2B%20CSS3%20SSR-1D4ED8)
![Database](https://img.shields.io/badge/DB-SQLite3%20%7C%20PostgreSQL-336791)

---

## Зачем нужен 

Основатели стартапов обычно держат бизнес в десяти разрозненных таблицах: финансы и Runway — в Google Sheets, CRM — в Notion, Cap Table — в Excel, задачи — в таск-трекере, а отчёт инвесторам собирают вручную раз в месяц.

**VectorStartUp** объединяет все контуры управления компанией в едином быстром рабочем пространстве: от кассового остатка и юнит-экономики до воронки продаж, счетов, вестинга и Data Room.

### Главные инженерные принципы

- **Серверная графика SVG** — все графики динамики кэша, сравнения Выручка vs Burn и спарклайны KPI рассчитываются в чистом Python (`core/analytics.py`) и рендерятся как чёткий векторный `<svg>` на стороне сервера.

- **Минимальный стек** — единственная зависимость в `requirements.txt` это `Django`. Никакого `node_modules`, Webpack, Vite, DRF или Redis для старта.

- **Мульти-компании из коробки** — один аккаунт может управлять несколькими стартапами со строгой изоляцией данных на уровне ORM и сессий.

---

## Модули платформы (16 разделов, 84 маршрута)

| Контур | Модуль | Маршрут | Возможности |
|---|---|---|---|
| **Обзор** | **Дашборд и «Фокус основателя»** | `/` | Cash on Hand, Burn Rate, Runway, автоматическая приоритизация рисков (просрочка счетов, низкий Runway, перерасход бюджета, горячие сделки, просроченные задачи, отстающие KPI). |
| | **Целевые KPI** | `/kpis/` | Метрики с направлением цели (`выше лучше` / `ниже лучше`), история замеров, индикаторы и серверные SVG-спарклайны. |
| | **Отчёт инвесторам** | `/investor-report/` | Автосборка Investor Update из живых данных компании, редактируемые блоки достижений/рисков/Asks, экспорт `.md` и печать в PDF (`Ctrl+P`). |
| **Выручка и рост** | **CRM-воронка B2B** | `/sales/` | Канбан и таблица сделок по 6 этапам (`Лид → Квалификация → Демо → Договор → Выиграна/Проиграна`), взвешенный пайплайн, MRR-эквивалент, Win Rate, CSV-экспорт. |
| | **Счета и дебиторка** | `/invoices/` | Выставление счетов (НДС 20% / УСН), автоматический контроль просрочки, отметка оплаты в 1 клик, скачивание печатного счёта `.txt` и CSV. |
| | **Гипотезы роста (ICE)** | `/experiments/` | Бэклог экспериментов с приоритетом по формуле `ICE = (Impact + Confidence + Ease) / 3` и статусами проверки. |
| **Финансы и капитал** | **Финмодель и симулятор Runway** | `/simulator/` | 18-месячный прогноз кассы, готовые сценарии в 1 клик (`Рост`, `Экономия`, `Новый раунд`), учёт найма и раунда, точка безубыточности, **SaaS Unit Economics** (ARPU, MRR/ARR, LTV/CAC, Payback, Rule of 40) + SVG-графики. |
| | **План бюджета** | `/budgets/` | Квартальные бюджетные статьи по категориям и контроль отклонения факт vs план. |
| | **Учёт расходов** | `/expenses/` | Реестр оплат и регулярных списаний, привязка к статьям бюджета и ответственным, быстрая отметка оплаты и выгрузка в CSV. |
| | **Cap Table и вестинг** | `/cap-table/` | Реестр долей (основатели, инвесторы, ESOP, советники), расчёт разблокированных долей с учётом клиффа и **симулятор размытия следующего раунда** (Pre/Post-money + расширение ESOP). |
| | **Венчуры и раунды** | `/ventures/` | База инвесторов и фондов, инвестиционные раунды и распределение привлечённых траншей по целям с контролем освоения. |
| **Стратегия и команда** | **Дорожная карта (Roadmap)** | `/roadmap/` | Квартальные стратегические вехи с серверными чек-листами и автоматическим пересчётом процента готовности. |
| | **Investor Data Room** | `/data-room/` | Структурированный реестр документов для Due Diligence с версиями, уровнями доступа (`Основатели / Команда / Инвесторы`) и индексом готовности (%). |
| | **Командные задачи** | `/tasks/` | Канбан-доска (`Бэклог → В работе → На ревью → Готово`), приоритеты, сроки, просрочки и комментарии. |
| | **Сотрудники и ФОТ** | `/team/` | Штатное расписание по отделам, оклады, опционы, автоматический вклад в Burn Rate и карточки сотрудников. |
| | **Компании и глобальный поиск** | `/companies/`, `/search/` | Создание/переключение компаний в 1 клик и сквозной поиск по задачам, сделкам, счетам, KPI, расходам, сотрудникам, вехам и Data Room. |

---

## Архитектура

```text
Браузер (HTML5 + CSS3)
   │  GET (фильтры, поиск, пресеты симулятора) / POST (PRG + CSRF)
   ▼
Django URL Router (core/urls.py — 84 маршрута)
   │
   ├── Middleware (Session, CSRF, Auth, Messages, XFrameOptions)
   ├── Context Processor (active_company_context → изоляция рабочей компании)
   │
   ▼
MVT Controllers (core/views.py + core/views_growth.py)
   │
   ├── core/forms.py       ──▶ Валидация форм (ModelForm + Auth)
   ├── core/analytics.py   ──▶ Чистый Python: Runway, Unit Economics, Cap Table, SVG-геометрия, Alerts
   └── core/models.py      ──▶ 20 ORM-моделей (DecimalField для денег, FK на Company)
          │
          ▼
SQLite3 (db.sqlite3) / PostgreSQL + SMTP EmailBackend (6-значные коды подтверждения)
```

## Ключевые финансовые формулы (`core/analytics.py`)

- **Cash on Hand** $= \text{Initial Cash} + \sum \text{Закрытые раунды} - \sum \text{Оплаченные расходы}$
- **Monthly Burn Rate** $= \max(\text{Расходы за 30 дней},\; \text{Месячный ФОТ активных сотрудников})$
- **Runway** $= \dfrac{\text{Cash on Hand}}{\text{Monthly Burn Rate}}$
- **LTV** $= \dfrac{\text{ARPU} \times \text{Gross Margin}}{\text{Monthly Churn}}$, $\quad \text{CAC Payback} = \dfrac{\text{CAC}}{\text{ARPU} \times \text{Gross Margin}}$
- **Rule of 40** $= \left((1 + \text{MoM})^{12} - 1\right) \times 100\% + \dfrac{\text{MRR} - \text{Burn}}{\text{MRR}} \times 100\%$
- **Post-money и размытие**: $\text{Доля инвестора} = \dfrac{\text{Investment}}{\text{Pre-money} + \text{Investment}}$, коэффициент сохранения долей $= 1 - \text{Доля инвестора} - \text{Новый ESOP}$.

---

## Быстрый старт

### Требования
- **Python 3.11+**
- `pip` и `venv`

### 1. Установка и запуск (Linux / macOS)

```bash
# Если вы в корне репозитория с папкой django_startup_hub:
cd django_startup_hub

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py makemigrations core
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### 1b. Установка и запуск (Windows PowerShell)

```powershell
cd django_startup_hub

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python manage.py makemigrations core
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Демо-доступ (после `seed_demo`)
- **Email**: `alexey@vectorstart.ru`
- **Пароль**: `demo12345`
- **Админ-панель Django**: `http://127.0.0.1:8000/admin/` (логин `founder` или email `alexey@vectorstart.ru`, пароль `demo12345`)

---

## Конфигурация (`.env.local` / `.env`)

`startup_hub/settings.py` автоматически загружает `.env.local` или `.env` при старте без сторонних библиотек.

### Отправка 6-значных кодов подтверждения

Чтобы включить реальную доставку на почту, создайте файл `.env.local` рядом с `manage.py`:

```env
# Пример для Gmail (используйте 16-значный пароль приложения Google, не обычный пароль)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your-email@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx
SMTP_FROM="VectorStartUp <your-email@gmail.com>"

# Время жизни 6-значного кода подтверждения в минут
EMAIL_VERIFICATION_TTL_MINUTES=15
```

### Подключение PostgreSQ

По умолчанию используется `db.sqlite3`. Для перехода на PostgreSQL установите `psycopg` и добавьте в `.env.local`:

```env
DB_ENGINE=postgresql
DB_NAME=vectorstart
DB_USER=postgres
DB_PASSWORD=strong_password
DB_HOST=127.0.0.1
DB_PORT=5432
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=replace-with-long-random-secret
```

---

## Безопасность

- **Регистрация с подтверждением Email**: аккаунт создаётся неактивным (`is_active=False`); 6-значный код генерируется через `secrets.randbelow`, ограничен TTL (15 мин) и 5 попытками ввода, проверяется через timing-safe `secrets.compare_digest`, а повторная отправка защищена кулдауном 30 секунд.
- **Изоляция данных между компаниями**: каждый запрос проверяет членство пользователя (`CompanyMembership`) и привязку объекта к `active_company`.
- **Защита форм и редиректов**: `CsrfViewMiddleware`, `@require_POST` на всех мутирующих действиях, `url_has_allowed_host_and_scheme` против Open Redirect, автоэкранирование шаблонов Django и `XFrameOptionsMiddleware`.
- **Точные денежные расчёты**: все суммы, доли и оценки хранятся в `DecimalField`.

---

## Структура проекта

```text
django_startup_hub/
├── manage.py
├── requirements.txt
├── .env.example
├── startup_hub/
│   ├── settings.py                 # Конфигурация, встроенный .env-загрузчик, SQLite/PostgreSQL, SMTP
│   ├── urls.py                     # Корневая маршрутизация
│   ├── wsgi.py
│   └── asgi.py
├── core/
│   ├── models.py                   # 20 реляционных ORM-моделей
│   ├── analytics.py                # Симулятор Runway, Unit Economics, Cap Table, SVG, Alerts, Отчёт
│   ├── forms.py                    # Django ModelForm и формы аутентификации
│   ├── views.py                    # Auth, Dashboard, Компании, Бюджеты, Расходы, Венчуры, Команда, Задачи, KPI
│   ├── views_growth.py             # Финмодель, CRM, Счета, Roadmap, Cap Table, ICE, Data Room, Отчёт, Поиск
│   ├── urls.py                     # 84 маршрута SSR
│   ├── backends.py                 # Вход по Email (case-insensitive)
│   ├── context_processors.py       # Активная компания во всех шаблонах
│   ├── templatetags/startup_tags.py# Форматирование денег и хелперы шаблонов
│   ├── admin.py                    # Регистрация всех моделей в Django Admin
│   ├── management/commands/
│   │   └── seed_demo.py            # Идемпотентный генератор демо-данных
│   ├── test_analytics.py           # Быстрые unit-тесты аналитического движка (stdlib)
│   └── tests.py                    # Интеграционные тесты Django (Auth, CRUD, изоляция компаний)
├── templates/                      # HTML5-шаблоны (base.html, base_auth.html, includes/ и 14 разделов)
└── static/
    └── css/
        └── main.css                # Единая дизайн-система CSS3 (60-30-10 Slate & Cobalt, @media print)
```

---

## Тестирование

```bash
# Полный набор тестов Django (модели, права доступа, аутентификация, CRUD, аналитика)
python manage.py test core -v 2

# Быстрая проверка только расчётного движка (без поднятия БД)
python3 -m unittest core.test_analytics -v
```
