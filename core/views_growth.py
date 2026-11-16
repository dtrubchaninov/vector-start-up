"""
Django MVT Controllers (views_growth.py) for VectorStartUp.
Covers: Runway & Unit Economics Simulator, B2B Sales CRM Pipeline,
Invoices & Receivables, Quarterly Roadmap, Cap Table & Dilution Simulator,
Growth Experiments (ICE), Investor Data Room, Investor Update Reports, and Global Search.
100% Server-Side Rendered (HTML5 + CSS3, zero JavaScript required).
"""

from __future__ import annotations

import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .analytics import (
    build_investor_update_report,
    build_invoice_text_document,
    build_runway_svg_chart,
    compute_data_room_readiness,
    compute_deal_metrics,
    compute_invoice_metrics,
    compute_unit_economics,
    compute_vesting_progress,
    simulate_round_dilution,
    simulate_runway_projection,
)
from .forms import (
    DataRoomDocForm,
    DealForm,
    EquityHolderForm,
    GrowthExperimentForm,
    InvoiceForm,
    RoadmapMilestoneForm,
    UnitEconomicsForm,
)
from .models import (
    ActivityLog,
    BudgetItem,
    Company,
    DataRoomDoc,
    Deal,
    Employee,
    EquityHolder,
    Expense,
    FundingRound,
    GrowthExperiment,
    Invoice,
    KPIMetric,
    MilestoneCheckItem,
    RoadmapMilestone,
    Task,
    UnitEconomicsProfile,
)


def _get_active_company(request):
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


def _company_cash_and_burn(company):
    today = timezone.localdate()
    thirty_days_ago = today - timedelta(days=30)
    total_raised = (
        FundingRound.objects.filter(company=company, status=FundingRound.Status.CLOSED)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    total_paid_expenses = (
        Expense.objects.filter(company=company, status=Expense.Status.PAID)
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )
    cash_on_hand = company.initial_cash + total_raised - total_paid_expenses
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
    return cash_on_hand, monthly_burn, runway_months, total_raised


def _float_param(request, key: str, default: float, lo: float | None = None, hi: float | None = None) -> float:
    raw = request.GET.get(key)
    if raw is None or raw == '':
        return default
    try:
        val = float(raw.replace(',', '.'))
    except ValueError:
        return default
    if lo is not None:
        val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


def _int_param(request, key: str, default: int, lo: int | None = None, hi: int | None = None) -> int:
    raw = request.GET.get(key)
    if raw is None or raw == '':
        return default
    try:
        val = int(float(raw))
    except ValueError:
        return default
    if lo is not None:
        val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


# ---------------------------------------------------------------------------
# 1. Finance Simulator (18-Month Runway) & SaaS Unit Economics
# ---------------------------------------------------------------------------


@login_required
def finance_simulator_view(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    profile, _ = UnitEconomicsProfile.objects.get_or_create(company=company)
    if request.method == 'POST':
        ue_form = UnitEconomicsForm(request.POST, instance=profile)
        if ue_form.is_valid():
            ue_form.save()
            _log(company, request.user, 'Финмодель', 'Обновлены параметры Unit-экономики SaaS')
            messages.success(request, 'Параметры юнит-экономики обновлены.')
            return redirect('finance_simulator')
    else:
        ue_form = UnitEconomicsForm(instance=profile)

    cash_on_hand, monthly_burn, _, _ = _company_cash_and_burn(company)
    ue_metrics = compute_unit_economics(
        arpu=float(profile.arpu),
        gross_margin_pct=float(profile.gross_margin_pct),
        monthly_churn_pct=float(profile.monthly_churn_pct),
        cac=float(profile.cac),
        active_customers=profile.active_customers,
        monthly_growth_pct=float(profile.monthly_growth_pct),
        monthly_burn=float(monthly_burn),
    )

    # Preset scenarios for instant 1-click simulation (pure GET links, zero JS)
    preset = request.GET.get('preset', '')
    defaults = {
        'growth': float(profile.monthly_growth_pct),
        'hires': 2,
        'hire_cost': 230_000,
        'hire_month': 3,
        'marketing': 0,
        'funding': 0,
        'funding_month': 6,
        'months': 18,
    }
    if preset == 'growth':
        defaults.update({'growth': 18.0, 'hires': 4, 'hire_month': 2, 'marketing': 20, 'funding': 20_000_000, 'funding_month': 4})
    elif preset == 'lean':
        defaults.update({'growth': 8.0, 'hires': 0, 'marketing': -25, 'funding': 0})
    elif preset == 'round':
        defaults.update({'growth': 14.0, 'hires': 3, 'hire_month': 4, 'marketing': 10, 'funding': 30_000_000, 'funding_month': 5})

    sim_params = {
        'growth': _float_param(request, 'growth', defaults['growth'], -30.0, 100.0),
        'hires': _int_param(request, 'hires', defaults['hires'], 0, 50),
        'hire_cost': _int_param(request, 'hire_cost', defaults['hire_cost'], 0, 5_000_000),
        'hire_month': _int_param(request, 'hire_month', defaults['hire_month'], 1, 24),
        'marketing': _int_param(request, 'marketing', defaults['marketing'], -70, 200),
        'funding': _int_param(request, 'funding', defaults['funding'], 0, 1_000_000_000),
        'funding_month': _int_param(request, 'funding_month', defaults['funding_month'], 1, 24),
        'months': _int_param(request, 'months', defaults['months'], 6, 36),
    }

    sim_result = simulate_runway_projection(
        starting_cash=float(max(Decimal('0.00'), cash_on_hand)),
        current_monthly_revenue=float(ue_metrics['mrr']),
        current_monthly_burn=float(monthly_burn),
        monthly_revenue_growth_pct=sim_params['growth'],
        planned_hires=sim_params['hires'],
        avg_hire_monthly_cost=float(sim_params['hire_cost']),
        hire_start_month=sim_params['hire_month'],
        marketing_delta_pct=float(sim_params['marketing']),
        funding_amount=float(sim_params['funding']),
        funding_month=sim_params['funding_month'],
        months=sim_params['months'],
    )
    chart = build_runway_svg_chart(sim_result.points, company.currency_symbol)

    return render(
        request,
        'simulator/index.html',
        {
            'company': company,
            'cash_on_hand': cash_on_hand,
            'monthly_burn': monthly_burn,
            'ue_form': ue_form,
            'ue_metrics': ue_metrics,
            'sim_params': sim_params,
            'sim_result': sim_result,
            'chart': chart,
            'active_preset': preset,
        },
    )


# ---------------------------------------------------------------------------
# 2. B2B Sales CRM Pipeline
# ---------------------------------------------------------------------------


@login_required
def sales_pipeline_view(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    deals = Deal.objects.filter(company=company).select_related('owner')
    metrics = compute_deal_metrics(deals)

    view_mode = request.GET.get('view', 'board')
    q = request.GET.get('q', '').strip()
    stage_filter = request.GET.get('stage', '').strip()

    filtered = deals
    if q:
        filtered = filtered.filter(
            Q(client_name__icontains=q) | Q(contact_name__icontains=q) | Q(notes__icontains=q)
        )
    if stage_filter:
        filtered = filtered.filter(stage=stage_filter)

    columns = []
    for code, label in Deal.Stage.choices:
        col_deals = [d for d in filtered if d.stage == code]
        columns.append(
            {
                'code': code,
                'label': label,
                'deals': col_deals,
                'total_amount': sum(d.amount for d in col_deals),
            }
        )

    return render(
        request,
        'sales/list.html',
        {
            'company': company,
            'deals': filtered,
            'columns': columns,
            'metrics': metrics,
            'view_mode': view_mode,
            'q': q,
            'stage_filter': stage_filter,
            'stage_choices': Deal.Stage.choices,
        },
    )


@login_required
def deal_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = DealForm(request.POST, company=company)
        if form.is_valid():
            deal = form.save(commit=False)
            deal.company = company
            deal.save()
            _log(company, request.user, 'Продажи', f'Добавлена сделка «{deal.client_name}» ({deal.amount} {company.currency_symbol})')
            messages.success(request, f'Сделка «{deal.client_name}» добавлена в воронку.')
            return redirect('sales_pipeline')
    else:
        form = DealForm(company=company)

    return render(
        request,
        'sales/form.html',
        {'form': form, 'page_title': 'Новая B2B-сделка', 'submit_label': 'Добавить в воронку'},
    )


@login_required
def deal_edit(request, pk):
    company = _get_active_company(request)
    deal = get_object_or_404(Deal, pk=pk, company=company)
    if request.method == 'POST':
        form = DealForm(request.POST, instance=deal, company=company)
        if form.is_valid():
            form.save()
            _log(company, request.user, 'Продажи', f'Обновлена сделка «{deal.client_name}» ({deal.get_stage_display()})')
            messages.success(request, 'Сделка обновлена.')
            return redirect('sales_pipeline')
    else:
        form = DealForm(instance=deal, company=company)

    return render(
        request,
        'sales/form.html',
        {'form': form, 'page_title': f'Сделка: {deal.client_name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def deal_change_stage(request, pk):
    company = _get_active_company(request)
    deal = get_object_or_404(Deal, pk=pk, company=company)
    new_stage = request.POST.get('stage')
    if new_stage in dict(Deal.Stage.choices):
        deal.stage = new_stage
        deal.probability = Deal.STAGE_DEFAULT_PROBABILITY.get(new_stage, deal.probability)
        deal.save(update_fields=['stage', 'probability', 'updated_at'])
        _log(company, request.user, 'Продажи', f'Сделка «{deal.client_name}» переведена в «{deal.get_stage_display()}»')
        messages.success(request, f'Этап сделки «{deal.client_name}» → {deal.get_stage_display()}.')
    return redirect(request.POST.get('next') or 'sales_pipeline')


@login_required
@require_POST
def deal_delete(request, pk):
    company = _get_active_company(request)
    deal = get_object_or_404(Deal, pk=pk, company=company)
    name = deal.client_name
    deal.delete()
    messages.warning(request, f'Сделка «{name}» удалена.')
    return redirect('sales_pipeline')


@login_required
def deal_export_csv(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')
    deals = Deal.objects.filter(company=company).select_related('owner')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="sales_{company.id}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Клиент', 'Контакт', 'Email', 'Сумма', 'Тип оплаты', 'Этап', 'Вероятность %', 'Плановая дата', 'Ответственный'])
    for d in deals:
        writer.writerow([
            d.client_name,
            d.contact_name,
            d.contact_email,
            d.amount,
            d.get_billing_type_display(),
            d.get_stage_display(),
            d.probability,
            d.expected_close_date.strftime('%Y-%m-%d') if d.expected_close_date else '',
            d.owner.full_name if d.owner else '',
        ])
    return response


# ---------------------------------------------------------------------------
# 3. Invoices & Accounts Receivable
# ---------------------------------------------------------------------------


@login_required
def invoice_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    invoices = Invoice.objects.filter(company=company)
    metrics = compute_invoice_metrics(invoices, timezone.localdate())

    status_filter = request.GET.get('status', '').strip()
    q = request.GET.get('q', '').strip()
    filtered = invoices
    if status_filter == 'OVERDUE':
        filtered = filtered.filter(status=Invoice.Status.SENT, due_date__lt=timezone.localdate())
    elif status_filter:
        filtered = filtered.filter(status=status_filter)
    if q:
        filtered = filtered.filter(
            Q(invoice_number__icontains=q) | Q(client_name__icontains=q) | Q(service_title__icontains=q)
        )

    return render(
        request,
        'invoices/list.html',
        {
            'company': company,
            'invoices': filtered,
            'metrics': metrics,
            'status_filter': status_filter,
            'q': q,
        },
    )


@login_required
def invoice_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    today = timezone.localdate()
    next_num = f'INV-{today.year}-{Invoice.objects.filter(company=company).count() + 1:03d}'
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.company = company
            if inv.status == Invoice.Status.PAID and not inv.paid_date:
                inv.paid_date = today
            inv.save()
            _log(company, request.user, 'Счета', f'Выставлен счёт № {inv.invoice_number} клиенту «{inv.client_name}» на {inv.amount} {company.currency_symbol}')
            messages.success(request, f'Счёт № {inv.invoice_number} создан.')
            return redirect('invoice_list')
    else:
        form = InvoiceForm(
            initial={
                'invoice_number': next_num,
                'issue_date': today,
                'due_date': today + timedelta(days=10),
                'status': Invoice.Status.SENT,
            }
        )

    return render(
        request,
        'invoices/form.html',
        {'form': form, 'page_title': 'Выставить счёт клиенту', 'submit_label': 'Создать счёт'},
    )


@login_required
def invoice_edit(request, pk):
    company = _get_active_company(request)
    inv = get_object_or_404(Invoice, pk=pk, company=company)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=inv)
        if form.is_valid():
            saved = form.save(commit=False)
            if saved.status == Invoice.Status.PAID and not saved.paid_date:
                saved.paid_date = timezone.localdate()
            saved.save()
            messages.success(request, f'Счёт № {saved.invoice_number} обновлён.')
            return redirect('invoice_list')
    else:
        form = InvoiceForm(instance=inv)

    return render(
        request,
        'invoices/form.html',
        {'form': form, 'page_title': f'Счёт № {inv.invoice_number}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def invoice_mark_paid(request, pk):
    company = _get_active_company(request)
    inv = get_object_or_404(Invoice, pk=pk, company=company)
    inv.status = Invoice.Status.PAID
    inv.paid_date = timezone.localdate()
    inv.save(update_fields=['status', 'paid_date'])
    _log(company, request.user, 'Счета', f'Оплачен счёт № {inv.invoice_number} ({inv.client_name}) на {inv.amount} {company.currency_symbol}')
    messages.success(request, f'Счёт № {inv.invoice_number} отмечен как оплаченный.')
    return redirect('invoice_list')


@login_required
def invoice_download_doc(request, pk):
    company = _get_active_company(request)
    inv = get_object_or_404(Invoice, pk=pk, company=company)
    content = build_invoice_text_document(company, inv)
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="invoice_{inv.invoice_number}.txt"'
    return response


@login_required
def invoice_export_csv(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')
    invoices = Invoice.objects.filter(company=company)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="invoices_{company.id}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Номер', 'Клиент', 'Услуга', 'Сумма', 'НДС 20%', 'Выставлен', 'Срок оплаты', 'Оплачен', 'Статус'])
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.client_name,
            inv.service_title,
            inv.amount,
            'Да' if inv.vat_included else 'Нет',
            inv.issue_date.strftime('%Y-%m-%d'),
            inv.due_date.strftime('%Y-%m-%d'),
            inv.paid_date.strftime('%Y-%m-%d') if inv.paid_date else '',
            inv.get_status_display(),
        ])
    return response


@login_required
@require_POST
def invoice_delete(request, pk):
    company = _get_active_company(request)
    inv = get_object_or_404(Invoice, pk=pk, company=company)
    num = inv.invoice_number
    inv.delete()
    messages.warning(request, f'Счёт № {num} удалён.')
    return redirect('invoice_list')


# ---------------------------------------------------------------------------
# 4. Quarterly Company Roadmap & Checklists
# ---------------------------------------------------------------------------


@login_required
def roadmap_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    milestones = (
        RoadmapMilestone.objects.filter(company=company)
        .select_related('owner')
        .prefetch_related('checklist_items')
    )
    quarter_filter = request.GET.get('quarter', '').strip()
    status_filter = request.GET.get('status', '').strip()
    quarters = sorted({m.quarter for m in milestones})

    filtered = list(milestones)
    if quarter_filter:
        filtered = [m for m in filtered if m.quarter == quarter_filter]
    if status_filter:
        filtered = [m for m in filtered if m.status == status_filter]

    grouped = []
    for q_label in sorted({m.quarter for m in filtered}):
        grouped.append({'quarter': q_label, 'items': [m for m in filtered if m.quarter == q_label]})

    completed_count = sum(1 for m in milestones if m.status == RoadmapMilestone.Status.COMPLETED)
    at_risk_count = sum(1 for m in milestones if m.status == RoadmapMilestone.Status.AT_RISK)
    avg_progress = (
        round(sum(m.progress_percent for m in milestones) / len(milestones))
        if milestones
        else 0
    )

    return render(
        request,
        'roadmap/list.html',
        {
            'company': company,
            'grouped': grouped,
            'quarters': quarters,
            'quarter_filter': quarter_filter,
            'status_filter': status_filter,
            'status_choices': RoadmapMilestone.Status.choices,
            'total_count': len(milestones),
            'completed_count': completed_count,
            'at_risk_count': at_risk_count,
            'avg_progress': avg_progress,
        },
    )


@login_required
def milestone_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = RoadmapMilestoneForm(request.POST, company=company)
        if form.is_valid():
            ms = form.save(commit=False)
            ms.company = company
            ms.save()
            raw_items = form.cleaned_data.get('initial_checklist', '')
            for line in raw_items.splitlines():
                title = line.strip()
                if title:
                    MilestoneCheckItem.objects.create(milestone=ms, title=title[:220])
            _log(company, request.user, 'Дорожная карта', f'Добавлена веха «{ms.title}» ({ms.quarter})')
            messages.success(request, f'Веха «{ms.title}» добавлена в дорожную карту.')
            return redirect('roadmap_list')
    else:
        form = RoadmapMilestoneForm(company=company)

    return render(
        request,
        'roadmap/form.html',
        {'form': form, 'page_title': 'Новая веха дорожной карты', 'submit_label': 'Добавить веху'},
    )


@login_required
def milestone_edit(request, pk):
    company = _get_active_company(request)
    ms = get_object_or_404(RoadmapMilestone, pk=pk, company=company)
    if request.method == 'POST':
        form = RoadmapMilestoneForm(request.POST, instance=ms, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Веха обновлена.')
            return redirect('roadmap_list')
    else:
        form = RoadmapMilestoneForm(instance=ms, company=company)

    return render(
        request,
        'roadmap/form.html',
        {'form': form, 'page_title': f'Редактировать веху: {ms.title}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def milestone_status(request, pk):
    company = _get_active_company(request)
    ms = get_object_or_404(RoadmapMilestone, pk=pk, company=company)
    new_status = request.POST.get('status')
    if new_status in dict(RoadmapMilestone.Status.choices):
        ms.status = new_status
        ms.save(update_fields=['status'])
        _log(company, request.user, 'Дорожная карта', f'Веха «{ms.title}» → {ms.get_status_display()}')
        messages.success(request, f'Статус вехи «{ms.title}»: {ms.get_status_display()}.')
    return redirect('roadmap_list')


@login_required
@require_POST
def milestone_check_toggle(request, pk):
    company = _get_active_company(request)
    item = get_object_or_404(MilestoneCheckItem, pk=pk, milestone__company=company)
    item.is_done = not item.is_done
    item.save(update_fields=['is_done'])
    return redirect('roadmap_list')


@login_required
@require_POST
def milestone_check_add(request, pk):
    company = _get_active_company(request)
    ms = get_object_or_404(RoadmapMilestone, pk=pk, company=company)
    title = request.POST.get('title', '').strip()
    if title:
        MilestoneCheckItem.objects.create(milestone=ms, title=title[:220])
        messages.success(request, 'Пункт добавлен в чек-лист.')
    return redirect('roadmap_list')


@login_required
@require_POST
def milestone_delete(request, pk):
    company = _get_active_company(request)
    ms = get_object_or_404(RoadmapMilestone, pk=pk, company=company)
    title = ms.title
    ms.delete()
    messages.warning(request, f'Веха «{title}» удалена.')
    return redirect('roadmap_list')


# ---------------------------------------------------------------------------
# 5. Cap Table, Vesting & Round Dilution Simulator
# ---------------------------------------------------------------------------


@login_required
def cap_table_view(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    holders = list(EquityHolder.objects.filter(company=company))
    today = timezone.localdate()

    holder_rows = []
    role_totals = {'FOUNDER': Decimal('0'), 'INVESTOR': Decimal('0'), 'ESOP': Decimal('0'), 'ADVISOR': Decimal('0')}
    total_pct = Decimal('0')
    for h in holders:
        total_pct += h.ownership_pct
        role_totals[h.role] = role_totals.get(h.role, Decimal('0')) + h.ownership_pct
        vesting = compute_vesting_progress(
            total_pct=float(h.ownership_pct),
            vesting_months=h.vesting_months,
            cliff_months=h.cliff_months,
            start_date=h.start_date,
            today=today,
        )
        holder_rows.append({'holder': h, 'vesting': vesting})

    # Round dilution simulation via GET parameters (zero JS!)
    pre_money = _int_param(request, 'pre_money', 250_000_000, 1_000_000, 100_000_000_000)
    invest_amount = _int_param(request, 'invest_amount', 60_000_000, 0, 100_000_000_000)
    new_esop = _float_param(request, 'new_esop', 5.0, 0.0, 30.0)

    dilution = simulate_round_dilution(
        holders=holders,
        pre_money_valuation=float(pre_money),
        investment_amount=float(invest_amount),
        new_esop_pool_pct=new_esop,
    )

    return render(
        request,
        'captable/index.html',
        {
            'company': company,
            'holder_rows': holder_rows,
            'total_pct': total_pct,
            'role_totals': role_totals,
            'sim_pre_money': pre_money,
            'sim_invest_amount': invest_amount,
            'sim_new_esop': new_esop,
            'dilution': dilution,
        },
    )


@login_required
def equity_holder_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = EquityHolderForm(request.POST)
        if form.is_valid():
            eh = form.save(commit=False)
            eh.company = company
            eh.save()
            _log(company, request.user, 'Cap Table', f'Добавлен держатель доли «{eh.name}» ({eh.ownership_pct}%)')
            messages.success(request, f'Участник «{eh.name}» добавлен в Cap Table.')
            return redirect('cap_table')
    else:
        form = EquityHolderForm()

    return render(
        request,
        'captable/form.html',
        {'form': form, 'page_title': 'Новый участник Cap Table', 'submit_label': 'Добавить в реестр'},
    )


@login_required
def equity_holder_edit(request, pk):
    company = _get_active_company(request)
    eh = get_object_or_404(EquityHolder, pk=pk, company=company)
    if request.method == 'POST':
        form = EquityHolderForm(request.POST, instance=eh)
        if form.is_valid():
            form.save()
            messages.success(request, 'Запись Cap Table обновлена.')
            return redirect('cap_table')
    else:
        form = EquityHolderForm(instance=eh)

    return render(
        request,
        'captable/form.html',
        {'form': form, 'page_title': f'Участник: {eh.name}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def equity_holder_delete(request, pk):
    company = _get_active_company(request)
    eh = get_object_or_404(EquityHolder, pk=pk, company=company)
    name = eh.name
    eh.delete()
    messages.warning(request, f'Участник «{name}» удалён из Cap Table.')
    return redirect('cap_table')


# ---------------------------------------------------------------------------
# 6. Growth Experiments (ICE Scoring)
# ---------------------------------------------------------------------------


@login_required
def experiment_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    status_filter = request.GET.get('status', '').strip()
    exps = list(GrowthExperiment.objects.filter(company=company).select_related('owner'))
    exps.sort(key=lambda e: (-e.ice_score, -e.id))

    running_count = sum(1 for e in exps if e.status == GrowthExperiment.Status.RUNNING)
    validated_count = sum(1 for e in exps if e.status == GrowthExperiment.Status.VALIDATED)
    rejected_count = sum(1 for e in exps if e.status == GrowthExperiment.Status.REJECTED)
    decided = validated_count + rejected_count
    success_rate = round((validated_count / decided) * 100) if decided > 0 else 0

    filtered = [e for e in exps if not status_filter or e.status == status_filter]

    return render(
        request,
        'experiments/list.html',
        {
            'company': company,
            'experiments': filtered,
            'status_filter': status_filter,
            'status_choices': GrowthExperiment.Status.choices,
            'total_count': len(exps),
            'running_count': running_count,
            'validated_count': validated_count,
            'success_rate': success_rate,
        },
    )


@login_required
def experiment_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = GrowthExperimentForm(request.POST, company=company)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.company = company
            exp.save()
            _log(company, request.user, 'Гипотезы', f'Добавлена гипотеза «{exp.title}» (ICE {exp.ice_score})')
            messages.success(request, f'Гипотеза «{exp.title}» добавлена в бэклог.')
            return redirect('experiment_list')
    else:
        form = GrowthExperimentForm(company=company)

    return render(
        request,
        'experiments/form.html',
        {'form': form, 'page_title': 'Новая гипотеза роста (ICE)', 'submit_label': 'Добавить гипотезу'},
    )


@login_required
def experiment_edit(request, pk):
    company = _get_active_company(request)
    exp = get_object_or_404(GrowthExperiment, pk=pk, company=company)
    if request.method == 'POST':
        form = GrowthExperimentForm(request.POST, instance=exp, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Гипотеза обновлена.')
            return redirect('experiment_list')
    else:
        form = GrowthExperimentForm(instance=exp, company=company)

    return render(
        request,
        'experiments/form.html',
        {'form': form, 'page_title': f'Гипотеза: {exp.title}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def experiment_status(request, pk):
    company = _get_active_company(request)
    exp = get_object_or_404(GrowthExperiment, pk=pk, company=company)
    new_status = request.POST.get('status')
    if new_status in dict(GrowthExperiment.Status.choices):
        exp.status = new_status
        exp.save(update_fields=['status'])
        _log(company, request.user, 'Гипотезы', f'Гипотеза «{exp.title}» → {exp.get_status_display()}')
        messages.success(request, f'Статус гипотезы «{exp.title}»: {exp.get_status_display()}.')
    return redirect('experiment_list')


@login_required
@require_POST
def experiment_delete(request, pk):
    company = _get_active_company(request)
    exp = get_object_or_404(GrowthExperiment, pk=pk, company=company)
    title = exp.title
    exp.delete()
    messages.warning(request, f'Гипотеза «{title}» удалена.')
    return redirect('experiment_list')


# ---------------------------------------------------------------------------
# 7. Investor Data Room
# ---------------------------------------------------------------------------


@login_required
def data_room_list(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    docs = list(DataRoomDoc.objects.filter(company=company).select_related('owner'))
    readiness = compute_data_room_readiness(docs)

    cat_filter = request.GET.get('category', '').strip()
    access_filter = request.GET.get('access', '').strip()
    filtered = docs
    if cat_filter:
        filtered = [d for d in filtered if d.category == cat_filter]
    if access_filter:
        filtered = [d for d in filtered if d.access_level == access_filter]

    return render(
        request,
        'dataroom/list.html',
        {
            'company': company,
            'docs': filtered,
            'total_docs': len(docs),
            'readiness': readiness,
            'cat_filter': cat_filter,
            'access_filter': access_filter,
            'category_choices': DataRoomDoc.Category.choices,
            'access_choices': DataRoomDoc.AccessLevel.choices,
            'status_choices': DataRoomDoc.Status.choices,
        },
    )


@login_required
def data_room_create(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    if request.method == 'POST':
        form = DataRoomDocForm(request.POST, company=company)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.company = company
            doc.save()
            _log(company, request.user, 'Data Room', f'Добавлен документ «{doc.title}» ({doc.version_label})')
            messages.success(request, f'Документ «{doc.title}» добавлен в Data Room.')
            return redirect('data_room_list')
    else:
        form = DataRoomDocForm(company=company)

    return render(
        request,
        'dataroom/form.html',
        {'form': form, 'page_title': 'Новый документ Data Room', 'submit_label': 'Добавить документ'},
    )


@login_required
def data_room_edit(request, pk):
    company = _get_active_company(request)
    doc = get_object_or_404(DataRoomDoc, pk=pk, company=company)
    if request.method == 'POST':
        form = DataRoomDocForm(request.POST, instance=doc, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ Data Room обновлён.')
            return redirect('data_room_list')
    else:
        form = DataRoomDocForm(instance=doc, company=company)

    return render(
        request,
        'dataroom/form.html',
        {'form': form, 'page_title': f'Документ: {doc.title}', 'submit_label': 'Сохранить'},
    )


@login_required
@require_POST
def data_room_status(request, pk):
    company = _get_active_company(request)
    doc = get_object_or_404(DataRoomDoc, pk=pk, company=company)
    new_status = request.POST.get('status')
    if new_status in dict(DataRoomDoc.Status.choices):
        doc.status = new_status
        doc.updated_at = timezone.localdate()
        doc.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Статус документа «{doc.title}»: {doc.get_status_display()}.')
    return redirect('data_room_list')


@login_required
@require_POST
def data_room_delete(request, pk):
    company = _get_active_company(request)
    doc = get_object_or_404(DataRoomDoc, pk=pk, company=company)
    title = doc.title
    doc.delete()
    messages.warning(request, f'Документ «{title}» удалён из Data Room.')
    return redirect('data_room_list')


# ---------------------------------------------------------------------------
# 8. Investor Update Report Generator (SSR Preview + Print + .md Download)
# ---------------------------------------------------------------------------


@login_required
def investor_report_view(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    today = timezone.localdate()
    quarter_num = (today.month - 1) // 3 + 1
    default_period = f'Q{quarter_num} {today.year}'

    src = request.POST if request.method == 'POST' else request.GET
    period_title = src.get('period_title', default_period).strip() or default_period
    highlights = src.get(
        'highlights',
        '- Ускорили расчёт ключевых операций и расширили корпоративные пилоты.\n- Удержали отток ниже целевого порога и усилили команду продаж.',
    )
    challenges = src.get(
        'challenges',
        '- Удлинение цикла юридического согласования в enterprise-сделках.',
    )
    asks = src.get(
        'asks',
        '- Тёплые интро к директорам по закупкам/операциям в профильных сетях.\n- Рекомендации сильных B2B Account Executives.',
    )

    cash_on_hand, monthly_burn, runway_months, total_raised = _company_cash_and_burn(company)
    active_emp_count = Employee.objects.filter(company=company).exclude(status=Employee.Status.INACTIVE).count()
    deals = list(Deal.objects.filter(company=company))
    deal_metrics = compute_deal_metrics(deals)
    kpis = list(KPIMetric.objects.filter(company=company))
    milestones = list(RoadmapMilestone.objects.filter(company=company).prefetch_related('checklist_items'))
    rounds = list(FundingRound.objects.filter(company=company))

    report_text = build_investor_update_report(
        company=company,
        period_title=period_title,
        cash_on_hand=float(cash_on_hand),
        monthly_burn=float(monthly_burn),
        runway_months=runway_months,
        total_closed_raised=float(total_raised),
        active_emp_count=active_emp_count,
        deal_metrics=deal_metrics,
        kpis=kpis,
        milestones=milestones,
        rounds=rounds,
        highlights=highlights,
        challenges=challenges,
        asks=asks,
    )

    if request.method == 'POST' and request.POST.get('action') == 'download':
        safe_slug = ''.join(ch if ch.isalnum() else '_' for ch in company.name).strip('_') or 'company'
        response = HttpResponse(report_text, content_type='text/markdown; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="investor_update_{safe_slug}.md"'
        return response

    return render(
        request,
        'reports/investor_update.html',
        {
            'company': company,
            'period_title': period_title,
            'highlights': highlights,
            'challenges': challenges,
            'asks': asks,
            'report_text': report_text,
            'cash_on_hand': cash_on_hand,
            'monthly_burn': monthly_burn,
            'runway_months': runway_months,
            'deal_metrics': deal_metrics,
        },
    )


# ---------------------------------------------------------------------------
# 9. Global Workspace Search (Zero-JS Topbar Search)
# ---------------------------------------------------------------------------


@login_required
def global_search_view(request):
    company = _get_active_company(request)
    if company is None:
        return redirect('company_create')

    q = request.GET.get('q', '').strip()
    results = []
    if q:
        for t in Task.objects.filter(company=company).filter(Q(title__icontains=q) | Q(description__icontains=q))[:8]:
            results.append({'section': 'Задачи', 'title': t.title, 'meta': t.get_status_display(), 'url_name': 'task_detail', 'arg': t.id})
        for d in Deal.objects.filter(company=company).filter(Q(client_name__icontains=q) | Q(contact_name__icontains=q) | Q(notes__icontains=q))[:8]:
            results.append({'section': 'CRM-сделки', 'title': d.client_name, 'meta': d.get_stage_display(), 'url_name': 'deal_edit', 'arg': d.id})
        for inv in Invoice.objects.filter(company=company).filter(Q(invoice_number__icontains=q) | Q(client_name__icontains=q) | Q(service_title__icontains=q))[:8]:
            results.append({'section': 'Счета', 'title': f'№ {inv.invoice_number} - {inv.client_name}', 'meta': inv.get_status_display(), 'url_name': 'invoice_edit', 'arg': inv.id})
        for exp in Expense.objects.filter(company=company).filter(Q(title__icontains=q) | Q(vendor__icontains=q))[:8]:
            results.append({'section': 'Расходы', 'title': exp.title, 'meta': exp.vendor or exp.get_category_display(), 'url_name': 'expense_edit', 'arg': exp.id})
        for b in BudgetItem.objects.filter(company=company, name__icontains=q)[:6]:
            results.append({'section': 'Бюджет', 'title': b.name, 'meta': b.period, 'url_name': 'budget_edit', 'arg': b.id})
        for emp in Employee.objects.filter(company=company).filter(Q(full_name__icontains=q) | Q(position__icontains=q))[:6]:
            results.append({'section': 'Команда', 'title': emp.full_name, 'meta': emp.position, 'url_name': 'employee_detail', 'arg': emp.id})
        for k in KPIMetric.objects.filter(company=company, name__icontains=q)[:6]:
            results.append({'section': 'KPI', 'title': k.name, 'meta': k.period_label, 'url_name': 'kpi_detail', 'arg': k.id})
        for ms in RoadmapMilestone.objects.filter(company=company).filter(Q(title__icontains=q) | Q(summary__icontains=q))[:6]:
            results.append({'section': 'Дорожная карта', 'title': ms.title, 'meta': ms.quarter, 'url_name': 'milestone_edit', 'arg': ms.id})
        for ge in GrowthExperiment.objects.filter(company=company).filter(Q(title__icontains=q) | Q(hypothesis__icontains=q))[:6]:
            results.append({'section': 'Гипотезы (ICE)', 'title': ge.title, 'meta': f'ICE {ge.ice_score}', 'url_name': 'experiment_edit', 'arg': ge.id})
        for doc in DataRoomDoc.objects.filter(company=company).filter(Q(title__icontains=q) | Q(summary__icontains=q))[:6]:
            results.append({'section': 'Data Room', 'title': doc.title, 'meta': doc.version_label, 'url_name': 'data_room_edit', 'arg': doc.id})

    return render(
        request,
        'search/results.html',
        {
            'company': company,
            'q': q,
            'results': results,
        },
    )
