"""
Pure-Python financial analytics, Runway simulation, SaaS unit economics,
Cap Table dilution modeling, Founder Focus alerts, Investor Updates,
and Server-Side SVG chart coordinate builders for VectorStartUp (Django SSR).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math
from typing import Iterable, Sequence

MONTH_SHORT_RU = [
    'Янв',
    'Фев',
    'Мар',
    'Апр',
    'Май',
    'Июн',
    'Июл',
    'Авг',
    'Сен',
    'Окт',
    'Ноя',
    'Дек',
]


def format_money_text(value: float | Decimal | int, symbol: str = '₽') -> str:
    num = float(value or 0)
    formatted = f'{num:,.0f}'.replace(',', ' ')
    if symbol in ('$', '€'):
        return f'{symbol}{formatted}'
    return f'{formatted} {symbol}'


def format_money_compact_text(value: float | Decimal | int, symbol: str = '₽') -> str:
    num = float(value or 0)
    abs_num = abs(num)
    if abs_num >= 1_000_000:
        short = f'{num / 1_000_000:.2f}'.rstrip('0').rstrip('.').replace('.', ',')
        return f'{short} млн {symbol}' if symbol == '₽' else f'{symbol}{short}M'
    if abs_num >= 100_000:
        short = f'{num / 1_000:.0f}'
        return f'{short} тыс. {symbol}' if symbol == '₽' else f'{symbol}{short}K'
    return format_money_text(num, symbol)


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not (12 <= mod100 <= 14):
        return few
    return many


@dataclass
class RunwayMonthPoint:
    month_index: int
    label: str
    revenue: int
    expenses: int
    funding_inflow: int
    net_cashflow: int
    ending_cash: int
    is_break_even: bool


@dataclass
class RunwaySimulationResult:
    points: list[RunwayMonthPoint]
    runway_months: int | None
    break_even_month: int | None
    ending_cash_at_horizon: int
    min_cash_point: RunwayMonthPoint
    revenue_at_horizon: int


def simulate_runway_projection(
    *,
    starting_cash: float,
    current_monthly_revenue: float,
    current_monthly_burn: float,
    monthly_revenue_growth_pct: float = 12.0,
    planned_hires: int = 0,
    avg_hire_monthly_cost: float = 220_000.0,
    hire_start_month: int = 3,
    marketing_delta_pct: float = 0.0,
    funding_amount: float = 0.0,
    funding_month: int = 6,
    months: int = 18,
    start_year: int | None = None,
    start_month: int | None = None,
) -> RunwaySimulationResult:
    today = date.today()
    base_year = start_year or today.year
    base_month = start_month or today.month
    horizon = max(3, min(36, int(months)))

    cash = max(0.0, float(starting_cash))
    revenue = max(0.0, float(current_monthly_revenue))
    base_expenses = max(0.0, float(current_monthly_burn))
    growth_factor = 1.0 + float(monthly_revenue_growth_pct) / 100.0
    marketing_multiplier = max(0.2, 1.0 + float(marketing_delta_pct) / 100.0)

    points: list[RunwayMonthPoint] = []
    runway_months: int | None = None
    break_even_month: int | None = None

    for m in range(1, horizon + 1):
        if m > 1:
            revenue = max(0.0, round(revenue * growth_factor))
        else:
            revenue = round(revenue)

        hiring_cost = (
            int(planned_hires) * max(0.0, float(avg_hire_monthly_cost))
            if planned_hires > 0 and m >= hire_start_month
            else 0.0
        )
        adjusted_base = round(base_expenses * marketing_multiplier)
        expenses = int(max(0, round(adjusted_base + hiring_cost)))
        funding_inflow = (
            int(round(funding_amount))
            if funding_amount > 0 and int(funding_month) == m
            else 0
        )

        net_cashflow = int(revenue) - expenses + funding_inflow
        cash = round(cash + net_cashflow)

        month_offset = (base_month - 1) + (m - 1)
        cur_year = base_year + month_offset // 12
        cur_month = (month_offset % 12) + 1
        label = f'{MONTH_SHORT_RU[cur_month - 1]} {str(cur_year)[-2:]}'

        is_break_even = revenue >= expenses and expenses > 0
        if is_break_even and break_even_month is None:
            break_even_month = m
        if cash <= 0 and runway_months is None:
            runway_months = m

        points.append(
            RunwayMonthPoint(
                month_index=m,
                label=label,
                revenue=int(revenue),
                expenses=expenses,
                funding_inflow=funding_inflow,
                net_cashflow=net_cashflow,
                ending_cash=int(cash),
                is_break_even=is_break_even,
            )
        )

    min_cash_point = min(points, key=lambda pt: pt.ending_cash)
    return RunwaySimulationResult(
        points=points,
        runway_months=runway_months,
        break_even_month=break_even_month,
        ending_cash_at_horizon=points[-1].ending_cash if points else 0,
        min_cash_point=min_cash_point,
        revenue_at_horizon=points[-1].revenue if points else 0,
    )


def build_runway_svg_chart(
    points: Sequence[RunwayMonthPoint],
    currency_symbol: str = '₽',
    width: int = 760,
    height: int = 240,
) -> dict:
    """Compute pure server-side SVG geometry for 18-month Cash Balance & Revenue/Burn chart."""
    pad_l, pad_r, pad_t, pad_b = 76, 20, 20, 34
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    if not points:
        return {
            'width': width,
            'height': height,
            'cash_polyline': '',
            'cash_area': '',
            'zero_y': pad_t + plot_h,
            'grid_lines': [],
            'x_labels': [],
            'dots': [],
        }

    values = [p.ending_cash for p in points]
    raw_min = min(0, min(values))
    raw_max = max(1, max(values))
    span = max(1.0, float(raw_max - raw_min))

    def map_x(idx: int) -> float:
        if len(points) == 1:
            return pad_l + plot_w / 2
        return pad_l + (idx / (len(points) - 1)) * plot_w

    def map_y(val: float) -> float:
        return pad_t + plot_h - ((val - raw_min) / span) * plot_h

    coords = []
    dots = []
    x_labels = []
    step_label = max(1, math.ceil(len(points) / 6))

    for idx, pt in enumerate(points):
        x = map_x(idx)
        y = map_y(pt.ending_cash)
        coords.append(f'{x:.1f},{y:.1f}')
        dots.append(
            {
                'x': round(x, 1),
                'y': round(y, 1),
                'label': pt.label,
                'value': format_money_compact_text(pt.ending_cash, currency_symbol),
                'negative': pt.ending_cash <= 0,
                'funding': pt.funding_inflow > 0,
            }
        )
        if idx == 0 or idx == len(points) - 1 or idx % step_label == 0:
            x_labels.append({'x': round(x, 1), 'text': pt.label})

    zero_y = round(map_y(0), 1)
    first_x = round(map_x(0), 1)
    last_x = round(map_x(len(points) - 1), 1)
    cash_area = f'{first_x},{zero_y} ' + ' '.join(coords) + f' {last_x},{zero_y}'

    grid_lines = []
    for i in range(4):
        frac = i / 3
        val = raw_min + frac * span
        gy = round(map_y(val), 1)
        grid_lines.append(
            {
                'y': gy,
                'label_y': round(gy + 4, 1),
                'label': format_money_compact_text(val, currency_symbol),
            }
        )

    # Revenue vs Burn comparison bars/lines SVG
    rb_max = max(1, max(max(p.revenue, p.expenses) for p in points))
    rev_coords = []
    exp_coords = []
    for idx, pt in enumerate(points):
        x = map_x(idx)
        ry = pad_t + plot_h - (pt.revenue / rb_max) * plot_h
        ey = pad_t + plot_h - (pt.expenses / rb_max) * plot_h
        rev_coords.append(f'{x:.1f},{ry:.1f}')
        exp_coords.append(f'{x:.1f},{ey:.1f}')

    rb_grid = []
    for i in range(4):
        val = (i / 3) * rb_max
        gy = round(pad_t + plot_h - (i / 3) * plot_h, 1)
        rb_grid.append({'y': gy, 'label_y': round(gy + 4, 1), 'label': format_money_compact_text(val, currency_symbol)})

    return {
        'width': width,
        'height': height,
        'pad_l': pad_l,
        'label_x': pad_l - 8,
        'x_label_y': height - 10,
        'pad_r': pad_r,
        'plot_right': width - pad_r,
        'plot_bottom': pad_t + plot_h,
        'cash_polyline': ' '.join(coords),
        'cash_area': cash_area,
        'zero_y': zero_y,
        'grid_lines': grid_lines,
        'x_labels': x_labels,
        'dots': dots,
        'rev_polyline': ' '.join(rev_coords),
        'exp_polyline': ' '.join(exp_coords),
        'rb_grid': rb_grid,
    }

def compute_unit_economics(
    *,
    arpu: float,
    gross_margin_pct: float,
    monthly_churn_pct: float,
    cac: float,
    active_customers: int,
    monthly_growth_pct: float,
    monthly_burn: float,
) -> dict:
    arpu_v = max(0.0, float(arpu))
    margin = max(0.0, min(100.0, float(gross_margin_pct))) / 100.0
    churn = max(0.1, float(monthly_churn_pct)) / 100.0
    cac_v = max(0.0, float(cac))
    customers = max(0, int(active_customers))

    mrr = round(arpu_v * customers)
    arr = mrr * 12
    monthly_gp_per_customer = arpu_v * margin
    ltv = round(monthly_gp_per_customer / churn)
    ltv_cac_ratio = round(ltv / cac_v, 2) if cac_v > 0 else 0.0
    cac_payback_months = (
        round(cac_v / monthly_gp_per_customer, 1)
        if monthly_gp_per_customer > 0
        else 0.0
    )

    annualized_growth_pct = round(((1.0 + float(monthly_growth_pct) / 100.0) ** 12 - 1.0) * 100.0, 1)
    profit_margin_pct = (
        round(((mrr - float(monthly_burn)) / mrr) * 100.0, 1) if mrr > 0 else -100.0
    )
    rule_of_40 = round(annualized_growth_pct + profit_margin_pct, 1)

    if ltv_cac_ratio >= 3.0 and 0 < cac_payback_months <= 12.0:
        health_state = 'good'
        health_label = 'Здоровая экономика'
    elif ltv_cac_ratio < 1.5 or cac_payback_months > 24.0:
        health_state = 'risk'
        health_label = 'Требует оптимизации'
    else:
        health_state = 'warn'
        health_label = 'В зоне наблюдения'

    return {
        'mrr': mrr,
        'arr': arr,
        'ltv': ltv,
        'ltv_cac_ratio': ltv_cac_ratio,
        'cac_payback_months': cac_payback_months,
        'annualized_growth_pct': annualized_growth_pct,
        'profit_margin_pct': profit_margin_pct,
        'rule_of_40': rule_of_40,
        'health_state': health_state,
        'health_label': health_label,
    }

def deal_monthly_value(amount: float | Decimal, billing_type: str) -> int:
    val = float(amount or 0)
    if billing_type == 'ANNUAL':
        return round(val / 12.0)
    if billing_type == 'ONE_TIME':
        return 0
    return round(val)


def compute_deal_metrics(deals: Iterable) -> dict:
    deals_list = list(deals)
    open_deals = [d for d in deals_list if d.stage not in ('WON', 'LOST')]
    won_deals = [d for d in deals_list if d.stage == 'WON']
    lost_deals = [d for d in deals_list if d.stage == 'LOST']

    open_pipeline_total = sum(float(d.amount) for d in open_deals)
    weighted_pipeline = round(
        sum(float(d.amount) * (float(d.probability) / 100.0) for d in open_deals)
    )
    won_monthly_equivalent = sum(
        deal_monthly_value(d.amount, d.billing_type) for d in won_deals
    )
    closed_count = len(won_deals) + len(lost_deals)
    win_rate_pct = round((len(won_deals) / closed_count) * 100) if closed_count > 0 else 0

    return {
        'open_deals_count': len(open_deals),
        'open_pipeline_total': round(open_pipeline_total),
        'weighted_pipeline': weighted_pipeline,
        'won_deals_count': len(won_deals),
        'won_monthly_equivalent': won_monthly_equivalent,
        'win_rate_pct': win_rate_pct,
    }

# 4. Invoices & Receivables Metrics

def compute_invoice_metrics(invoices: Iterable, today: date | None = None) -> dict:
    ref_day = today or date.today()
    paid_total = 0.0
    receivable_total = 0.0
    overdue_total = 0.0
    overdue_count = 0
    draft_total = 0.0

    for inv in invoices:
        amt = float(inv.amount)
        if inv.status == 'PAID':
            paid_total += amt
        elif inv.status == 'SENT':
            receivable_total += amt
            if inv.due_date and inv.due_date < ref_day:
                overdue_total += amt
                overdue_count += 1
        else:
            draft_total += amt

    return {
        'paid_total': round(paid_total),
        'receivable_total': round(receivable_total),
        'overdue_total': round(overdue_total),
        'overdue_count': overdue_count,
        'draft_total': round(draft_total),
    }


def build_invoice_text_document(company, invoice) -> str:
    vat_line = (
        'Включая НДС 20%'
        if invoice.vat_included
        else 'Без НДС (УСН / освобождение от НДС)'
    )
    if invoice.status == 'PAID':
        paid_str = invoice.paid_date.strftime('%d.%m.%Y') if invoice.paid_date else ''
        status_text = f'Оплачен ({paid_str})'.strip()
    elif invoice.status == 'SENT':
        status_text = 'Ожидает оплаты'
    else:
        status_text = 'Черновик'

    return '\n'.join(
        [
            f'СЧЁТ НА ОПЛАТУ № {invoice.invoice_number}',
            f'Дата выставления: {invoice.issue_date.strftime("%d.%m.%Y")}',
            f'Срок оплаты: до {invoice.due_date.strftime("%d.%m.%Y")}',
            '',
            f'Поставщик: {company.legal_name or company.name}',
            f'Покупатель: {invoice.client_name}',
            '',
            'Наименование услуги / лицензии:',
            f'- {invoice.service_title}',
            '',
            f'Итого к оплате: {format_money_text(invoice.amount, company.currency_symbol)}',
            f'Налогообложение: {vat_line}',
            f'Статус: {status_text}',
        ]
    )

# 5. Cap Table Dilution Simulator & Vesting Math


def compute_vesting_progress(
    *,
    total_pct: float,
    vesting_months: int,
    cliff_months: int,
    start_date: date | None,
    today: date | None = None,
) -> dict:
    total = max(0.0, float(total_pct))
    if vesting_months <= 0:
        return {
            'vested_pct': round(total, 2),
            'unvested_pct': 0.0,
            'vested_ratio_pct': 100,
            'months_elapsed': 0,
        }

    ref_day = today or date.today()
    if start_date is None:
        elapsed = 0
    else:
        elapsed = max(0, (ref_day.year - start_date.year) * 12 + (ref_day.month - start_date.month))

    if elapsed < cliff_months:
        return {
            'vested_pct': 0.0,
            'unvested_pct': round(total, 2),
            'vested_ratio_pct': 0,
            'months_elapsed': elapsed,
        }

    ratio = min(1.0, elapsed / float(vesting_months))
    vested_pct = round(total * ratio, 2)
    unvested_pct = round(max(0.0, total - vested_pct), 2)
    return {
        'vested_pct': vested_pct,
        'unvested_pct': unvested_pct,
        'vested_ratio_pct': round(ratio * 100),
        'months_elapsed': elapsed,
    }


def simulate_round_dilution(
    *,
    holders: Sequence,
    pre_money_valuation: float,
    investment_amount: float,
    new_esop_pool_pct: float = 0.0,
) -> dict:
    pre_money = max(1.0, float(pre_money_valuation))
    investment = max(0.0, float(investment_amount))
    post_money = pre_money + investment
    new_investor_pct = round((investment / post_money) * 100.0, 2)
    esop_top_up_pct = max(0.0, min(30.0, float(new_esop_pool_pct)))
    retention_factor = max(0.0, (100.0 - new_investor_pct - esop_top_up_pct) / 100.0)

    total_current = sum(float(h.ownership_pct) for h in holders) or 100.0

    rows = []
    for h in holders:
        before_pct = round((float(h.ownership_pct) / total_current) * 100.0, 2)
        after_pct = round(before_pct * retention_factor, 2)
        rows.append(
            {
                'name': h.name,
                'role': h.role,
                'role_label': h.get_role_display() if hasattr(h, 'get_role_display') else h.role,
                'before_pct': before_pct,
                'after_pct': after_pct,
                'dilution_delta_pct': round(after_pct - before_pct, 2),
                'post_money_value': round((after_pct / 100.0) * post_money),
            }
        )

    if esop_top_up_pct > 0:
        rows.append(
            {
                'name': 'Расширение опционного пула (новый ESOP)',
                'role': 'ESOP',
                'role_label': 'Опционный пул (ESOP)',
                'before_pct': 0.0,
                'after_pct': esop_top_up_pct,
                'dilution_delta_pct': esop_top_up_pct,
                'post_money_value': round((esop_top_up_pct / 100.0) * post_money),
            }
        )

    if new_investor_pct > 0:
        rows.append(
            {
                'name': 'Новый инвестор раунда',
                'role': 'INVESTOR',
                'role_label': 'Инвестор',
                'before_pct': 0.0,
                'after_pct': new_investor_pct,
                'dilution_delta_pct': new_investor_pct,
                'post_money_value': round(investment),
            }
        )

    return {
        'pre_money': round(pre_money),
        'investment_amount': round(investment),
        'post_money': round(post_money),
        'new_investor_pct': new_investor_pct,
        'esop_top_up_pct': esop_top_up_pct,
        'retention_factor': retention_factor,
        'rows': rows,
    }



# 6. Growth Experiments (ICE) & Data Room Readiness


def compute_ice_score(impact: int, confidence: int, ease: int) -> float:
    imp = max(1, min(10, int(impact)))
    conf = max(1, min(10, int(confidence)))
    ea = max(1, min(10, int(ease)))
    return round((imp + conf + ea) / 3.0, 1)


def compute_data_room_readiness(docs: Iterable) -> dict:
    investor_docs = [d for d in docs if d.access_level == 'INVESTORS']
    ready_docs = [d for d in investor_docs if d.status == 'READY']
    total = len(investor_docs)
    ready = len(ready_docs)
    readiness_pct = round((ready / total) * 100) if total > 0 else 0
    return {
        'total_investor_docs': total,
        'ready_investor_docs': ready,
        'readiness_pct': readiness_pct,
    }



# 7. Founder Focus Alerts & Investor Update Report



def compute_founder_alerts(
    *,
    company,
    runway_months: float | None,
    budget_rows: Sequence[dict],
    overdue_tasks: Sequence,
    deals: Sequence,
    kpis: Sequence,
    invoices: Sequence,
    today: date | None = None,
) -> list[dict]:
    alerts: list[dict] = []
    sym = company.currency_symbol
    ref_day = today or date.today()

    if invoices:
        inv_metrics = compute_invoice_metrics(invoices, ref_day)
        if inv_metrics['overdue_count'] > 0:
            alerts.append(
                {
                    'severity': 'risk',
                    'severity_label': 'Критично',
                    'title': f'Просроченная дебиторка: {format_money_compact_text(inv_metrics["overdue_total"], sym)}',
                    'detail': f'Ожидают оплаты просроченные счета ({inv_metrics["overdue_count"]} шт.) - напомните контрагентам.',
                    'url_name': 'invoice_list',
                    'action_label': 'К счетам',
                }
            )

    if runway_months is not None and 0 < runway_months < 9:
        sev = 'risk' if runway_months < 6 else 'warn'
        alerts.append(
            {
                'severity': sev,
                'severity_label': 'Критично' if sev == 'risk' else 'Внимание',
                'title': f'Запас прочности (Runway): {runway_months} мес.',
                'detail': 'Смоделируйте сокращение burn rate или подготовьте следующий раунд в финмодели.',
                'url_name': 'finance_simulator',
                'action_label': 'Открыть финмодель',
            }
        )

    for row in budget_rows:
        planned = float(row['item'].planned_amount)
        spent = float(row['spent'])
        if planned > 0 and spent > planned:
            over_pct = round(((spent - planned) / planned) * 100)
            alerts.append(
                {
                    'severity': 'risk',
                    'severity_label': 'Перерасход',
                    'title': f'Перерасход статьи «{row["item"].name}» (+{over_pct}%)',
                    'detail': f'Факт {format_money_compact_text(spent, sym)} при плане {format_money_compact_text(planned, sym)}.',
                    'url_name': 'budget_list',
                    'action_label': 'Проверить бюджет',
                }
            )
            break

    if overdue_tasks:
        first_task = overdue_tasks[0]
        due_txt = first_task.due_date.strftime('%d.%m.%Y') if first_task.due_date else ''
        alerts.append(
            {
                'severity': 'warn',
                'severity_label': 'Внимание',
                'title': f'Просроченные задачи: {len(overdue_tasks)}',
                'detail': f'Ближайшая: «{first_task.title}» (срок {due_txt}).',
                'url_name': 'task_list',
                'action_label': 'К задачам',
            }
        )

    hot_deals = [d for d in deals if d.stage == 'CONTRACT']
    if hot_deals:
        hot_sum = sum(float(d.amount) for d in hot_deals)
        n = len(hot_deals)
        word = _plural_ru(n, 'сделка', 'сделки', 'сделок')
        alerts.append(
            {
                'severity': 'good',
                'severity_label': 'Возможность',
                'title': f'{n} {word} на финальном согласовании договора',
                'detail': f'Потенциал закрытия: {format_money_compact_text(hot_sum, sym)} («{hot_deals[0].client_name}»).',
                'url_name': 'sales_pipeline',
                'action_label': 'Открыть CRM',
            }
        )

    lagging_kpi = next((k for k in kpis if k.progress_percent < 75), None)
    if lagging_kpi is not None:
        alerts.append(
            {
                'severity': 'warn',
                'severity_label': 'Отставание KPI',
                'title': f'KPI «{lagging_kpi.name}» отстаёт от цели',
                'detail': f'Текущее значение: {lagging_kpi.current_value} {lagging_kpi.unit} при цели {lagging_kpi.target_value} {lagging_kpi.unit}.',
                'url_name': 'kpi_list',
                'action_label': 'Обновить KPI',
            }
        )

    return alerts[:4]


def build_investor_update_report(
    *,
    company,
    period_title: str,
    cash_on_hand: float,
    monthly_burn: float,
    runway_months: float | None,
    total_closed_raised: float,
    active_emp_count: int,
    deal_metrics: dict,
    kpis: Sequence,
    milestones: Sequence,
    rounds: Sequence,
    highlights: str,
    challenges: str,
    asks: str,
) -> str:
    sym = company.currency_symbol
    kpi_lines = (
        '\n'.join(
            f'- {k.name}: {k.current_value} / {k.target_value} {k.unit} ({k.period_label})'
            for k in kpis
        )
        if kpis
        else '- Показатели KPI ещё не добавлены'
    )

    milestone_lines = (
        '\n'.join(
            f'- [{m.quarter}] {m.title} - готовность {m.progress_percent}%'
            for m in list(milestones)[:6]
        )
        if milestones
        else '- Вехи дорожной карты ещё не добавлены'
    )

    active_rounds = [r for r in rounds if r.status != 'CLOSED']
    round_line = (
        ', '.join(f'{r.round_name} ({format_money_compact_text(r.amount, sym)})' for r in active_rounds)
        if active_rounds
        else 'новых активных раундов нет'
    )
    runway_txt = f'{runway_months} мес.' if runway_months is not None else 'без ограничений'

    return '\n'.join(
        [
            f'Отчёт для инвесторов: {company.name} ({company.get_stage_display()})',
            f'Период: {period_title}',
            f'Отрасль: {company.industry}',
            '',
            '1. Ключевые финансовые показатели',
            f'- Денежный остаток (Cash): {format_money_text(cash_on_hand, sym)}',
            f'- Ежемесячный расход (Burn Rate): {format_money_text(monthly_burn, sym)}/мес',
            f'- Запас прочности (Runway): {runway_txt}',
            f'- Привлечено инвестиций: {format_money_text(total_closed_raised, sym)} (в пайплайне: {round_line})',
            f'- Целевой MRR: {format_money_text(company.target_mrr, sym)} · Команда: {active_emp_count} чел.',
            '',
            '2. Продажи и коммерческий пайплайн',
            f'- Активных сделок в воронке: {deal_metrics["open_deals_count"]} на сумму {format_money_text(deal_metrics["open_pipeline_total"], sym)}',
            f'- Взвешенный прогноз (Weighted Pipeline): {format_money_text(deal_metrics["weighted_pipeline"], sym)}',
            f'- Закрыто сделок: {deal_metrics["won_deals_count"]} (конверсия: {deal_metrics["win_rate_pct"]}%)',
            '',
            '3. Метрики KPI',
            kpi_lines,
            '',
            '4. Дорожная карта и вехи',
            milestone_lines,
            '',
            '5. Главные достижения периода',
            highlights.strip() or '- Заполните ключевые победы компании',
            '',
            '6. Вызовы и риски',
            challenges.strip() or '- Опишите основные узкие места',
            '',
            '7. Чем могут помочь инвесторы и советники (Asks)',
            asks.strip() or '- Укажите нужные интро, найм или экспертизу',
        ]
    )
