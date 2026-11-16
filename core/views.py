"""
Django MVT Controllers (views.py) for VectorStartUp.
Strictly Server-Side Rendered (SSR) via django.shortcuts.render() and PRG redirects.
No JSON APIs, no DRF, no SPA endpoints.
"""

import csv
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    BudgetItemForm,
    CompanyForm,
    EmailLoginForm,
    EmailVerificationForm,
    EmployeeForm,
    ExpenseForm,
    FundingRoundForm,
    InvestmentAllocationForm,
    InvestorForm,
    KPIEntryForm,
    KPIMetricForm,
    RegisterForm,
    TaskCommentForm,
    TaskForm,
)
from .analytics import (
    compute_data_room_readiness,
    compute_deal_metrics,
    compute_founder_alerts,
    compute_invoice_metrics,
)
from .models import (
    ActivityLog,
    BudgetCategory,
    BudgetItem,
    Company,
    CompanyMembership,
    DataRoomDoc,
    Deal,
    EmailVerificationCode,
    Employee,
    Expense,
    FundingRound,
    InvestmentAllocation,
    Investor,
    Invoice,
    KPIMetric,
    RoadmapMilestone,
    Task,
)

User = get_user_model()
RESEND_COOLDOWN_SECONDS = 30


def _send_verification_email(user, verification: EmailVerificationCode) -> None:
    """Send 6-digit account confirmation code via Django EmailBackend (SMTP or console in dev)."""
    ttl = getattr(settings, 'EMAIL_VERIFICATION_TTL_MINUTES', 15)
    greeting = user.first_name or user.email
    subject = 'VectorStartUp - код подтверждения регистрации'
    message = (
        f'Здравствуйте, {greeting}!\n\n'
        f'Ваш код для подтверждения почты в платформе «VectorStartUp»: {verification.code}\n\n'
        f'Код действителен {ttl} минут. После подтверждения вы сможете входить в аккаунт '
        f'по адресу {user.email} и выбранному паролю.\n\n'
        f'Если вы не регистрировались в VectorStartUp, просто проигнорируйте это письмо.'
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _get_active_company(request):
    """Return active Company for authenticated user or None if user has no companies yet."""
    qs = Company.objects.filter(memberships__user=request.user).distinct().order_by('name')
    active_id = request.session.get('active_company_id')
    company = qs.filter(id=active_id).first() if active_id else None
    if company is None:
        company = qs.first()
        if company:
            request.session['active_company_id'] = company.id
    return company


def _log(company, user, action_type: str, summary: str) -> None:
    ActivityLog.objects.create(
        company=company,
        actor=user,
        action_type=action_type,
        summary=summary[:260],
    )


def _build_sparkline_points(values, width=320, height=76, pad=8):
    """Compute SVG polyline coordinates server-side for pure SSR KPI trend charts."""
    if not values:
        return ''
    nums = [float(v) for v in values]
    if len(nums) == 1:
        y = height / 2
        return f'{pad},{y:.1f} {width - pad},{y:.1f}'
    lo, hi = min(nums), max(nums)
    span = (hi - lo) if hi != lo else 1.0
    step_x = (width - pad * 2) / (len(nums) - 1)
    coords = []
    for idx, val in enumerate(nums):
        x = pad + idx * step_x
        y = (height - pad) - ((val - lo) / span) * (height - pad * 2)
        coords.append(f'{x:.1f},{y:.1f}')
    return ' '.join(coords)


# ---------------------------------------------------------------------------
# 1. Authentication (Email Registration, Email Code Verification, Email Login)
# ---------------------------------------------------------------------------


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            candidate = User.objects.filter(email__iexact=email).first()
            if candidate is not None and candidate.check_password(password) and not candidate.is_active:
                request.session['pending_verification_email'] = candidate.email
                latest_code = candidate.verification_codes.filter(is_used=False).first()
                if latest_code is None or not latest_code.is_valid:
                    latest_code = EmailVerificationCode.create_for_user(candidate)
                    _send_verification_email(candidate, latest_code)
                    messages.warning(
                        request,
                        f'Почта {candidate.email} ещё не подтверждена. Мы отправили новый 6-значный код на ваш email.',
                    )
                else:
                    messages.warning(
                        request,
                        f'Почта {candidate.email} ещё не подтверждена. Введите 6-значный код из письма.',
                    )
                return redirect('verify_email')

            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect('dashboard')

            form.add_error(None, 'Неверный email или пароль.')
    else:
        form = EmailLoginForm()

    return render(request, 'auth/login.html', {'form': form, 'next': next_url})


class UserLogoutView(LogoutView):
    next_page = 'login'


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            verification = EmailVerificationCode.create_for_user(user)
            _send_verification_email(user, verification)
            request.session['pending_verification_email'] = user.email
            messages.success(
                request,
                f'Мы отправили 6-значный код подтверждения на {user.email}. Введите его ниже для активации аккаунта.',
            )
            return redirect('verify_email')
    else:
        form = RegisterForm()

    return render(request, 'auth/register.html', {'form': form})


def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    pending_email = request.session.get('pending_verification_email', '')
    ttl_minutes = getattr(settings, 'EMAIL_VERIFICATION_TTL_MINUTES', 15)

    if request.method == 'POST':
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            submitted_code = form.cleaned_data['code']
            request.session['pending_verification_email'] = email
            pending_email = email

            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                form.add_error('email', 'Аккаунт с таким email не найден. Сначала зарегистрируйтесь.')
            elif user.is_active:
                messages.info(request, 'Эта почта уже подтверждена. Войдите по email и паролю.')
                return redirect('login')
            else:
                verification = (
                    EmailVerificationCode.objects.filter(user=user, is_used=False)
                    .order_by('-created_at')
                    .first()
                )
                if verification is None:
                    form.add_error('code', 'Активный код не найден. Запросите повторную отправку письма.')
                elif verification.is_expired:
                    verification.is_used = True
                    verification.save(update_fields=['is_used'])
                    form.add_error('code', 'Срок действия кода истёк. Нажмите «Отправить код повторно».')
                elif verification.attempts >= EmailVerificationCode.MAX_ATTEMPTS:
                    verification.is_used = True
                    verification.save(update_fields=['is_used'])
                    form.add_error('code', 'Превышено число попыток ввода. Запросите новый код.')
                elif not secrets.compare_digest(verification.code, submitted_code):
                    verification.attempts += 1
                    if verification.attempts >= EmailVerificationCode.MAX_ATTEMPTS:
                        verification.is_used = True
                        verification.save(update_fields=['attempts', 'is_used'])
                        form.add_error('code', 'Неверный код. Попытки исчерпаны - запросите новый код.')
                    else:
                        verification.save(update_fields=['attempts'])
                        form.add_error(
                            'code',
                            f'Неверный код подтверждения. Осталось попыток: {verification.remaining_attempts}.',
                        )
                else:
                    verification.is_used = True
                    verification.save(update_fields=['is_used'])
                    user.is_active = True
                    user.save(update_fields=['is_active'])
                    request.session.pop('pending_verification_email', None)
                    login(request, user, backend='core.backends.EmailBackend')
                    messages.success(
                        request,
                        f'Почта {user.email} подтверждена! Добро пожаловать, {user.first_name or user.email}.',
                    )
                    if Company.objects.filter(memberships__user=user).exists():
                        return redirect('dashboard')
                    return redirect('company_create')
    else:
        form = EmailVerificationForm(initial={'email': pending_email})

    return render(
        request,
        'auth/verify_email.html',
        {
            'form': form,
            'pending_email': pending_email,
            'ttl_minutes': ttl_minutes,
        },
    )


@require_POST
def resend_verification_code_view(request):
    email = (request.POST.get('email') or request.session.get('pending_verification_email') or '').strip().lower()
    if not email:
        messages.error(request, 'Укажите email для повторной отправки кода.')
        return redirect('verify_email')

    request.session['pending_verification_email'] = email
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        messages.error(request, 'Аккаунт с таким email не найден. Пройдите регистрацию.')
        return redirect('register')

    if user.is_active:
        messages.info(request, 'Этот аккаунт уже подтверждён. Вы можете войти по email и паролю.')
        return redirect('login')

    latest = EmailVerificationCode.objects.filter(user=user).order_by('-created_at').first()
    if latest is not None:
        elapsed = (timezone.now() - latest.created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed) + 1
            messages.warning(request, f'Повторная отправка возможна через {wait} сек.')
            return redirect('verify_email')

    verification = EmailVerificationCode.create_for_user(user)
    _send_verification_email(user, verification)
    messages.success(request, f'Новый 6-значный код подтверждения отправлен на {user.email}.')
    return redirect('verify_email')


# ---------------------------------------------------------------------------
# 2. Companies (Registration, Switching, Settings, Delete)
# ---------------------------------------------------------------------------


@login_required
def company_list(request):
    companies = (
        Company.objects.filter(memberships__user=request.user)
        .annotate(
            employees_count=Count('employees', distinct=True),
            tasks_count=Count('tasks', distinct=True),
        )
        .distinct()
    )
    return render(request, 'companies/list.html', {'companies': companies})


@login_required
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.created_by = request.user
            company.save()
            CompanyMembership.objects.create(
                company=company,
                user=request.user,
                role=CompanyMembership.Role.FOUNDER,
            )
            request.session['active_company_id'] = company.id
            _log(company, request.user, 'Компания', f'Зарегистрирована компания «{company.name}» ({company.get_stage_display()})')
            messages.success(request, f'Компания «{company.name}» успешно зарегистрирована.')
            return redirect('dashboard')
    else:
        form = CompanyForm()

    return render(
        request,
        'companies/form.html',
        {'form': form, 'page_title': 'Регистрация компании', 'submit_label': 'Создать компанию'},
    )


@login_required
def company_edit(request, pk):
    company = get_object_or_404(Company, pk=pk, memberships__user=request.user)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            _log(company, request.user, 'Компания', f'Обновлены реквизиты компании «{company.name}»')
            messages.success(request, 'Настройки компании сохранены.')
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)

    return render(
        request,
        'companies/form.html',
        {
            'form': form,
            'company_obj': company,
            'page_title': f'Настройки: {company.name}',
            'submit_label': 'Сохранить изменения',
        },
    )


@login_required
@require_POST
def company_switch(request, pk):
    company = get_object_or_404(Company, pk=pk, memberships__user=request.user)
    request.session['active_company_id'] = company.id
    messages.info(request, f'Рабочее пространство переключено на «{company.name}».')
    next_url = request.POST.get('next') or 'dashboard'
    return redirect(next_url)


@login_required
@require_POST
def company_delete(request, pk):
    company = get_object_or_404(
        Company,
        pk=pk,
        memberships__user=request.user,
        memberships__role=CompanyMembership.Role.FOUNDER,
    )
    name = company.name
    company.delete()
    if request.session.get('active_company_id') == pk:
        request.session.pop('active_company_id', None)
    messages.warning(request, f'Компания «{name}» удалена.')
    return redirect('company_list')


# ---------------------------------------------------------------------------
# 3. Executive KPI Dashboard
# ---------------------------------------------------------------------------


@login_required
def dashboard_view(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    today = timezone.localdate()
    thirty_days_ago = today - timedelta(days=30)

    # Financial aggregates
    total_raised = (
        FundingRound.objects.filter(company=company, status=FundingRound.Status.CLOSED)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    pipeline_raised = (
        FundingRound.objects.filter(company=company)
        .exclude(status=FundingRound.Status.CLOSED)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    total_paid_expenses = (
        Expense.objects.filter(company=company, status=Expense.Status.PAID)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    pending_expenses = (
        Expense.objects.filter(company=company, status=Expense.Status.PENDING)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    cash_on_hand = company.initial_cash + total_raised - total_paid_expenses

    # Monthly burn rate: max(last 30d paid+pending expenses, active payroll + recurring expenses)
    last_30d_spend = (
        Expense.objects.filter(company=company, expense_date__gte=thirty_days_ago)
        .exclude(status=Expense.Status.DRAFT)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    monthly_payroll = (
        Employee.objects.filter(company=company)
        .exclude(status=Employee.Status.INACTIVE)
        .aggregate(total=Sum('monthly_salary'))['total']
        or Decimal('0.00')
    )
    monthly_burn = max(last_30d_spend, monthly_payroll)
    runway_months = (
        round(float(cash_on_hand / monthly_burn), 1)
        if monthly_burn > 0 and cash_on_hand > 0
        else (0.0 if cash_on_hand <= 0 else None)
    )

    # Budget utilization by category
    budget_planned_total = (
        BudgetItem.objects.filter(company=company).aggregate(total=Sum('planned_amount'))['total']
        or Decimal('0.00')
    )
    budget_utilization_pct = (
        round(float(total_paid_expenses / budget_planned_total * 100), 1)
        if budget_planned_total > 0
        else 0.0
    )

    budget_rows = []
    for item in BudgetItem.objects.filter(company=company)[:6]:
        spent = (
            item.expenses.exclude(status=Expense.Status.DRAFT).aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        pct = round(float(spent / item.planned_amount * 100), 1) if item.planned_amount > 0 else 0.0
        state = 'risk' if pct > 100 else ('warn' if pct >= 85 else 'good')
        budget_rows.append(
            {
                'item': item,
                'spent': spent,
                'remaining': item.planned_amount - spent,
                'pct': pct,
                'bar_width': min(pct, 100.0),
                'state': state,
            }
        )

    # Investment allocations & Cap Table
    allocations = InvestmentAllocation.objects.filter(company=company).select_related('funding_round')[:6]
    investors_equity = (
        FundingRound.objects.filter(company=company, status=FundingRound.Status.CLOSED)
        .aggregate(total=Sum('equity_percent'))['total']
        or Decimal('0.00')
    )
    esop_equity = (
        Employee.objects.filter(company=company)
        .exclude(status=Employee.Status.INACTIVE)
        .aggregate(total=Sum('equity_options_pct'))['total']
        or Decimal('0.00')
    )
    founders_equity = max(Decimal('0.00'), Decimal('100.00') - investors_equity - esop_equity)

    # Tasks summary
    all_tasks = Task.objects.filter(company=company).select_related('assignee')
    tasks_total = all_tasks.count()
    tasks_done = all_tasks.filter(status=Task.Status.DONE).count()
    tasks_in_progress = all_tasks.filter(status=Task.Status.IN_PROGRESS).count()
    tasks_overdue = all_tasks.exclude(status=Task.Status.DONE).filter(due_date__lt=today).count()
    tasks_completion_pct = round(tasks_done / tasks_total * 100, 1) if tasks_total else 0.0
    urgent_tasks = all_tasks.exclude(status=Task.Status.DONE).order_by('due_date', '-created_at')[:5]

    # Team & KPIs
    active_employees_count = Employee.objects.filter(company=company).exclude(status=Employee.Status.INACTIVE).count()
    all_kpis = list(KPIMetric.objects.filter(company=company).select_related('owner'))
    kpis = all_kpis[:4]
    recent_activities = ActivityLog.objects.filter(company=company).select_related('actor')[:8]

    # Commercial, Receivables, Roadmap, Data Room & Founder Focus Alerts
    all_deals = list(Deal.objects.filter(company=company))
    deal_metrics = compute_deal_metrics(all_deals)
    all_invoices = list(Invoice.objects.filter(company=company))
    invoice_metrics = compute_invoice_metrics(all_invoices, today)
    all_docs = list(DataRoomDoc.objects.filter(company=company))
    data_room_readiness = compute_data_room_readiness(all_docs)
    overdue_tasks_list = list(all_tasks.exclude(status=Task.Status.DONE).filter(due_date__lt=today).order_by('due_date'))
    active_milestones = list(
        RoadmapMilestone.objects.filter(company=company)
        .exclude(status=RoadmapMilestone.Status.COMPLETED)
        .prefetch_related('checklist_items')[:4]
    )

    founder_alerts = compute_founder_alerts(
        company=company,
        runway_months=runway_months,
        budget_rows=budget_rows,
        overdue_tasks=overdue_tasks_list,
        deals=all_deals,
        kpis=all_kpis,
        invoices=all_invoices,
        today=today,
    )

    context = {
        'company': company,
        'cash_on_hand': cash_on_hand,
        'total_raised': total_raised,
        'pipeline_raised': pipeline_raised,
        'total_paid_expenses': total_paid_expenses,
        'pending_expenses': pending_expenses,
        'monthly_burn': monthly_burn,
        'runway_months': runway_months,
        'monthly_payroll': monthly_payroll,
        'active_employees_count': active_employees_count,
        'budget_planned_total': budget_planned_total,
        'budget_utilization_pct': budget_utilization_pct,
        'budget_rows': budget_rows,
        'allocations': allocations,
        'founders_equity': founders_equity,
        'investors_equity': investors_equity,
        'esop_equity': esop_equity,
        'tasks_total': tasks_total,
        'tasks_done': tasks_done,
        'tasks_in_progress': tasks_in_progress,
        'tasks_overdue': tasks_overdue,
        'tasks_completion_pct': tasks_completion_pct,
        'urgent_tasks': urgent_tasks,
        'kpis': kpis,
        'recent_activities': recent_activities,
        'founder_alerts': founder_alerts,
        'deal_metrics': deal_metrics,
        'invoice_metrics': invoice_metrics,
        'data_room_readiness': data_room_readiness,
        'active_milestones': active_milestones,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# 4. Budget Planning (CRUD + Plan/Fact Analysis + Filter & Sort)
# ---------------------------------------------------------------------------


@login_required
def budget_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    period = request.GET.get('period', '').strip()
    sort = request.GET.get('sort', '-planned')

    qs = BudgetItem.objects.filter(company=company)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(notes__icontains=q))
    if category:
        qs = qs.filter(category=category)
    if period:
        qs = qs.filter(period=period)

    rows = []
    total_planned = Decimal('0.00')
    total_spent = Decimal('0.00')
    over_budget_count = 0

    for item in qs:
        spent = (
            item.expenses.exclude(status=Expense.Status.DRAFT).aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        remaining = item.planned_amount - spent
        pct = round(float(spent / item.planned_amount * 100), 1) if item.planned_amount > 0 else 0.0
        state = 'risk' if pct > 100 else ('warn' if pct >= 85 else 'good')
        if pct > 100:
            over_budget_count += 1
        total_planned += item.planned_amount
        total_spent += spent
        rows.append(
            {
                'item': item,
                'spent': spent,
                'remaining': remaining,
                'pct': pct,
                'bar_width': min(pct, 100.0),
                'state': state,
                'status_label': 'Превышен' if state == 'risk' else ('Близко к лимиту' if state == 'warn' else 'В норме'),
            }
        )

    sort_key_map = {
        '-planned': lambda r: -r['item'].planned_amount,
        'planned': lambda r: r['item'].planned_amount,
        '-spent': lambda r: -r['spent'],
        '-pct': lambda r: -r['pct'],
        'name': lambda r: r['item'].name.lower(),
    }
    rows.sort(key=sort_key_map.get(sort, sort_key_map['-planned']))

    periods = list(
        BudgetItem.objects.filter(company=company).values_list('period', flat=True).distinct().order_by('-period')
    )
    overall_pct = round(float(total_spent / total_planned * 100), 1) if total_planned > 0 else 0.0

    return render(
        request,
        'budgets/list.html',
        {
            'rows': rows,
            'total_planned': total_planned,
            'total_spent': total_spent,
            'total_remaining': total_planned - total_spent,
            'overall_pct': overall_pct,
            'over_budget_count': over_budget_count,
            'categories': BudgetCategory.choices,
            'periods': periods,
            'q': q,
            'selected_category': category,
            'selected_period': period,
            'sort': sort,
        },
    )


@login_required
def budget_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = BudgetItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.company = company
            item.save()
            _log(company, request.user, 'Бюджет', f'Добавлена статья бюджета «{item.name}» ({item.period})')
            messages.success(request, f'Статья бюджета «{item.name}» создана.')
            return redirect('budget_list')
    else:
        form = BudgetItemForm()

    return render(
        request,
        'budgets/form.html',
        {'form': form, 'page_title': 'Новая статья бюджета', 'submit_label': 'Сохранить статью'},
    )


@login_required
def budget_edit(request, pk):
    company = _get_active_company(request)
    item = get_object_or_404(BudgetItem, pk=pk, company=company)
    if request.method == 'POST':
        form = BudgetItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            _log(company, request.user, 'Бюджет', f'Изменена статья бюджета «{item.name}»')
            messages.success(request, 'Статья бюджета обновлена.')
            return redirect('budget_list')
    else:
        form = BudgetItemForm(instance=item)

    return render(
        request,
        'budgets/form.html',
        {'form': form, 'page_title': f'Редактирование: {item.name}', 'submit_label': 'Сохранить изменения'},
    )


@login_required
@require_POST
def budget_delete(request, pk):
    company = _get_active_company(request)
    item = get_object_or_404(BudgetItem, pk=pk, company=company)
    name = item.name
    item.delete()
    _log(company, request.user, 'Бюджет', f'Удалена статья бюджета «{name}»')
    messages.warning(request, f'Статья бюджета «{name}» удалена.')
    return redirect('budget_list')


# ---------------------------------------------------------------------------
# 5. Expenses Ledger (CRUD + Filter + Sort + Pagination + CSV Export)
# ---------------------------------------------------------------------------


def _filtered_expenses(request, company):
    qs = Expense.objects.filter(company=company).select_related('budget_item', 'responsible')
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    status = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    sort = request.GET.get('sort', '-expense_date')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(vendor__icontains=q) | Q(notes__icontains=q))
    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(expense_date__gte=date_from)
    if date_to:
        qs = qs.filter(expense_date__lte=date_to)

    allowed_sorts = {'-expense_date', 'expense_date', '-amount', 'amount', 'title'}
    if sort not in allowed_sorts:
        sort = '-expense_date'
    qs = qs.order_by(sort, '-created_at')
    return qs, {
        'q': q,
        'selected_category': category,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
    }


@login_required
def expense_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    qs, filters = _filtered_expenses(request, company)
    filtered_total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    paid_total = qs.filter(status=Expense.Status.PAID).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    pending_total = qs.filter(status=Expense.Status.PENDING).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'expenses/list.html',
        {
            'page_obj': page_obj,
            'filtered_total': filtered_total,
            'paid_total': paid_total,
            'pending_total': pending_total,
            'categories': BudgetCategory.choices,
            'statuses': Expense.Status.choices,
            **filters,
        },
    )


@login_required
def expense_export_csv(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    qs, _ = _filtered_expenses(request, company)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="expenses_{company.id}.csv"'
    response.write('\ufeff')  # UTF-8 BOM for clean Excel Cyrillic display

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Дата', 'Наименование', 'Категория', 'Контрагент', 'Сумма', 'Валюта', 'Статус', 'Ответственный'])
    for exp in qs:
        writer.writerow(
            [
                exp.expense_date.strftime('%Y-%m-%d'),
                exp.title,
                exp.get_category_display(),
                exp.vendor,
                f'{exp.amount:.2f}',
                company.currency,
                exp.get_status_display(),
                exp.responsible.full_name if exp.responsible else '',
            ]
        )
    return response


@login_required
def expense_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, company=company)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.company = company
            expense.created_by = request.user
            expense.save()
            _log(company, request.user, 'Расходы', f'Добавлен расход «{expense.title}» на {expense.amount} {company.currency_symbol}')
            messages.success(request, f'Расход «{expense.title}» записан.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(company=company)

    return render(
        request,
        'expenses/form.html',
        {'form': form, 'page_title': 'Новый расход', 'submit_label': 'Добавить расход'},
    )


@login_required
def expense_edit(request, pk):
    company = _get_active_company(request)
    expense = get_object_or_404(Expense, pk=pk, company=company)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, company=company)
        if form.is_valid():
            form.save()
            _log(company, request.user, 'Расходы', f'Обновлён расход «{expense.title}»')
            messages.success(request, 'Расход обновлён.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, company=company)

    return render(
        request,
        'expenses/form.html',
        {'form': form, 'page_title': f'Редактирование расхода', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def expense_mark_paid(request, pk):
    company = _get_active_company(request)
    expense = get_object_or_404(Expense, pk=pk, company=company)
    expense.status = Expense.Status.PAID
    expense.save(update_fields=['status'])
    _log(company, request.user, 'Расходы', f'Оплачен расход «{expense.title}» ({expense.amount} {company.currency_symbol})')
    messages.success(request, f'Расход «{expense.title}» отмечен как оплаченный.')
    return redirect('expense_list')


@login_required
@require_POST
def expense_delete(request, pk):
    company = _get_active_company(request)
    expense = get_object_or_404(Expense, pk=pk, company=company)
    title = expense.title
    expense.delete()
    _log(company, request.user, 'Расходы', f'Удалён расход «{title}»')
    messages.warning(request, f'Расход «{title}» удалён.')
    return redirect('expense_list')


# ---------------------------------------------------------------------------
# 6. Ventures, Funding Rounds & Investment Allocations
# ---------------------------------------------------------------------------


@login_required
def ventures_overview(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    q = request.GET.get('q', '').strip()
    inv_type = request.GET.get('investor_type', '').strip()

    rounds = FundingRound.objects.filter(company=company).select_related('investor').prefetch_related('allocations')
    investors = Investor.objects.filter(company=company)
    if q:
        investors = investors.filter(Q(name__icontains=q) | Q(contact_name__icontains=q))
    if inv_type:
        investors = investors.filter(investor_type=inv_type)

    allocations = InvestmentAllocation.objects.filter(company=company).select_related('funding_round')

    total_closed = rounds.filter(status=FundingRound.Status.CLOSED).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_pipeline = rounds.exclude(status=FundingRound.Status.CLOSED).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0.00')
    total_alloc_spent = allocations.aggregate(total=Sum('spent_amount'))['total'] or Decimal('0.00')

    investors_equity = rounds.filter(status=FundingRound.Status.CLOSED).aggregate(total=Sum('equity_percent'))['total'] or Decimal('0.00')
    esop_equity = (
        Employee.objects.filter(company=company)
        .exclude(status=Employee.Status.INACTIVE)
        .aggregate(total=Sum('equity_options_pct'))['total']
        or Decimal('0.00')
    )
    founders_equity = max(Decimal('0.00'), Decimal('100.00') - investors_equity - esop_equity)

    return render(
        request,
        'ventures/overview.html',
        {
            'rounds': rounds,
            'investors': investors,
            'allocations': allocations,
            'total_closed': total_closed,
            'total_pipeline': total_pipeline,
            'total_allocated': total_allocated,
            'total_alloc_spent': total_alloc_spent,
            'founders_equity': founders_equity,
            'investors_equity': investors_equity,
            'esop_equity': esop_equity,
            'investor_types': Investor.InvestorType.choices,
            'q': q,
            'selected_investor_type': inv_type,
        },
    )


@login_required
def investor_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = InvestorForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.company = company
            inv.save()
            _log(company, request.user, 'Инвестиции', f'Добавлен инвестор «{inv.name}»')
            messages.success(request, f'Инвестор «{inv.name}» добавлен.')
            return redirect('ventures_overview')
    else:
        form = InvestorForm()

    return render(
        request,
        'ventures/form.html',
        {'form': form, 'page_title': 'Новый инвестор / фонд', 'submit_label': 'Добавить инвестора'},
    )


@login_required
def investor_edit(request, pk):
    company = _get_active_company(request)
    inv = get_object_or_404(Investor, pk=pk, company=company)
    if request.method == 'POST':
        form = InvestorForm(request.POST, instance=inv)
        if form.is_valid():
            form.save()
            messages.success(request, 'Карточка инвестора обновлена.')
            return redirect('ventures_overview')
    else:
        form = InvestorForm(instance=inv)

    return render(
        request,
        'ventures/form.html',
        {'form': form, 'page_title': f'Инвестор: {inv.name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def investor_delete(request, pk):
    company = _get_active_company(request)
    inv = get_object_or_404(Investor, pk=pk, company=company)
    name = inv.name
    inv.delete()
    messages.warning(request, f'Инвестор «{name}» удалён.')
    return redirect('ventures_overview')


@login_required
def round_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = FundingRoundForm(request.POST, company=company)
        if form.is_valid():
            fr = form.save(commit=False)
            fr.company = company
            fr.save()
            _log(company, request.user, 'Инвестиции', f'Создан раунд «{fr.round_name}» ({fr.amount} {company.currency_symbol})')
            messages.success(request, f'Инвестиционный раунд «{fr.round_name}» добавлен.')
            return redirect('ventures_overview')
    else:
        form = FundingRoundForm(company=company)

    return render(
        request,
        'ventures/form.html',
        {'form': form, 'page_title': 'Новый инвестиционный раунд', 'submit_label': 'Создать раунд'},
    )


@login_required
def round_edit(request, pk):
    company = _get_active_company(request)
    fr = get_object_or_404(FundingRound, pk=pk, company=company)
    if request.method == 'POST':
        form = FundingRoundForm(request.POST, instance=fr, company=company)
        if form.is_valid():
            form.save()
            _log(company, request.user, 'Инвестиции', f'Обновлён раунд «{fr.round_name}» ({fr.get_status_display()})')
            messages.success(request, 'Раунд обновлён.')
            return redirect('ventures_overview')
    else:
        form = FundingRoundForm(instance=fr, company=company)

    return render(
        request,
        'ventures/form.html',
        {'form': form, 'page_title': f'Раунд: {fr.round_name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def round_delete(request, pk):
    company = _get_active_company(request)
    fr = get_object_or_404(FundingRound, pk=pk, company=company)
    name = fr.round_name
    fr.delete()
    messages.warning(request, f'Раунд «{name}» удалён.')
    return redirect('ventures_overview')


@login_required
def allocation_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = InvestmentAllocationForm(request.POST, company=company)
        if form.is_valid():
            alloc = form.save(commit=False)
            alloc.company = company
            alloc.save()
            _log(company, request.user, 'Инвестиции', f'Запланировано распределение «{alloc.bucket_name}»')
            messages.success(request, f'Направление «{alloc.bucket_name}» добавлено.')
            return redirect('ventures_overview')
    else:
        form = InvestmentAllocationForm(company=company)

    return render(
        request,
        'ventures/form.html',
        {'form': form, 'page_title': 'Распределение инвестиций', 'submit_label': 'Добавить направление'},
    )


@login_required
def allocation_edit(request, pk):
    company = _get_active_company(request)
    alloc = get_object_or_404(InvestmentAllocation, pk=pk, company=company)
    if request.method == 'POST':
        form = InvestmentAllocationForm(request.POST, instance=alloc, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Распределение обновлено.')
            return redirect('ventures_overview')
    else:
        form = InvestmentAllocationForm(instance=alloc, company=company)

    return render(
        request,
        'ventures/form.html',
        {'form': form, 'page_title': f'Распределение: {alloc.bucket_name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def allocation_delete(request, pk):
    company = _get_active_company(request)
    alloc = get_object_or_404(InvestmentAllocation, pk=pk, company=company)
    alloc.delete()
    messages.warning(request, 'Статья распределения удалена.')
    return redirect('ventures_overview')


# ---------------------------------------------------------------------------
# 7. Team & Employees (CRUD + Payroll Breakdown + Detail)
# ---------------------------------------------------------------------------


@login_required
def employee_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    q = request.GET.get('q', '').strip()
    department = request.GET.get('department', '').strip()
    status = request.GET.get('status', '').strip()
    sort = request.GET.get('sort', 'full_name')

    qs = Employee.objects.filter(company=company).annotate(
        open_tasks_count=Count('tasks', filter=~Q(tasks__status=Task.Status.DONE))
    )
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(position__icontains=q) | Q(email__icontains=q))
    if department:
        qs = qs.filter(department=department)
    if status:
        qs = qs.filter(status=status)

    allowed_sorts = {'full_name', '-monthly_salary', 'monthly_salary', '-hired_at', 'hired_at'}
    if sort not in allowed_sorts:
        sort = 'full_name'
    qs = qs.order_by(sort)

    active_qs = Employee.objects.filter(company=company).exclude(status=Employee.Status.INACTIVE)
    total_payroll = active_qs.aggregate(total=Sum('monthly_salary'))['total'] or Decimal('0.00')
    total_esop = active_qs.aggregate(total=Sum('equity_options_pct'))['total'] or Decimal('0.00')
    dept_summary = (
        active_qs.values('department')
        .annotate(headcount=Count('id'), payroll=Sum('monthly_salary'))
        .order_by('-payroll')
    )
    dept_labels = dict(Employee.Department.choices)
    for row in dept_summary:
        row['label'] = dept_labels.get(row['department'], row['department'])

    return render(
        request,
        'employees/list.html',
        {
            'employees': qs,
            'total_payroll': total_payroll,
            'total_esop': total_esop,
            'active_count': active_qs.count(),
            'dept_summary': dept_summary,
            'departments': Employee.Department.choices,
            'statuses': Employee.Status.choices,
            'q': q,
            'selected_department': department,
            'selected_status': status,
            'sort': sort,
        },
    )


@login_required
def employee_detail(request, pk):
    company = _get_active_company(request)
    employee = get_object_or_404(Employee, pk=pk, company=company)
    tasks = employee.tasks.all()[:10]
    expenses = employee.expenses.all()[:10]
    return render(
        request,
        'employees/detail.html',
        {'employee': employee, 'tasks': tasks, 'expenses': expenses},
    )


@login_required
def employee_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = company
            emp.save()
            _log(company, request.user, 'Команда', f'Добавлен сотрудник {emp.full_name} ({emp.position})')
            messages.success(request, f'Сотрудник {emp.full_name} добавлен в команду.')
            return redirect('employee_list')
    else:
        form = EmployeeForm()

    return render(
        request,
        'employees/form.html',
        {'form': form, 'page_title': 'Новый сотрудник', 'submit_label': 'Добавить сотрудника'},
    )


@login_required
def employee_edit(request, pk):
    company = _get_active_company(request)
    emp = get_object_or_404(Employee, pk=pk, company=company)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные сотрудника сохранены.')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=emp)

    return render(
        request,
        'employees/form.html',
        {'form': form, 'page_title': f'Сотрудник: {emp.full_name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def employee_delete(request, pk):
    company = _get_active_company(request)
    emp = get_object_or_404(Employee, pk=pk, company=company)
    name = emp.full_name
    emp.delete()
    _log(company, request.user, 'Команда', f'Удалён сотрудник {name}')
    messages.warning(request, f'Сотрудник {name} удалён.')
    return redirect('employee_list')


# ---------------------------------------------------------------------------
# 8. Team Tasks (Kanban & List Views + Instant POST Transition + Comments)
# ---------------------------------------------------------------------------


@login_required
def task_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    view_mode = request.GET.get('view', 'board')
    q = request.GET.get('q', '').strip()
    priority = request.GET.get('priority', '').strip()
    status = request.GET.get('status', '').strip()
    assignee_id = request.GET.get('assignee', '').strip()
    overdue_only = request.GET.get('overdue', '') == '1'

    qs = Task.objects.filter(company=company).select_related('assignee')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(milestone__icontains=q) | Q(description__icontains=q))
    if priority:
        qs = qs.filter(priority=priority)
    if status:
        qs = qs.filter(status=status)
    if assignee_id:
        qs = qs.filter(assignee_id=assignee_id)
    if overdue_only:
        qs = qs.exclude(status=Task.Status.DONE).filter(due_date__lt=timezone.localdate())

    tasks_all = list(qs)
    columns = []
    for code, label in Task.Status.choices:
        col_tasks = [t for t in tasks_all if t.status == code]
        columns.append({'code': code, 'label': label, 'tasks': col_tasks, 'count': len(col_tasks)})

    employees = Employee.objects.filter(company=company).exclude(status=Employee.Status.INACTIVE)

    return render(
        request,
        'tasks/list.html',
        {
            'view_mode': view_mode,
            'tasks': tasks_all,
            'columns': columns,
            'employees': employees,
            'priorities': Task.Priority.choices,
            'statuses': Task.Status.choices,
            'q': q,
            'selected_priority': priority,
            'selected_status': status,
            'selected_assignee': assignee_id,
            'overdue_only': overdue_only,
        },
    )


@login_required
def task_detail(request, pk):
    company = _get_active_company(request)
    task = get_object_or_404(Task.objects.select_related('assignee', 'created_by'), pk=pk, company=company)
    if request.method == 'POST':
        comment_form = TaskCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            messages.success(request, 'Комментарий добавлен.')
            return redirect('task_detail', pk=task.pk)
    else:
        comment_form = TaskCommentForm()

    comments = task.comments.select_related('author').all()
    return render(
        request,
        'tasks/detail.html',
        {
            'task': task,
            'comments': comments,
            'comment_form': comment_form,
            'statuses': Task.Status.choices,
        },
    )


@login_required
def task_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = TaskForm(request.POST, company=company)
        if form.is_valid():
            task = form.save(commit=False)
            task.company = company
            task.created_by = request.user
            task.save()
            _log(company, request.user, 'Задачи', f'Создана задача «{task.title}»')
            messages.success(request, f'Задача «{task.title}» создана.')
            return redirect('task_list')
    else:
        initial = {}
        if request.GET.get('status') in dict(Task.Status.choices):
            initial['status'] = request.GET.get('status')
        form = TaskForm(company=company, initial=initial)

    return render(
        request,
        'tasks/form.html',
        {'form': form, 'page_title': 'Новая задача', 'submit_label': 'Создать задачу'},
    )


@login_required
def task_edit(request, pk):
    company = _get_active_company(request)
    task = get_object_or_404(Task, pk=pk, company=company)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача обновлена.')
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task, company=company)

    return render(
        request,
        'tasks/form.html',
        {'form': form, 'page_title': f'Редактирование задачи', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def task_change_status(request, pk):
    company = _get_active_company(request)
    task = get_object_or_404(Task, pk=pk, company=company)
    new_status = request.POST.get('status', '')
    if new_status in dict(Task.Status.choices):
        task.status = new_status
        task.save(update_fields=['status', 'updated_at'])
        _log(company, request.user, 'Задачи', f'Задача «{task.title}» → {task.get_status_display()}')
        messages.success(request, f'Статус задачи обновлён: {task.get_status_display()}.')
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('task_list')


@login_required
@require_POST
def task_delete(request, pk):
    company = _get_active_company(request)
    task = get_object_or_404(Task, pk=pk, company=company)
    title = task.title
    task.delete()
    _log(company, request.user, 'Задачи', f'Удалена задача «{title}»')
    messages.warning(request, f'Задача «{title}» удалена.')
    return redirect('task_list')


# ---------------------------------------------------------------------------
# 9. KPI Tracker (CRUD + Historical Check-Ins + Server-Side SVG Sparklines)
# ---------------------------------------------------------------------------


@login_required
def kpi_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    category = request.GET.get('category', '').strip()
    qs = KPIMetric.objects.filter(company=company).select_related('owner').prefetch_related('entries')
    if category:
        qs = qs.filter(category=category)

    kpi_cards = []
    for metric in qs:
        entry_vals = [e.value for e in metric.entries.all()]
        if not entry_vals:
            entry_vals = [metric.current_value]
        kpi_cards.append(
            {
                'metric': metric,
                'sparkline_points': _build_sparkline_points(entry_vals, width=260, height=52, pad=6),
                'entries_count': len(entry_vals),
            }
        )

    return render(
        request,
        'kpis/list.html',
        {
            'kpi_cards': kpi_cards,
            'categories': KPIMetric.Category.choices,
            'selected_category': category,
        },
    )


@login_required
def kpi_detail(request, pk):
    company = _get_active_company(request)
    metric = get_object_or_404(KPIMetric.objects.select_related('owner'), pk=pk, company=company)

    if request.method == 'POST':
        entry_form = KPIEntryForm(request.POST)
        if entry_form.is_valid():
            entry = entry_form.save(commit=False)
            entry.metric = metric
            entry.created_by = request.user
            entry.save()
            metric.current_value = entry.value
            metric.save(update_fields=['current_value', 'updated_at'])
            _log(company, request.user, 'KPI', f'Зафиксирован замер «{metric.name}»: {entry.value} {metric.unit}')
            messages.success(request, 'Новый замер KPI записан.')
            return redirect('kpi_detail', pk=metric.pk)
    else:
        entry_form = KPIEntryForm()

    entries = list(metric.entries.all())
    sparkline_points = _build_sparkline_points([e.value for e in entries], width=560, height=130, pad=14)

    return render(
        request,
        'kpis/detail.html',
        {
            'metric': metric,
            'entries': list(reversed(entries)),
            'entry_form': entry_form,
            'sparkline_points': sparkline_points,
        },
    )


@login_required
def kpi_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = KPIMetricForm(request.POST, company=company)
        if form.is_valid():
            metric = form.save(commit=False)
            metric.company = company
            metric.save()
            _log(company, request.user, 'KPI', f'Добавлена KPI-метрика «{metric.name}»')
            messages.success(request, f'KPI-метрика «{metric.name}» создана.')
            return redirect('kpi_list')
    else:
        form = KPIMetricForm(company=company)

    return render(
        request,
        'kpis/form.html',
        {'form': form, 'page_title': 'Новая KPI-метрика', 'submit_label': 'Создать метрику'},
    )


@login_required
def kpi_edit(request, pk):
    company = _get_active_company(request)
    metric = get_object_or_404(KPIMetric, pk=pk, company=company)
    if request.method == 'POST':
        form = KPIMetricForm(request.POST, instance=metric, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Метрика обновлена.')
            return redirect('kpi_detail', pk=metric.pk)
    else:
        form = KPIMetricForm(instance=metric, company=company)

    return render(
        request,
        'kpis/form.html',
        {'form': form, 'page_title': f'KPI: {metric.name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def kpi_delete(request, pk):
    company = _get_active_company(request)
    metric = get_object_or_404(KPIMetric, pk=pk, company=company)
    name = metric.name
    metric.delete()
    messages.warning(request, f'Метрика «{name}» удалена.')
    return redirect('kpi_list')
