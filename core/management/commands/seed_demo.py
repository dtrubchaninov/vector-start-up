"""
Management command: python manage.py seed_demo
Idempotently seeds realistic demo founder account, two startups, budgets,
expenses, investors, funding rounds, allocations, employees, tasks, KPIs, and logs.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    ActivityLog,
    BudgetCategory,
    BudgetItem,
    Company,
    CompanyMembership,
    DataRoomDoc,
    Deal,
    Employee,
    EquityHolder,
    Expense,
    FundingRound,
    GrowthExperiment,
    InvestmentAllocation,
    Investor,
    Invoice,
    KPIEntry,
    KPIMetric,
    MilestoneCheckItem,
    RoadmapMilestone,
    Task,
    TaskComment,
    UnitEconomicsProfile,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Наполняет базу данных реалистичными демо-данными стартапов для VectorStartUp.'

    def handle(self, *args, **options):
        today = timezone.localdate()

        founder, created = User.objects.get_or_create(
            username='founder',
            defaults={
                'first_name': 'Алексей',
                'last_name': 'Соколов',
                'email': 'alexey@vectorstart.ru',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            founder.set_password('demo12345')
            founder.save()
            self.stdout.write(
                self.style.SUCCESS('Создан демо-пользователь: alexey@vectorstart.ru (логин founder) / demo12345')
            )

        existing_company = Company.objects.filter(name='НейроЛогистика').first()
        if existing_company is not None:
            seeded_extras = self._seed_growth_modules(existing_company, today)
            if seeded_extras:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Новые модули (CRM, счета, Roadmap, Cap Table, гипотезы, Data Room) добавлены к «НейроЛогистика».'
                    )
                )
            else:
                self.stdout.write(self.style.WARNING('Демо-данные уже загружены. Пропускаем повторное наполнение.'))
            return

        # 1. Primary Startup: НейроЛогистика
        company = Company.objects.create(
            name='НейроЛогистика',
            legal_name='ООО «НейроЛогистика Технологии»',
            industry='Логистика и ИИ-маршрутизация (B2B SaaS)',
            stage=Company.Stage.SEED,
            currency=Company.Currency.RUB,
            founded_date=today - timedelta(days=410),
            initial_cash=Decimal('3200000.00'),
            target_mrr=Decimal('2400000.00'),
            website='https://neurologistics.example.ru',
            description='Платформа предиктивной маршрутизации и оптимизации последней мили для региональных дистрибьюторов и ритейла.',
            created_by=founder,
        )
        CompanyMembership.objects.create(
            company=company,
            user=founder,
            role=CompanyMembership.Role.FOUNDER,
        )

        # Employees
        emp_ceo = Employee.objects.create(
            company=company,
            user=founder,
            full_name='Алексей Соколов',
            position='CEO & Co-Founder',
            department=Employee.Department.PRODUCT,
            email='alexey@neurologistics.ru',
            phone='@asokolov',
            monthly_salary=Decimal('240000.00'),
            equity_options_pct=Decimal('0.00'),
            status=Employee.Status.ACTIVE,
            hired_at=today - timedelta(days=400),
        )
        emp_cto = Employee.objects.create(
            company=company,
            full_name='Мария Волкова',
            position='CTO & Lead Backend',
            department=Employee.Department.ENGINEERING,
            email='maria@neurologistics.ru',
            phone='@mvolkova_dev',
            monthly_salary=Decimal('310000.00'),
            equity_options_pct=Decimal('4.50'),
            status=Employee.Status.ACTIVE,
            hired_at=today - timedelta(days=380),
        )
        emp_ml = Employee.objects.create(
            company=company,
            full_name='Дмитрий Орлов',
            position='Senior ML Engineer',
            department=Employee.Department.ENGINEERING,
            email='dmitry@neurologistics.ru',
            phone='@dorlov_ml',
            monthly_salary=Decimal('285000.00'),
            equity_options_pct=Decimal('1.50'),
            status=Employee.Status.ACTIVE,
            hired_at=today - timedelta(days=260),
        )
        emp_design = Employee.objects.create(
            company=company,
            full_name='Елена Ковалёва',
            position='Product Designer',
            department=Employee.Department.DESIGN,
            email='elena@neurologistics.ru',
            phone='@ekovaleva_ux',
            monthly_salary=Decimal('195000.00'),
            equity_options_pct=Decimal('0.75'),
            status=Employee.Status.ACTIVE,
            hired_at=today - timedelta(days=210),
        )
        emp_growth = Employee.objects.create(
            company=company,
            full_name='Игорь Смирнов',
            position='Head of B2B Sales',
            department=Employee.Department.SALES,
            email='igor@neurologistics.ru',
            phone='@ismirnov_sales',
            monthly_salary=Decimal('210000.00'),
            equity_options_pct=Decimal('1.00'),
            status=Employee.Status.ACTIVE,
            hired_at=today - timedelta(days=150),
        )
        emp_fin = Employee.objects.create(
            company=company,
            full_name='Анна Лебедева',
            position='Финансовый менеджер',
            department=Employee.Department.FINANCE,
            email='anna@neurologistics.ru',
            phone='@alebedeva_fin',
            monthly_salary=Decimal('165000.00'),
            equity_options_pct=Decimal('0.25'),
            status=Employee.Status.ONBOARDING,
            hired_at=today - timedelta(days=14),
        )

        # Budget items (Q4 2026)
        b_payroll = BudgetItem.objects.create(
            company=company,
            name='Фонд оплаты труда (инженерная и коммерческая команда)',
            category=BudgetCategory.PAYROLL,
            period='2026-Q4',
            planned_amount=Decimal('4500000.00'),
            notes='Включая налоги и резерв под найм DevOps-инженера.',
        )
        b_cloud = BudgetItem.objects.create(
            company=company,
            name='Облачная инфраструктура, GPU и карты',
            category=BudgetCategory.CLOUD,
            period='2026-Q4',
            planned_amount=Decimal('850000.00'),
            notes='Yandex Cloud, GPU-кластер для переобучения моделей, геокодер.',
        )
        b_marketing = BudgetItem.objects.create(
            company=company,
            name='B2B-маркетинг, конференции и контент',
            category=BudgetCategory.MARKETING,
            period='2026-Q4',
            planned_amount=Decimal('920000.00'),
            notes='Стенд на TransRussia, таргетинг, вебинары для директоров по логистике.',
        )
        b_eng = BudgetItem.objects.create(
            company=company,
            name='Внешний аудит безопасности и лицензии ПО',
            category=BudgetCategory.ENGINEERING,
            period='2026-Q4',
            planned_amount=Decimal('420000.00'),
            notes='Пентест API, GitHub Enterprise, Figma, Sentry.',
        )
        b_legal = BudgetItem.objects.create(
            company=company,
            name='Юридическое сопровождение Seed-раунда и IP',
            category=BudgetCategory.LEGAL,
            period='2026-Q4',
            planned_amount=Decimal('380000.00'),
            notes='Регистрация ПО в реестре, корпоративный договор, бухучёт.',
        )
        b_office = BudgetItem.objects.create(
            company=company,
            name='Коворкинг и командировки к пилотным клиентам',
            category=BudgetCategory.OFFICE,
            period='2026-Q4',
            planned_amount=Decimal('310000.00'),
            notes='Переговорные комнаты и выездные внедрения.',
        )

        # Expenses
        expenses_data = [
            ('Выплата заработной платы за октябрь', BudgetCategory.PAYROLL, b_payroll, 'Банк-клиент (Зарплатный проект)', Decimal('1405000.00'), today - timedelta(days=18), Expense.Status.PAID, True, emp_fin),
            ('Выплата заработной платы за ноябрь (аванс)', BudgetCategory.PAYROLL, b_payroll, 'Банк-клиент (Зарплатный проект)', Decimal('710000.00'), today - timedelta(days=4), Expense.Status.PAID, True, emp_fin),
            ('Yandex Cloud - кластер Kubernetes и Managed PostgreSQL', BudgetCategory.CLOUD, b_cloud, 'Yandex Cloud', Decimal('342000.00'), today - timedelta(days=12), Expense.Status.PAID, True, emp_cto),
            ('Аренда GPU-инстансов для обучения VRP-модели', BudgetCategory.CLOUD, b_cloud, 'Selectel Cloud', Decimal('295000.00'), today - timedelta(days=6), Expense.Status.PAID, False, emp_ml),
            ('Участие в логистическом форуме и печать материалов', BudgetCategory.MARKETING, b_marketing, 'ЭкспоФорум', Decimal('540000.00'), today - timedelta(days=15), Expense.Status.PAID, False, emp_growth),
            ('Лидогенерация и перформанс-кампании B2B', BudgetCategory.MARKETING, b_marketing, 'Агентство РостДиджитал', Decimal('415000.00'), today - timedelta(days=3), Expense.Status.PENDING, True, emp_growth),
            ('Пентест и аудит информационной безопасности', BudgetCategory.ENGINEERING, b_eng, 'Positive Audit Lab', Decimal('320000.00'), today - timedelta(days=9), Expense.Status.PAID, False, emp_cto),
            ('Юридическое сопровождение сделки и регистрация ПО', BudgetCategory.LEGAL, b_legal, 'LexTech Partners', Decimal('245000.00'), today - timedelta(days=20), Expense.Status.PAID, False, emp_ceo),
            ('Аренда рабочих мест в технопарке', BudgetCategory.OFFICE, b_office, 'Технопарк Сколково', Decimal('145000.00'), today - timedelta(days=10), Expense.Status.PAID, True, emp_fin),
            ('Командировка на запуск пилота в Казани', BudgetCategory.OFFICE, b_office, 'Авиа и отель', Decimal('68500.00'), today - timedelta(days=2), Expense.Status.PENDING, False, emp_growth),
        ]
        for title, cat, b_item, vendor, amount, exp_date, status, recurring, resp in expenses_data:
            Expense.objects.create(
                company=company,
                budget_item=b_item,
                category=cat,
                title=title,
                vendor=vendor,
                amount=amount,
                expense_date=exp_date,
                status=status,
                is_recurring=recurring,
                responsible=resp,
                created_by=founder,
            )

        # Investors & Funding Rounds
        inv_vc = Investor.objects.create(
            company=company,
            name='Северный Вектор Венчурс',
            investor_type=Investor.InvestorType.VC,
            contact_name='Сергей Громов (Партнёр)',
            email='sgromov@northvector.vc',
            website='https://northvector.example.vc',
            typical_check='15–60 млн ₽',
            notes='Фокус на промышленный SaaS и логистику. Лид-инвестор нашего Seed-раунда.',
        )
        inv_angel = Investor.objects.create(
            company=company,
            name='Виктор Морозов (Ангельский синдикат)',
            investor_type=Investor.InvestorType.ANGEL,
            contact_name='Виктор Морозов',
            email='vmorozov@angels.example.ru',
            typical_check='3–10 млн ₽',
            notes='Основатель логистического оператора, помогает с интро в федеральный ритейл.',
        )
        inv_grant = Investor.objects.create(
            company=company,
            name='Фонд содействия инновациям',
            investor_type=Investor.InvestorType.GRANT,
            contact_name='Программа «Старт-ИИ»',
            email='grants@fasie.example.ru',
            typical_check='4–8 млн ₽',
            notes='Неразмываемое грантовое финансирование на R&D.',
        )

        round_preseed = FundingRound.objects.create(
            company=company,
            investor=inv_angel,
            round_name='Pre-Seed Ангельский',
            stage=Company.Stage.PRE_SEED,
            amount=Decimal('8500000.00'),
            equity_percent=Decimal('7.50'),
            pre_money_valuation=Decimal('105000000.00'),
            closed_date=today - timedelta(days=280),
            status=FundingRound.Status.CLOSED,
            notes='Закрыт на этапе первых 3 пилотных клиентов.',
        )
        round_seed = FundingRound.objects.create(
            company=company,
            investor=inv_vc,
            round_name='Seed Раунд 2026',
            stage=Company.Stage.SEED,
            amount=Decimal('24000000.00'),
            equity_percent=Decimal('14.00'),
            pre_money_valuation=Decimal('147000000.00'),
            closed_date=today - timedelta(days=75),
            status=FundingRound.Status.CLOSED,
            notes='Обеспечивает 18 месяцев runway для масштабирования продаж в РФ и СНГ.',
        )
        FundingRound.objects.create(
            company=company,
            investor=inv_grant,
            round_name='Грант «Старт-ИИ» (Этап 2)',
            stage=Company.Stage.SEED,
            amount=Decimal('6000000.00'),
            equity_percent=Decimal('0.00'),
            pre_money_valuation=Decimal('0.00'),
            closed_date=today + timedelta(days=35),
            status=FundingRound.Status.TERM_SHEET,
            notes='Ожидается финальное подписание соглашения по R&D-вехе.',
        )

        # Investment Allocations
        InvestmentAllocation.objects.create(
            company=company,
            funding_round=round_seed,
            bucket_name='Ядро ML-маршрутизатора и интеграции 1С/SAP',
            category=BudgetCategory.ENGINEERING,
            allocated_amount=Decimal('10500000.00'),
            spent_amount=Decimal('4850000.00'),
            target_milestone='Релиз v2.4 с расчётом окон доставки за <1.2 сек',
        )
        InvestmentAllocation.objects.create(
            company=company,
            funding_round=round_seed,
            bucket_name='Коммерческий блок и B2B-привлечение',
            category=BudgetCategory.MARKETING,
            allocated_amount=Decimal('6500000.00'),
            spent_amount=Decimal('2640000.00'),
            target_milestone='Подключение 25 платящих корпоративных клиентов',
        )
        InvestmentAllocation.objects.create(
            company=company,
            funding_round=round_seed,
            bucket_name='Облачный кластер и отказоустойчивость SLA 99.9%',
            category=BudgetCategory.CLOUD,
            allocated_amount=Decimal('3500000.00'),
            spent_amount=Decimal('1420000.00'),
            target_milestone='Мультирегиональный отказоустойчивый контур',
        )
        InvestmentAllocation.objects.create(
            company=company,
            funding_round=round_seed,
            bucket_name='Стратегический операционный резерв',
            category=BudgetCategory.OFFICE,
            allocated_amount=Decimal('3500000.00'),
            spent_amount=Decimal('620000.00'),
            target_milestone='Подушка безопасности на 4 месяца burn rate',
        )
        InvestmentAllocation.objects.create(
            company=company,
            funding_round=round_preseed,
            bucket_name='Разработка MVP и первые 3 пилота',
            category=BudgetCategory.ENGINEERING,
            allocated_amount=Decimal('8500000.00'),
            spent_amount=Decimal('8100000.00'),
            target_milestone='Подтверждение Product-Market Fit',
        )

        # Tasks
        t1 = Task.objects.create(
            company=company,
            title='Оптимизировать расчёт маршрутов для 500+ точек доставки',
            description='Снизить время генерации маршрута на пиковых заказах до 1.5 сек и добавить учёт температурных зон кузова.',
            assignee=emp_ml,
            created_by=founder,
            priority=Task.Priority.CRITICAL,
            status=Task.Status.IN_PROGRESS,
            due_date=today + timedelta(days=4),
            milestone='Спринт 14 - Релиз v2.4',
            estimated_hours=24,
        )
        Task.objects.create(
            company=company,
            title='Подготовить финансовый отчёт для совета директоров за Q4',
            description='Свести план/факт по бюджету, юнит-экономику CAC/LTV и прогноз runway на 12 месяцев.',
            assignee=emp_fin,
            created_by=founder,
            priority=Task.Priority.HIGH,
            status=Task.Status.IN_REVIEW,
            due_date=today + timedelta(days=2),
            milestone='Совет директоров',
            estimated_hours=8,
        )
        Task.objects.create(
            company=company,
            title='Закрыть коммерческое предложение для сети «ВолгаРитейл»',
            description='Финализировать SLA, расчёт ROI на 120 грузовиков и подписать годовой контракт.',
            assignee=emp_growth,
            created_by=founder,
            priority=Task.Priority.HIGH,
            status=Task.Status.IN_PROGRESS,
            due_date=today - timedelta(days=1),
            milestone='Enterprise Pipeline',
            estimated_hours=10,
        )
        Task.objects.create(
            company=company,
            title='Редизайн экрана диспетчера и экспорт путевых листов',
            description='Упростить ручную корректировку точек на маршруте и выгрузку отчёта для водителей.',
            assignee=emp_design,
            created_by=founder,
            priority=Task.Priority.MEDIUM,
            status=Task.Status.BACKLOG,
            due_date=today + timedelta(days=11),
            milestone='Спринт 15',
            estimated_hours=16,
        )
        Task.objects.create(
            company=company,
            title='Настроить коннектор обмена заказами с 1С:УТ 11',
            description='Двусторонний обмен накладными, статусами доставки и весогабаритными характеристиками.',
            assignee=emp_cto,
            created_by=founder,
            priority=Task.Priority.HIGH,
            status=Task.Status.DONE,
            due_date=today - timedelta(days=5),
            milestone='Спринт 13',
            estimated_hours=20,
        )
        Task.objects.create(
            company=company,
            title='Завершить юридический аудит лицензионного договора SaaS',
            description='Обновить оферту с учётом требований по обработке персональных данных 152-ФЗ.',
            assignee=emp_ceo,
            created_by=founder,
            priority=Task.Priority.MEDIUM,
            status=Task.Status.DONE,
            due_date=today - timedelta(days=8),
            milestone='Юридический контур',
            estimated_hours=6,
        )

        TaskComment.objects.create(
            task=t1,
            author=founder,
            body='Провели замер на датасете клиента: текущее время 2.9 сек, после батчинга матрицы расстояний ожидаем ~1.1 сек.',
        )

        # KPI Metrics + History
        kpi_mrr = KPIMetric.objects.create(
            company=company,
            name='Ежемесячная выручка (MRR)',
            category=KPIMetric.Category.REVENUE,
            unit='₽',
            current_value=Decimal('1920000.00'),
            target_value=Decimal('2400000.00'),
            direction=KPIMetric.Direction.HIGHER_BETTER,
            period_label='Q4 2026',
            owner=emp_growth,
            description='Сумма активных регулярных B2B-подписок без разовых внедрений.',
        )
        for offset, val in [(90, '1180000'), (60, '1420000'), (30, '1690000'), (5, '1920000')]:
            KPIEntry.objects.create(
                metric=kpi_mrr,
                recorded_date=today - timedelta(days=offset),
                value=Decimal(val),
                note='Закрытие новых контрактов',
                created_by=founder,
            )

        kpi_clients = KPIMetric.objects.create(
            company=company,
            name='Активные корпоративные клиенты',
            category=KPIMetric.Category.GROWTH,
            unit='компаний',
            current_value=Decimal('19'),
            target_value=Decimal('25'),
            direction=KPIMetric.Direction.HIGHER_BETTER,
            period_label='Q4 2026',
            owner=emp_growth,
            description='Компании с оплаченной подпиской и >100 маршрутов в месяц.',
        )
        for offset, val in [(90, '11'), (60, '14'), (30, '17'), (3, '19')]:
            KPIEntry.objects.create(
                metric=kpi_clients,
                recorded_date=today - timedelta(days=offset),
                value=Decimal(val),
                created_by=founder,
            )

        kpi_churn = KPIMetric.objects.create(
            company=company,
            name='Месячный отток клиентов (Churn)',
            category=KPIMetric.Category.FINANCE,
            unit='%',
            current_value=Decimal('2.1'),
            target_value=Decimal('2.5'),
            direction=KPIMetric.Direction.LOWER_BETTER,
            period_label='Q4 2026',
            owner=emp_ceo,
            description='Доля отменённых подписок за календарный месяц.',
        )
        for offset, val in [(90, '3.4'), (60, '2.9'), (30, '2.4'), (4, '2.1')]:
            KPIEntry.objects.create(
                metric=kpi_churn,
                recorded_date=today - timedelta(days=offset),
                value=Decimal(val),
                created_by=founder,
            )

        kpi_sla = KPIMetric.objects.create(
            company=company,
            name='Экономия пробега у клиентов',
            category=KPIMetric.Category.PRODUCT,
            unit='%',
            current_value=Decimal('16.4'),
            target_value=Decimal('18.0'),
            direction=KPIMetric.Direction.HIGHER_BETTER,
            period_label='Q4 2026',
            owner=emp_ml,
            description='Среднее сокращение километража автопарка после перехода на наш алгоритм.',
        )
        for offset, val in [(90, '12.8'), (60, '14.1'), (30, '15.6'), (2, '16.4')]:
            KPIEntry.objects.create(
                metric=kpi_sla,
                recorded_date=today - timedelta(days=offset),
                value=Decimal(val),
                created_by=founder,
            )

        # Activity Logs
        logs = [
            ('Инвестиции', 'Закрыт раунд «Seed Раунд 2026» от фонда Северный Вектор Венчурс на 24 000 000 ₽'),
            ('Расходы', 'Оплачен счёт Selectel Cloud (GPU-инстансы) на сумму 295 000 ₽'),
            ('Задачи', 'Завершена задача «Настроить коннектор обмена заказами с 1С:УТ 11»'),
            ('KPI', 'Обновлён показатель MRR: 1 920 000 ₽ (80% от цели Q4)'),
            ('Команда', 'Анна Лебедева присоединилась к команде на роль Финансовый менеджер'),
        ]
        for action_type, summary in logs:
            ActivityLog.objects.create(
                company=company,
                actor=founder,
                action_type=action_type,
                summary=summary,
            )

        # 2. Second Startup (for workspace switching demonstration)
        company2 = Company.objects.create(
            name='ФинПоток',
            legal_name='ООО «ФинПоток Аналитика»',
            industry='FinTech / Казначейство для МСБ',
            stage=Company.Stage.PRE_SEED,
            currency=Company.Currency.RUB,
            founded_date=today - timedelta(days=120),
            initial_cash=Decimal('1800000.00'),
            target_mrr=Decimal('650000.00'),
            website='https://finpotok.example.ru',
            description='Сервис автоматического платёжного календаря и прогнозирования кассовых разрывов для малого бизнеса.',
            created_by=founder,
        )
        CompanyMembership.objects.create(
            company=company2,
            user=founder,
            role=CompanyMembership.Role.FOUNDER,
        )
        emp2 = Employee.objects.create(
            company=company2,
            user=founder,
            full_name='Алексей Соколов',
            position='Founder & Product Lead',
            department=Employee.Department.PRODUCT,
            email='alexey@finpotok.ru',
            monthly_salary=Decimal('150000.00'),
            status=Employee.Status.ACTIVE,
        )
        b2 = BudgetItem.objects.create(
            company=company2,
            name='Разработка MVP и интеграция с банками',
            category=BudgetCategory.ENGINEERING,
            period='2026-Q4',
            planned_amount=Decimal('900000.00'),
        )
        Expense.objects.create(
            company=company2,
            budget_item=b2,
            category=BudgetCategory.ENGINEERING,
            title='Подряд на банковский API-шлюз',
            vendor='Студия КодФинанс',
            amount=Decimal('320000.00'),
            expense_date=today - timedelta(days=7),
            status=Expense.Status.PAID,
            responsible=emp2,
            created_by=founder,
        )
        Task.objects.create(
            company=company2,
            title='Запустить закрытое бета-тестирование с 15 предпринимателями',
            assignee=emp2,
            created_by=founder,
            priority=Task.Priority.HIGH,
            status=Task.Status.IN_PROGRESS,
            due_date=today + timedelta(days=10),
            milestone='Beta Launch',
            estimated_hours=12,
        )
        KPIMetric.objects.create(
            company=company2,
            name='Компании в бета-пилоте',
            category=KPIMetric.Category.GROWTH,
            unit='компаний',
            current_value=Decimal('9'),
            target_value=Decimal('15'),
            period_label='Q4 2026',
            owner=emp2,
        )
        ActivityLog.objects.create(
            company=company2,
            actor=founder,
            action_type='Компания',
            summary='Зарегистрирована компания «ФинПоток» (Pre-Seed)',
        )

        self._seed_growth_modules(company, today)
        self.stdout.write(self.style.SUCCESS('Демо-данные VectorStartUp успешно созданы (2 стартапа + все модули роста).'))

    def _seed_growth_modules(self, company: Company, today) -> bool:
        """Idempotently populate CRM deals, invoices, roadmap, unit economics, cap table, experiments & data room."""
        created_any = False
        emp_ceo = Employee.objects.filter(company=company, full_name__icontains='Соколов').first()
        emp_cto = Employee.objects.filter(company=company, full_name__icontains='Волкова').first()
        emp_growth = Employee.objects.filter(company=company, full_name__icontains='Смирнов').first()
        emp_fin = Employee.objects.filter(company=company, full_name__icontains='Лебедева').first()
        emp_ml = Employee.objects.filter(company=company, full_name__icontains='Орлов').first()

        # 1. Unit Economics Profile
        if not UnitEconomicsProfile.objects.filter(company=company).exists():
            UnitEconomicsProfile.objects.create(
                company=company,
                arpu=Decimal('101000.00'),
                gross_margin_pct=Decimal('79.5'),
                monthly_churn_pct=Decimal('2.10'),
                cac=Decimal('245000.00'),
                active_customers=19,
                monthly_growth_pct=Decimal('12.5'),
            )
            created_any = True

        # 2. B2B Sales CRM Deals
        if not Deal.objects.filter(company=company).exists():
            deals_seed = [
                ('Сеть «ВолгаРитейл» (120 машин)', 'Андрей Никитин', 'anikitin@volgaretail.example.ru', Decimal('2880000.00'), Deal.BillingType.ANNUAL, Deal.Stage.CONTRACT, 85, today + timedelta(days=9), emp_growth, 'Согласуем SLA и график интеграции с 1С.'),
                ('ТК «СеверЭкспресс»', 'Ольга Фёдорова', 'ofedorova@severexp.example.ru', Decimal('1920000.00'), Deal.BillingType.ANNUAL, Deal.Stage.DEMO, 60, today + timedelta(days=22), emp_growth, 'Запущен пилот на 45 машинах в Санкт-Петербурге.'),
                ('Дистрибьютор «АгроФреш»', 'Павел Егоров', 'pegorov@agrofresh.example.ru', Decimal('185000.00'), Deal.BillingType.MONTHLY, Deal.Stage.QUALIFIED, 35, today + timedelta(days=34), emp_growth, 'Интересует учёт температурных окон доставки.'),
                ('ФармЛогистика Плюс', 'Наталья Белова', 'nbelova@pharmlog.example.ru', Decimal('3600000.00'), Deal.BillingType.ANNUAL, Deal.Stage.LEAD, 15, today + timedelta(days=50), emp_ceo, 'Тёплое интро от ангельского синдиката.'),
                ('УралТранс Групп', 'Сергей Макаров', 'smakarov@uraltrans.example.ru', Decimal('2160000.00'), Deal.BillingType.ANNUAL, Deal.Stage.WON, 100, today - timedelta(days=14), emp_growth, 'Годовой контракт подписан и оплачен.'),
            ]
            for name, contact, email, amt, btype, stage, prob, close_dt, owner, notes in deals_seed:
                Deal.objects.create(
                    company=company,
                    client_name=name,
                    contact_name=contact,
                    contact_email=email,
                    amount=amt,
                    billing_type=btype,
                    stage=stage,
                    probability=prob,
                    expected_close_date=close_dt,
                    owner=owner,
                    notes=notes,
                )
            created_any = True

        # 3. Client Invoices & Receivables
        if not Invoice.objects.filter(company=company).exists():
            invoices_seed = [
                ('INV-2026-041', 'УралТранс Групп', 'Годовая SaaS-лицензия (тариф Enterprise, 80 машин)', Decimal('2160000.00'), False, today - timedelta(days=20), today - timedelta(days=10), today - timedelta(days=12), Invoice.Status.PAID),
                ('INV-2026-042', 'ЛогистикЮг ООО', 'Подписка «НейроЛогистика Про» за ноябрь', Decimal('195000.00'), False, today - timedelta(days=16), today - timedelta(days=4), None, Invoice.Status.SENT),
                ('INV-2026-043', 'ТК «СеверЭкспресс»', 'Пилотное внедрение и настройка коннектора 1С', Decimal('340000.00'), True, today - timedelta(days=5), today + timedelta(days=8), None, Invoice.Status.SENT),
                ('INV-2026-044', 'Сеть «ВолгаРитейл»', 'Авансовый платёж по годовому контракту (черновик)', Decimal('720000.00'), True, today, today + timedelta(days=14), None, Invoice.Status.DRAFT),
            ]
            for num, client, svc, amt, vat, iss, due, paid, st in invoices_seed:
                Invoice.objects.create(
                    company=company,
                    invoice_number=num,
                    client_name=client,
                    service_title=svc,
                    amount=amt,
                    vat_included=vat,
                    issue_date=iss,
                    due_date=due,
                    paid_date=paid,
                    status=st,
                )
            created_any = True

        # 4. Quarterly Roadmap Milestones + Checklists
        if not RoadmapMilestone.objects.filter(company=company).exists():
            ms1 = RoadmapMilestone.objects.create(
                company=company,
                title='Релиз ML-маршрутизатора v2.4 (<1.2 сек на 500 точек)',
                quarter='2026-Q4',
                category=RoadmapMilestone.Category.PRODUCT,
                status=RoadmapMilestone.Status.IN_PROGRESS,
                due_date=today + timedelta(days=18),
                owner=emp_ml,
                summary='Сокращение времени расчёта и поддержка мультитемпературных кузовов.',
            )
            for title, done in [
                ('Батчинг матрицы расстояний на GPU', True),
                ('Учёт временных окон разгрузки в ритейле', True),
                ('Нагрузочное тестирование на датасете ВолгаРитейл', False),
            ]:
                MilestoneCheckItem.objects.create(milestone=ms1, title=title, is_done=done)

            ms2 = RoadmapMilestone.objects.create(
                company=company,
                title='Достичь 2,4 млн ₽ MRR и 25 корпоративных клиентов',
                quarter='2026-Q4',
                category=RoadmapMilestone.Category.REVENUE,
                status=RoadmapMilestone.Status.IN_PROGRESS,
                due_date=today + timedelta(days=38),
                owner=emp_growth,
                summary='Закрытие enterprise-сделок из Q4 пайплайна.',
            )
            for title, done in [
                ('Подписать контракт с УралТранс Групп', True),
                ('Завершить пилот с СеверЭкспресс', False),
                ('Подписать договор с ВолгаРитейл', False),
            ]:
                MilestoneCheckItem.objects.create(milestone=ms2, title=title, is_done=done)

            ms3 = RoadmapMilestone.objects.create(
                company=company,
                title='Подготовка к Series A и завершение Data Room',
                quarter='2027-Q1',
                category=RoadmapMilestone.Category.FUNDRAISING,
                status=RoadmapMilestone.Status.PLANNED,
                due_date=today + timedelta(days=95),
                owner=emp_ceo,
                summary='Сбор аудированной финмодели, кейсов ROI и шорт-листа фондов.',
            )
            for title, done in [
                ('Собрать 5 подтверждённых кейсов экономии пробега', False),
                ('Обновить питч-дек под Series A', False),
                ('Пройти юридический due diligence IP', False),
            ]:
                MilestoneCheckItem.objects.create(milestone=ms3, title=title, is_done=done)
            created_any = True

        # 5. Detailed Cap Table & Vesting
        if not EquityHolder.objects.filter(company=company).exists():
            holders_seed = [
                ('Алексей Соколов (CEO & Co-Founder)', EquityHolder.Role.FOUNDER, Decimal('44.00'), 48, 12, today - timedelta(days=410), 'Стандартный 4-летний вестинг с клиффом 12 мес.'),
                ('Мария Волкова (CTO & Co-Founder)', EquityHolder.Role.FOUNDER, Decimal('24.50'), 48, 12, today - timedelta(days=395), 'Ключевой сооснователь, технический директор.'),
                ('Северный Вектор Венчурс (Seed)', EquityHolder.Role.INVESTOR, Decimal('14.00'), 0, 0, today - timedelta(days=75), 'Лид-инвестор Seed-раунда, привилегированные права 1x.'),
                ('Виктор Морозов (Ангельский синдикат)', EquityHolder.Role.INVESTOR, Decimal('7.50'), 0, 0, today - timedelta(days=280), 'Pre-Seed раунд, без вестинга.'),
                ('Опционный пул команды (ESOP)', EquityHolder.Role.ESOP, Decimal('8.50'), 48, 12, today - timedelta(days=300), 'Зарезервирован под ключевых инженеров и коммерческий блок.'),
                ('Сергей Волгин (Индустриальный советник)', EquityHolder.Role.ADVISOR, Decimal('1.50'), 24, 6, today - timedelta(days=210), 'Эксперт по федеральным сетям ритейла.'),
            ]
            for name, role, pct, vest, cliff, sdate, notes in holders_seed:
                EquityHolder.objects.create(
                    company=company,
                    name=name,
                    role=role,
                    ownership_pct=pct,
                    vesting_months=vest,
                    cliff_months=cliff,
                    start_date=sdate,
                    notes=notes,
                )
            created_any = True

        # 6. Growth Experiments (ICE)
        if not GrowthExperiment.objects.filter(company=company).exists():
            exps_seed = [
                ('Калькулятор ROI на лендинге по числу грузовиков', 'Если показать директору по логистике расчёт экономии топлива за 30 секунд до звонка, конверсия в демо вырастет на 35%.', 'Конверсия сайт → демо', 9, 8, 8, GrowthExperiment.Status.RUNNING, emp_growth, 'Запущен A/B-тест на входящем трафике.'),
                ('Бесплатный аудит 1 дня маршрутов из Excel', 'Если загружать реальный реестр заказов клиента и отдавать сравнение пробега за 24 часа, цикл сделки сократится на 3 недели.', 'Скорость закрытия пилота', 9, 9, 6, GrowthExperiment.Status.VALIDATED, emp_ml, 'Подтверждено: 3 из 4 клиентов перешли в платный пилот.'),
                ('Партнёрская программа с интеграторами 1С', 'Если делиться 15% от первого года подписки с 1С-франчайзи, получим стабильный канал тёплых лидов.', 'Новые B2B-лиды / мес', 8, 6, 5, GrowthExperiment.Status.IDEA, emp_ceo, ''),
            ]
            for title, hyp, metric, imp, conf, ease, st, owner, note in exps_seed:
                GrowthExperiment.objects.create(
                    company=company,
                    title=title,
                    hypothesis=hyp,
                    target_metric=metric,
                    impact=imp,
                    confidence=conf,
                    ease=ease,
                    status=st,
                    owner=owner,
                    outcome_note=note,
                )
            created_any = True

        # 7. Investor Data Room Docs
        if not DataRoomDoc.objects.filter(company=company).exists():
            docs_seed = [
                ('Pitch Deck - НейроЛогистика (Seed / Series A)', DataRoomDoc.Category.PITCH, DataRoomDoc.AccessLevel.INVESTORS, DataRoomDoc.Status.READY, 'v3.2', emp_ceo, 'Презентация продукта, рынка, трекшена и плана роста на 24 месяца.'),
                ('Финансовая модель и P&L прогноз (2026–2028)', DataRoomDoc.Category.FINANCE, DataRoomDoc.AccessLevel.INVESTORS, DataRoomDoc.Status.READY, 'v2.4', emp_fin, 'Детализированный прогноз MRR, CAC/LTV, штатного расписания и Cash Flow.'),
                ('Свидетельство о регистрации ПО и отчуждение IP', DataRoomDoc.Category.IP, DataRoomDoc.AccessLevel.INVESTORS, DataRoomDoc.Status.READY, 'v1.0', emp_cto, 'Договоры передачи исключительных прав на исходный код и ML-модели.'),
                ('Реестр действующих B2B-контрактов и SLA', DataRoomDoc.Category.CONTRACTS, DataRoomDoc.AccessLevel.INVESTORS, DataRoomDoc.Status.UPDATING, 'v1.8', emp_growth, 'Обезличенный свод контрактов, чеков и условий продления.'),
                ('Корпоративный договор и устав ООО', DataRoomDoc.Category.LEGAL, DataRoomDoc.AccessLevel.FOUNDERS, DataRoomDoc.Status.READY, 'v2.0', emp_ceo, 'Актуальная редакция после закрытия Seed-раунда.'),
                ('Положение об опционной программе (ESOP)', DataRoomDoc.Category.TEAM, DataRoomDoc.AccessLevel.TEAM, DataRoomDoc.Status.DRAFT, 'v0.9', emp_fin, 'Правила вестинга и распределения опционов среди сотрудников.'),
            ]
            for title, cat, acc, st, ver, owner, summary in docs_seed:
                DataRoomDoc.objects.create(
                    company=company,
                    title=title,
                    category=cat,
                    access_level=acc,
                    status=st,
                    version_label=ver,
                    owner=owner,
                    summary=summary,
                    updated_at=today - timedelta(days=3),
                )
            created_any = True

        return created_any

