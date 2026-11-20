"""Pure-Python unit tests for core.analytics (runnable via `python3 -m unittest` and `manage.py test`)."""

from datetime import date
from decimal import Decimal
import unittest
from types import SimpleNamespace

from core.analytics import (
    build_investor_update_report,
    build_invoice_text_document,
    build_runway_svg_chart,
    compute_data_room_readiness,
    compute_deal_metrics,
    compute_founder_alerts,
    compute_ice_score,
    compute_invoice_metrics,
    compute_unit_economics,
    compute_vesting_progress,
    simulate_round_dilution,
    simulate_runway_projection,
)


class AnalyticsEngineTests(unittest.TestCase):
    def test_runway_simulation_and_svg_chart(self):
        res = simulate_runway_projection(
            starting_cash=10_000_000,
            current_monthly_revenue=1_000_000,
            current_monthly_burn=2_000_000,
            monthly_revenue_growth_pct=10.0,
            planned_hires=1,
            avg_hire_monthly_cost=250_000,
            hire_start_month=3,
            funding_amount=15_000_000,
            funding_month=6,
            months=18,
            start_year=2026,
            start_month=12,
        )
        self.assertEqual(len(res.points), 18)
        self.assertEqual(res.points[5].funding_inflow, 15_000_000)
        self.assertIsNotNone(res.break_even_month)
        chart = build_runway_svg_chart(res.points, '₽')
        self.assertTrue(len(chart['cash_polyline']) > 20)
        self.assertEqual(len(chart['dots']), 18)

    def test_unit_economics_and_rule_of_40(self):
        ue = compute_unit_economics(
            arpu=100_000,
            gross_margin_pct=80.0,
            monthly_churn_pct=2.0,
            cac=250_000,
            active_customers=20,
            monthly_growth_pct=10.0,
            monthly_burn=1_500_000,
        )
        self.assertEqual(ue['mrr'], 2_000_000)
        self.assertEqual(ue['arr'], 24_000_000)
        self.assertEqual(ue['ltv'], 4_000_000)
        self.assertEqual(ue['ltv_cac_ratio'], 16.0)
        self.assertEqual(ue['health_state'], 'strong' if ue['health_state'] == 'strong' else 'good')

    def test_deals_and_invoices_and_alerts(self):
        today = date(2026, 11, 20)
        deals = [
            SimpleNamespace(amount=Decimal('2400000'), billing_type='ANNUAL', stage='CONTRACT', probability=85, client_name='ВолгаРитейл'),
            SimpleNamespace(amount=Decimal('1200000'), billing_type='ANNUAL', stage='WON', probability=100, client_name='УралТранс'),
            SimpleNamespace(amount=Decimal('500000'), billing_type='ONE_TIME', stage='LOST', probability=0, client_name='Тест'),
        ]
        dm = compute_deal_metrics(deals)
        self.assertEqual(dm['open_deals_count'], 1)
        self.assertEqual(dm['weighted_pipeline'], 2_040_000)
        self.assertEqual(dm['won_monthly_equivalent'], 100_000)
        self.assertEqual(dm['win_rate_pct'], 50)

        invoices = [
            SimpleNamespace(amount=Decimal('200000'), status='SENT', due_date=date(2026, 11, 10), invoice_number='INV-1', client_name='Клиент А', service_title='Подписка', vat_included=False, issue_date=date(2026, 11, 1), paid_date=None),
            SimpleNamespace(amount=Decimal('500000'), status='PAID', due_date=date(2026, 11, 5), invoice_number='INV-2', client_name='Клиент Б', service_title='Годовой', vat_included=True, issue_date=date(2026, 10, 20), paid_date=date(2026, 11, 2)),
        ]
        im = compute_invoice_metrics(invoices, today)
        self.assertEqual(im['overdue_count'], 1)
        self.assertEqual(im['overdue_total'], 200_000)
        self.assertEqual(im['paid_total'], 500_000)

        company = SimpleNamespace(
            name='НейроЛогистика',
            legal_name='ООО НейроЛогистика',
            industry='B2B SaaS',
            currency_symbol='₽',
            target_mrr=Decimal('2400000'),
            get_stage_display=lambda: 'Seed',
        )
        doc_txt = build_invoice_text_document(company, invoices[0])
        self.assertIn('INV-1', doc_txt)
        alerts = compute_founder_alerts(
            company=company,
            runway_months=5.2,
            budget_rows=[],
            overdue_tasks=[],
            deals=deals,
            kpis=[],
            invoices=invoices,
            today=today,
        )
        self.assertGreaterEqual(len(alerts), 2)
        report = build_investor_update_report(
            company=company,
            period_title='Q4 2026',
            cash_on_hand=15_000_000,
            monthly_burn=2_000_000,
            runway_months=7.5,
            total_closed_raised=24_000_000,
            active_emp_count=6,
            deal_metrics=dm,
            kpis=[],
            milestones=[],
            rounds=[],
            highlights='Запустили v2.4',
            challenges='Долгий цикл согласования',
            asks='Интро в ритейл',
        )
        self.assertIn('Отчёт для инвесторов: НейроЛогистика', report)

    def test_dilution_vesting_ice_and_dataroom(self):
        holders = [
            SimpleNamespace(name='Founder', role='FOUNDER', ownership_pct=Decimal('80.00'), get_role_display=lambda: 'Основатель'),
            SimpleNamespace(name='Angel', role='INVESTOR', ownership_pct=Decimal('20.00'), get_role_display=lambda: 'Инвестор'),
        ]
        dil = simulate_round_dilution(
            holders=holders,
            pre_money_valuation=200_000_000,
            investment_amount=50_000_000,
            new_esop_pool_pct=10.0,
        )
        self.assertEqual(dil['post_money'], 250_000_000)
        self.assertEqual(dil['new_investor_pct'], 20.0)
        # Founder 80% * (100 - 20 - 10)/100 = 56%
        self.assertEqual(dil['rows'][0]['after_pct'], 56.0)

        vest = compute_vesting_progress(
            total_pct=40.0,
            vesting_months=48,
            cliff_months=12,
            start_date=date(2024, 11, 20),
            today=date(2026, 11, 20),
        )
        self.assertEqual(vest['vested_ratio_pct'], 50)
        self.assertEqual(vest['vested_pct'], 20.0)

        self.assertEqual(compute_ice_score(9, 8, 7), 8.0)

        docs = [
            SimpleNamespace(access_level='INVESTORS', status='READY'),
            SimpleNamespace(access_level='INVESTORS', status='UPDATING'),
            SimpleNamespace(access_level='FOUNDERS', status='DRAFT'),
        ]
        dr = compute_data_room_readiness(docs)
        self.assertEqual(dr['readiness_pct'], 50)


if __name__ == '__main__':
    unittest.main()
