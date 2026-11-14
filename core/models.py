"""
Django ORM models for VectorStartUp (Startup & Early-Stage Company Operating Platform).
All domain entities are scoped to a Company workspace with strict relational integrity.
"""

from datetime import timedelta
from decimal import Decimal
import secrets
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Company(models.Model):
    class Stage(models.TextChoices):
        IDEA = 'IDEA', 'Идея / MVP'
        PRE_SEED = 'PRE_SEED', 'Pre-Seed'
        SEED = 'SEED', 'Seed'
        SERIES_A = 'SERIES_A', 'Series A'
        SERIES_B = 'SERIES_B', 'Series B+'
        BOOTSTRAPPED = 'BOOTSTRAPPED', 'Бутстрэппинг'

    class Currency(models.TextChoices):
        RUB = 'RUB', '₽ RUB'
        USD = 'USD', '$ USD'
        EUR = 'EUR', '€ EUR'

    name = models.CharField('Название компании', max_length=140)
    legal_name = models.CharField('Юридическое наименование', max_length=200, blank=True)
    industry = models.CharField('Отрасль', max_length=120, default='B2B SaaS')
    stage = models.CharField('Стадия развития', max_length=20, choices=Stage.choices, default=Stage.PRE_SEED)
    currency = models.CharField('Основная валюта', max_length=3, choices=Currency.choices, default=Currency.RUB)
    founded_date = models.DateField('Дата основания', default=timezone.localdate)
    initial_cash = models.DecimalField(
        'Начальный капитал / остаток',
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    target_mrr = models.DecimalField(
        'Целевой MRR',
        max_digits=14,
        decimal_places=2,
        default=Decimal('500000.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    website = models.URLField('Веб-сайт', blank=True)
    description = models.TextField('Миссия и описание продукта', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_companies',
        verbose_name='Создатель',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name

    @property
    def currency_symbol(self) -> str:
        return {'RUB': '₽', 'USD': '$', 'EUR': '€'}.get(self.currency, '₽')


class CompanyMembership(models.Model):
    class Role(models.TextChoices):
        FOUNDER = 'FOUNDER', 'Основатель (CEO)'
        FINANCE = 'FINANCE', 'Финансовый директор (CFO)'
        MANAGER = 'MANAGER', 'Руководитель направления'
        MEMBER = 'MEMBER', 'Участник команды'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='memberships', verbose_name='Компания')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_memberships',
        verbose_name='Пользователь',
    )
    role = models.CharField('Роль', max_length=20, choices=Role.choices, default=Role.FOUNDER)
    joined_at = models.DateTimeField('Присоединился', auto_now_add=True)

    class Meta:
        verbose_name = 'Участник компании'
        verbose_name_plural = 'Участники компаний'
        unique_together = ('company', 'user')

    def __str__(self) -> str:
        return f'{self.user.username} - {self.company.name} ({self.get_role_display()})'


class Employee(models.Model):
    class Department(models.TextChoices):
        ENGINEERING = 'ENGINEERING', 'Разработка'
        PRODUCT = 'PRODUCT', 'Продукт'
        DESIGN = 'DESIGN', 'Дизайн'
        MARKETING = 'MARKETING', 'Маркетинг и рост'
        SALES = 'SALES', 'Продажи'
        FINANCE = 'FINANCE', 'Финансы и право'
        OPERATIONS = 'OPERATIONS', 'Операции'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Активен'
        ONBOARDING = 'ONBOARDING', 'Онбординг'
        INACTIVE = 'INACTIVE', 'Архив'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees', verbose_name='Компания')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profiles',
        verbose_name='Аккаунт пользователя',
    )
    full_name = models.CharField('ФИО', max_length=160)
    position = models.CharField('Должность', max_length=120)
    department = models.CharField('Отдел', max_length=20, choices=Department.choices, default=Department.ENGINEERING)
    email = models.EmailField('Рабочий Email', blank=True)
    phone = models.CharField('Телефон / Telegram', max_length=60, blank=True)
    monthly_salary = models.DecimalField(
        'Оклад в месяц',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    equity_options_pct = models.DecimalField(
        'Опционы / доля (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    hired_at = models.DateField('Дата выхода', default=timezone.localdate)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ['status', 'full_name']

    def __str__(self) -> str:
        return f'{self.full_name} ({self.position})'


class BudgetCategory(models.TextChoices):
    PAYROLL = 'PAYROLL', 'ФОТ и команда'
    ENGINEERING = 'ENGINEERING', 'Разработка и R&D'
    CLOUD = 'CLOUD', 'Инфраструктура и облако'
    MARKETING = 'MARKETING', 'Маркетинг и привлечение'
    SALES = 'SALES', 'Продажи и клиентский сервис'
    LEGAL = 'LEGAL', 'Юристы, бухгалтерия и налоги'
    OFFICE = 'OFFICE', 'Офис и операционные расходы'
    OTHER = 'OTHER', 'Прочее'


class BudgetItem(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='budget_items', verbose_name='Компания')
    name = models.CharField('Статья бюджета', max_length=160)
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=BudgetCategory.choices,
        default=BudgetCategory.ENGINEERING,
    )
    period = models.CharField('Период (напр. 2026-Q4)', max_length=32, default='2026-Q4')
    planned_amount = models.DecimalField(
        'Плановая сумма',
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    notes = models.TextField('Комментарий и обоснование', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Статья бюджета'
        verbose_name_plural = 'Статьи бюджета'
        ordering = ['-period', 'category', 'name']

    def __str__(self) -> str:
        return f'{self.name} ({self.period})'


class Expense(models.Model):
    class Status(models.TextChoices):
        PAID = 'PAID', 'Оплачено'
        PENDING = 'PENDING', 'Ожидает оплаты'
        DRAFT = 'DRAFT', 'Черновик'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='expenses', verbose_name='Компания')
    budget_item = models.ForeignKey(
        BudgetItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Статья бюджета',
    )
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=BudgetCategory.choices,
        default=BudgetCategory.ENGINEERING,
    )
    title = models.CharField('Наименование расхода', max_length=180)
    vendor = models.CharField('Контрагент / сервис', max_length=140, blank=True)
    amount = models.DecimalField(
        'Сумма',
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    expense_date = models.DateField('Дата расхода', default=timezone.localdate)
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.PAID)
    is_recurring = models.BooleanField('Регулярный (ежемесячный)', default=False)
    responsible = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Ответственный',
    )
    notes = models.TextField('Примечание', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logged_expenses',
        verbose_name='Добавил',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-expense_date', '-created_at']

    def __str__(self) -> str:
        return f'{self.title} - {self.amount}'


class Investor(models.Model):
    class InvestorType(models.TextChoices):
        VC = 'VC', 'Венчурный фонд (VC)'
        ANGEL = 'ANGEL', 'Бизнес-ангел'
        ACCELERATOR = 'ACCELERATOR', 'Акселератор'
        GRANT = 'GRANT', 'Грантовый фонд'
        CORPORATE = 'CORPORATE', 'Корпоративный инвестор'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='investors', verbose_name='Компания')
    name = models.CharField('Название фонда / ФИО инвестора', max_length=160)
    investor_type = models.CharField('Тип', max_length=20, choices=InvestorType.choices, default=InvestorType.VC)
    contact_name = models.CharField('Контактное лицо', max_length=140, blank=True)
    email = models.EmailField('Email', blank=True)
    website = models.URLField('Сайт', blank=True)
    typical_check = models.CharField('Типовой чек', max_length=80, blank=True)
    notes = models.TextField('Заметки по переговорам', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Инвестор'
        verbose_name_plural = 'Инвесторы'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class FundingRound(models.Model):
    class Status(models.TextChoices):
        NEGOTIATION = 'NEGOTIATION', 'Переговоры'
        TERM_SHEET = 'TERM_SHEET', 'Term Sheet'
        CLOSED = 'CLOSED', 'Закрыт (деньги получены)'

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='funding_rounds',
        verbose_name='Компания',
    )
    investor = models.ForeignKey(
        Investor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funding_rounds',
        verbose_name='Лид-инвестор / фонд',
    )
    round_name = models.CharField('Название раунда', max_length=120)
    stage = models.CharField('Стадия', max_length=20, choices=Company.Stage.choices, default=Company.Stage.SEED)
    amount = models.DecimalField(
        'Сумма инвестиций',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    equity_percent = models.DecimalField(
        'Доля инвестора (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    pre_money_valuation = models.DecimalField(
        'Pre-money оценка',
        max_digits=16,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    closed_date = models.DateField('Дата закрытия / план', default=timezone.localdate)
    status = models.CharField('Статус сделки', max_length=20, choices=Status.choices, default=Status.CLOSED)
    notes = models.TextField('Условия и ковенанты', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Инвестиционный раунд'
        verbose_name_plural = 'Инвестиционные раунды'
        ordering = ['-closed_date', '-created_at']

    def __str__(self) -> str:
        return f'{self.round_name} ({self.amount})'


class InvestmentAllocation(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='investment_allocations',
        verbose_name='Компания',
    )
    funding_round = models.ForeignKey(
        FundingRound,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name='Инвестиционный раунд',
    )
    bucket_name = models.CharField('Направление распределения', max_length=160)
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=BudgetCategory.choices,
        default=BudgetCategory.ENGINEERING,
    )
    allocated_amount = models.DecimalField(
        'Выделенная сумма',
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    spent_amount = models.DecimalField(
        'Освоено',
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    target_milestone = models.CharField('Целевая веха (Milestone)', max_length=200, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Распределение инвестиций'
        verbose_name_plural = 'Распределения инвестиций'
        ordering = ['-allocated_amount']

    def __str__(self) -> str:
        return f'{self.bucket_name} - {self.funding_round.round_name}'

    @property
    def share_of_round_pct(self) -> float:
        if not self.funding_round.amount:
            return 0.0
        return round(float(self.allocated_amount / self.funding_round.amount * 100), 1)

    @property
    def utilization_pct(self) -> float:
        if not self.allocated_amount:
            return 0.0
        return round(min(float(self.spent_amount / self.allocated_amount * 100), 999.0), 1)


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Низкий'
        MEDIUM = 'MEDIUM', 'Средний'
        HIGH = 'HIGH', 'Высокий'
        CRITICAL = 'CRITICAL', 'Критический'

    class Status(models.TextChoices):
        BACKLOG = 'BACKLOG', 'Бэклог'
        IN_PROGRESS = 'IN_PROGRESS', 'В работе'
        IN_REVIEW = 'IN_REVIEW', 'На ревью'
        DONE = 'DONE', 'Готово'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='tasks', verbose_name='Компания')
    title = models.CharField('Название задачи', max_length=200)
    description = models.TextField('Описание и критерии приёмки', blank=True)
    assignee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='Исполнитель',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        verbose_name='Автор',
    )
    priority = models.CharField('Приоритет', max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField('Статус', max_length=16, choices=Status.choices, default=Status.BACKLOG)
    due_date = models.DateField('Срок выполнения', null=True, blank=True)
    milestone = models.CharField('Спринт / веха', max_length=80, blank=True)
    estimated_hours = models.PositiveIntegerField('Оценка (часы)', default=4)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['due_date', '-created_at']

    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_date
            and self.status != self.Status.DONE
            and self.due_date < timezone.localdate()
        )


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name='Задача')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_comments',
        verbose_name='Автор',
    )
    body = models.TextField('Комментарий')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий к задаче'
        verbose_name_plural = 'Комментарии к задачам'
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'Комментарий к #{self.task_id}'


class KPIMetric(models.Model):
    class Category(models.TextChoices):
        REVENUE = 'REVENUE', 'Выручка'
        GROWTH = 'GROWTH', 'Рост и маркетинг'
        PRODUCT = 'PRODUCT', 'Продукт'
        FINANCE = 'FINANCE', 'Юнит-экономика'
        TEAM = 'TEAM', 'Команда'

    class Direction(models.TextChoices):
        HIGHER_BETTER = 'HIGHER_BETTER', 'Чем выше, тем лучше'
        LOWER_BETTER = 'LOWER_BETTER', 'Чем ниже, тем лучше'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='kpis', verbose_name='Компания')
    name = models.CharField('Название метрики', max_length=140)
    category = models.CharField('Группа', max_length=20, choices=Category.choices, default=Category.REVENUE)
    unit = models.CharField('Единица измерения', max_length=20, default='₽')
    current_value = models.DecimalField('Текущее значение', max_digits=14, decimal_places=2, default=Decimal('0.00'))
    target_value = models.DecimalField('Целевое значение', max_digits=14, decimal_places=2, default=Decimal('100.00'))
    direction = models.CharField(
        'Направление цели',
        max_length=20,
        choices=Direction.choices,
        default=Direction.HIGHER_BETTER,
    )
    period_label = models.CharField('Период', max_length=40, default='Q4 2026')
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kpis',
        verbose_name='Ответственный',
    )
    description = models.TextField('Методика расчёта', blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'KPI-метрика'
        verbose_name_plural = 'KPI-метрики'
        ordering = ['category', 'name']

    def __str__(self) -> str:
        return f'{self.name} ({self.period_label})'

    @property
    def progress_percent(self) -> float:
        if self.target_value == 0:
            return 0.0
        if self.direction == self.Direction.HIGHER_BETTER:
            pct = float(self.current_value / self.target_value * 100)
        else:
            if self.current_value <= 0:
                return 100.0
            pct = float(self.target_value / self.current_value * 100)
        return round(max(0.0, min(pct, 150.0)), 1)

    @property
    def progress_bar_width(self) -> float:
        return min(self.progress_percent, 100.0)

    @property
    def health_state(self) -> str:
        pct = self.progress_percent
        if pct >= 85:
            return 'good'
        if pct >= 55:
            return 'warn'
        return 'risk'

    @property
    def health_label(self) -> str:
        return {
            'good': 'По плану',
            'warn': 'Требует внимания',
            'risk': 'Отставание',
        }[self.health_state]


class KPIEntry(models.Model):
    metric = models.ForeignKey(KPIMetric, on_delete=models.CASCADE, related_name='entries', verbose_name='Метрика')
    recorded_date = models.DateField('Дата замера', default=timezone.localdate)
    value = models.DecimalField('Значение', max_digits=14, decimal_places=2)
    note = models.CharField('Комментарий', max_length=220, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Зафиксировал',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Замер KPI'
        verbose_name_plural = 'Замеры KPI'
        ordering = ['recorded_date', 'created_at']

    def __str__(self) -> str:
        return f'{self.metric.name}: {self.value} ({self.recorded_date})'


class ActivityLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='activities', verbose_name='Компания')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь',
    )
    action_type = models.CharField('Раздел', max_length=40)
    summary = models.CharField('Событие', max_length=260)
    created_at = models.DateTimeField('Время', auto_now_add=True)

    class Meta:
        verbose_name = 'Событие'
        verbose_name_plural = 'Журнал событий'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.summary


class EmailVerificationCode(models.Model):
    """Stores 6-digit email verification codes in DB with TTL and attempt limits."""

    MAX_ATTEMPTS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_codes',
        verbose_name='Пользователь',
    )
    email = models.EmailField('Email')
    code = models.CharField('Код подтверждения', max_length=6)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    expires_at = models.DateTimeField('Действителен до')
    is_used = models.BooleanField('Использован', default=False)
    attempts = models.PositiveSmallIntegerField('Попытки ввода', default=0)

    class Meta:
        verbose_name = 'Код подтверждения Email'
        verbose_name_plural = 'Коды подтверждения Email'
        ordering = ['-created_at']

    def __str__(self) -> str:
        status = 'использован' if self.is_used else 'активен'
        return f'{self.email} ({status})'

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def remaining_attempts(self) -> int:
        return max(0, self.MAX_ATTEMPTS - self.attempts)

    @property
    def is_valid(self) -> bool:
        return (not self.is_used) and (not self.is_expired) and self.attempts < self.MAX_ATTEMPTS

    @classmethod
    def create_for_user(cls, user, ttl_minutes: int | None = None):
        """Invalidate previous unused codes and issue a fresh cryptographically random 6-digit code."""
        ttl = ttl_minutes or getattr(settings, 'EMAIL_VERIFICATION_TTL_MINUTES', 15)
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = f'{secrets.randbelow(1_000_000):06d}'
        return cls.objects.create(
            user=user,
            email=user.email.strip().lower(),
            code=code,
            expires_at=timezone.now() + timedelta(minutes=ttl),
        )


class Deal(models.Model):
    """B2B Sales CRM deal scoped to a startup company."""

    class Stage(models.TextChoices):
        LEAD = 'LEAD', 'Лид'
        QUALIFIED = 'QUALIFIED', 'Квалификация'
        DEMO = 'DEMO', 'Демо / пилот'
        CONTRACT = 'CONTRACT', 'Договор'
        WON = 'WON', 'Выиграна'
        LOST = 'LOST', 'Проиграна'

    class BillingType(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Ежемесячно (MRR)'
        ANNUAL = 'ANNUAL', 'Годовой контракт'
        ONE_TIME = 'ONE_TIME', 'Разовый проект'

    STAGE_DEFAULT_PROBABILITY = {
        'LEAD': 15,
        'QUALIFIED': 35,
        'DEMO': 60,
        'CONTRACT': 85,
        'WON': 100,
        'LOST': 0,
    }

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='deals', verbose_name='Компания')
    client_name = models.CharField('Клиент / организация', max_length=180)
    contact_name = models.CharField('Контактное лицо', max_length=140, blank=True)
    contact_email = models.EmailField('Email контакта', blank=True)
    amount = models.DecimalField(
        'Сумма контракта',
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    billing_type = models.CharField(
        'Тип оплаты',
        max_length=16,
        choices=BillingType.choices,
        default=BillingType.ANNUAL,
    )
    stage = models.CharField('Этап воронки', max_length=16, choices=Stage.choices, default=Stage.LEAD)
    probability = models.PositiveSmallIntegerField(
        'Вероятность (%)',
        default=25,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    expected_close_date = models.DateField('Плановая дата закрытия', null=True, blank=True)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deals',
        verbose_name='Ответственный',
    )
    notes = models.TextField('Детали переговоров', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Сделка CRM'
        verbose_name_plural = 'Сделки CRM'
        ordering = ['expected_close_date', '-amount']

    def __str__(self) -> str:
        return f'{self.client_name} ({self.get_stage_display()})'

    @property
    def weighted_amount(self) -> Decimal:
        return (self.amount * Decimal(self.probability) / Decimal('100')).quantize(Decimal('1'))


class RoadmapMilestone(models.Model):
    """Quarterly strategic company milestone with checklist."""

    class Category(models.TextChoices):
        PRODUCT = 'PRODUCT', 'Продукт'
        REVENUE = 'REVENUE', 'Выручка и продажи'
        FUNDRAISING = 'FUNDRAISING', 'Инвестиции'
        TEAM = 'TEAM', 'Команда'
        OPERATIONS = 'OPERATIONS', 'Операции и право'

    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Запланировано'
        IN_PROGRESS = 'IN_PROGRESS', 'В работе'
        AT_RISK = 'AT_RISK', 'Под риском'
        COMPLETED = 'COMPLETED', 'Выполнено'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='milestones', verbose_name='Компания')
    title = models.CharField('Название вехи', max_length=200)
    quarter = models.CharField('Квартал (напр. 2026-Q4)', max_length=24, default='2026-Q4')
    category = models.CharField('Направление', max_length=20, choices=Category.choices, default=Category.PRODUCT)
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.PLANNED)
    due_date = models.DateField('Целевой срок', null=True, blank=True)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='milestones',
        verbose_name='Ответственный',
    )
    summary = models.TextField('Критерии достижения', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Веха дорожной карты'
        verbose_name_plural = 'Вехи дорожной карты'
        ordering = ['quarter', 'due_date', '-created_at']

    def __str__(self) -> str:
        return f'[{self.quarter}] {self.title}'

    @property
    def progress_percent(self) -> int:
        if self.status == self.Status.COMPLETED:
            return 100
        items = list(self.checklist_items.all())
        if not items:
            if self.status == self.Status.IN_PROGRESS:
                return 40
            if self.status == self.Status.AT_RISK:
                return 25
            return 0
        done_count = sum(1 for item in items if item.is_done)
        return round((done_count / len(items)) * 100)


class MilestoneCheckItem(models.Model):
    milestone = models.ForeignKey(
        RoadmapMilestone,
        on_delete=models.CASCADE,
        related_name='checklist_items',
        verbose_name='Веха',
    )
    title = models.CharField('Пункт чек-листа', max_length=220)
    is_done = models.BooleanField('Выполнено', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Пункт вехи'
        verbose_name_plural = 'Пункты вех'
        ordering = ['id']

    def __str__(self) -> str:
        return self.title


class UnitEconomicsProfile(models.Model):
    """Editable SaaS unit economics parameters per company."""

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='unit_economics',
        verbose_name='Компания',
    )
    arpu = models.DecimalField(
        'ARPU (выручка с клиента / мес)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('95000.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    gross_margin_pct = models.DecimalField(
        'Валовая маржа (%)',
        max_digits=5,
        decimal_places=1,
        default=Decimal('78.0'),
        validators=[MinValueValidator(Decimal('0.0')), MaxValueValidator(Decimal('100.0'))],
    )
    monthly_churn_pct = models.DecimalField(
        'Месячный отток Churn (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.10'),
        validators=[MinValueValidator(Decimal('0.10')), MaxValueValidator(Decimal('100.00'))],
    )
    cac = models.DecimalField(
        'CAC (стоимость привлечения клиента)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('240000.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    active_customers = models.PositiveIntegerField('Платящих клиентов', default=19)
    monthly_growth_pct = models.DecimalField(
        'Рост выручки MoM (%)',
        max_digits=5,
        decimal_places=1,
        default=Decimal('11.5'),
        validators=[MinValueValidator(Decimal('-50.0')), MaxValueValidator(Decimal('200.0'))],
    )
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Профиль юнит-экономики'
        verbose_name_plural = 'Профили юнит-экономики'

    def __str__(self) -> str:
        return f'Unit-экономика: {self.company.name}'


class Invoice(models.Model):
    """Client invoices and accounts receivable tracking."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Черновик'
        SENT = 'SENT', 'Выставлен'
        PAID = 'PAID', 'Оплачен'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices', verbose_name='Компания')
    invoice_number = models.CharField('Номер счёта', max_length=40)
    client_name = models.CharField('Клиент / плательщик', max_length=180)
    service_title = models.CharField('Наименование услуги / тарифа', max_length=240)
    amount = models.DecimalField(
        'Сумма счёта',
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    vat_included = models.BooleanField('Включая НДС 20%', default=False)
    issue_date = models.DateField('Дата выставления', default=timezone.localdate)
    due_date = models.DateField('Срок оплаты', default=timezone.localdate)
    paid_date = models.DateField('Дата фактической оплаты', null=True, blank=True)
    status = models.CharField('Статус', max_length=16, choices=Status.choices, default=Status.SENT)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Счёт на оплату'
        verbose_name_plural = 'Счета и дебиторка'
        ordering = ['-issue_date', '-created_at']

    def __str__(self) -> str:
        return f'Счёт № {self.invoice_number} - {self.client_name}'

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.status == self.Status.SENT
            and self.due_date
            and self.due_date < timezone.localdate()
        )


class EquityHolder(models.Model):
    """Detailed Cap Table entry with vesting schedule."""

    class Role(models.TextChoices):
        FOUNDER = 'FOUNDER', 'Основатель'
        INVESTOR = 'INVESTOR', 'Инвестор'
        ESOP = 'ESOP', 'Опционный пул (ESOP)'
        ADVISOR = 'ADVISOR', 'Советник'

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='equity_holders',
        verbose_name='Компания',
    )
    name = models.CharField('Держатель / фонд / пул', max_length=180)
    role = models.CharField('Категория', max_length=16, choices=Role.choices, default=Role.FOUNDER)
    ownership_pct = models.DecimalField(
        'Доля (%)',
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
    )
    vesting_months = models.PositiveSmallIntegerField('Вестинг (мес., 0 - без вестинга)', default=48)
    cliff_months = models.PositiveSmallIntegerField('Клифф (мес.)', default=12)
    start_date = models.DateField('Дата начала вестинга', default=timezone.localdate)
    notes = models.TextField('Условия владения', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Участник Cap Table'
        verbose_name_plural = 'Участники Cap Table'
        ordering = ['-ownership_pct', 'name']

    def __str__(self) -> str:
        return f'{self.name} ({self.ownership_pct}%)'


class GrowthExperiment(models.Model):
    """Product & growth hypothesis prioritized by ICE score."""

    class Status(models.TextChoices):
        IDEA = 'IDEA', 'Идея'
        RUNNING = 'RUNNING', 'Идёт тест'
        VALIDATED = 'VALIDATED', 'Подтверждена'
        REJECTED = 'REJECTED', 'Отклонена'

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='experiments',
        verbose_name='Компания',
    )
    title = models.CharField('Название гипотезы', max_length=200)
    hypothesis = models.TextField('Формулировка гипотезы (Если... то...)')
    target_metric = models.CharField('Целевая метрика', max_length=120, default='Конверсия в оплату')
    impact = models.PositiveSmallIntegerField(
        'Влияние (Impact, 1–10)',
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    confidence = models.PositiveSmallIntegerField(
        'Уверенность (Confidence, 1–10)',
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    ease = models.PositiveSmallIntegerField(
        'Простота (Ease, 1–10)',
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    status = models.CharField('Статус', max_length=16, choices=Status.choices, default=Status.IDEA)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='experiments',
        verbose_name='Ответственный',
    )
    outcome_note = models.TextField('Итог / вывод эксперимента', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Гипотеза роста'
        verbose_name_plural = 'Гипотезы роста (ICE)'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title

    @property
    def ice_score(self) -> float:
        return round((self.impact + self.confidence + self.ease) / 3.0, 1)


class DataRoomDoc(models.Model):
    """Structured Investor Data Room document registry."""

    class Category(models.TextChoices):
        PITCH = 'PITCH', 'Питч-дек и презентации'
        FINANCE = 'FINANCE', 'Финмодель и отчётность'
        LEGAL = 'LEGAL', 'Учредительные и устав'
        CONTRACTS = 'CONTRACTS', 'Клиентские контракты'
        IP = 'IP', 'Интеллектуальная собственность'
        TEAM = 'TEAM', 'Команда и ESOP'

    class AccessLevel(models.TextChoices):
        FOUNDERS = 'FOUNDERS', 'Только основатели'
        TEAM = 'TEAM', 'Вся команда'
        INVESTORS = 'INVESTORS', 'Доступно инвесторам'

    class Status(models.TextChoices):
        READY = 'READY', 'Готов к отправке'
        UPDATING = 'UPDATING', 'Обновляется'
        DRAFT = 'DRAFT', 'Черновик'

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='data_room_docs',
        verbose_name='Компания',
    )
    title = models.CharField('Название документа', max_length=200)
    category = models.CharField('Раздел', max_length=16, choices=Category.choices, default=Category.PITCH)
    access_level = models.CharField(
        'Уровень доступа',
        max_length=16,
        choices=AccessLevel.choices,
        default=AccessLevel.INVESTORS,
    )
    status = models.CharField('Статус готовности', max_length=16, choices=Status.choices, default=Status.READY)
    version_label = models.CharField('Версия', max_length=32, default='v1.0')
    doc_url = models.URLField('Ссылка на документ (Drive / Notion / PDF)', blank=True)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='data_room_docs',
        verbose_name='Ответственный',
    )
    summary = models.TextField('Краткое описание', blank=True)
    updated_at = models.DateField('Дата обновления', default=timezone.localdate)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Документ Data Room'
        verbose_name_plural = 'Документы Data Room'
        ordering = ['category', '-updated_at']

    def __str__(self) -> str:
        return f'{self.title} ({self.version_label})'


