"""Unit and integration tests for VectorStartUp Django MVC/MVT application."""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    BudgetCategory,
    BudgetItem,
    Company,
    CompanyMembership,
    Employee,
    Expense,
    FundingRound,
    InvestmentAllocation,
    Investor,
    KPIMetric,
    Task,
)

User = get_user_model()


class StartupHubMVTTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            first_name='Алиса',
            email='alice@example.ru',
            password='password123',
        )
        self.client.login(username='alice', password='password123')
        self.company = Company.objects.create(
            name='ТестСтарт',
            industry='SaaS',
            stage=Company.Stage.SEED,
            initial_cash=Decimal('1000000.00'),
            created_by=self.user,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.user,
            role=CompanyMembership.Role.FOUNDER,
        )

    def test_dashboard_renders_html_with_metrics(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertContains(response, 'ТестСтарт')

    def test_budget_and_expense_flow(self):
        budget = BudgetItem.objects.create(
            company=self.company,
            name='Облако',
            category=BudgetCategory.CLOUD,
            period='2026-Q4',
            planned_amount=Decimal('200000.00'),
        )
        resp = self.client.post(
            reverse('expense_create'),
            {
                'title': 'Серверы',
                'category': BudgetCategory.CLOUD,
                'budget_item': budget.id,
                'amount': '50000.00',
                'expense_date': '2026-11-15',
                'vendor': 'CloudHost',
                'status': Expense.Status.PAID,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Expense.objects.filter(company=self.company).count(), 1)

        csv_resp = self.client.get(reverse('expense_export_csv'))
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn('text/csv', csv_resp['Content-Type'])
        self.assertIn('Серверы', csv_resp.content.decode('utf-8-sig'))

    def test_venture_allocation_limit_validation(self):
        investor = Investor.objects.create(company=self.company, name='Фонд А')
        fr = FundingRound.objects.create(
            company=self.company,
            investor=investor,
            round_name='Seed',
            amount=Decimal('5000000.00'),
            equity_percent=Decimal('10.00'),
            status=FundingRound.Status.CLOSED,
        )
        # Attempt to allocate more than round amount -> form error (200)
        resp = self.client.post(
            reverse('allocation_create'),
            {
                'funding_round': fr.id,
                'bucket_name': 'R&D',
                'category': BudgetCategory.ENGINEERING,
                'allocated_amount': '6000000.00',
                'spent_amount': '0.00',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InvestmentAllocation.objects.count(), 0)

    def test_task_status_transition_and_kpi_checkin(self):
        emp = Employee.objects.create(
            company=self.company,
            full_name='Иван Петров',
            position='Backend Dev',
            monthly_salary=Decimal('200000.00'),
        )
        task = Task.objects.create(
            company=self.company,
            title='Настроить CI',
            assignee=emp,
            status=Task.Status.BACKLOG,
        )
        resp = self.client.post(
            reverse('task_change_status', args=[task.id]),
            {'status': Task.Status.DONE},
        )
        self.assertEqual(resp.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)

        kpi = KPIMetric.objects.create(
            company=self.company,
            name='MRR',
            unit='₽',
            current_value=Decimal('100000.00'),
            target_value=Decimal('500000.00'),
        )
        resp = self.client.post(
            reverse('kpi_detail', args=[kpi.id]),
            {'recorded_date': '2026-11-19', 'value': '250000.00', 'note': 'Новый клиент'},
        )
        self.assertEqual(resp.status_code, 302)
        kpi.refresh_from_db()
        self.assertEqual(kpi.current_value, Decimal('250000.00'))
        self.assertEqual(kpi.progress_percent, 50.0)


class EmailAuthFlowTests(TestCase):
    def test_full_email_registration_verification_and_login(self):
        from datetime import timedelta
        from django.core import mail
        from django.utils import timezone
        from .models import EmailVerificationCode

        email = 'Founder.New@Startup.RU'
        normalized = 'founder.new@startup.ru'

        # 1. Register by email -> inactive user + verification code in DB + email sent
        resp = self.client.post(
            reverse('register'),
            {
                'email': email,
                'first_name': 'Мария',
                'last_name': 'Орлова',
                'password1': 'StrongPass2026!',
                'password2': 'StrongPass2026!',
            },
        )
        self.assertRedirects(resp, reverse('verify_email'))

        user = User.objects.get(email=normalized)
        self.assertFalse(user.is_active)

        code_obj = EmailVerificationCode.objects.get(user=user, is_used=False)
        self.assertEqual(len(code_obj.code), 6)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [normalized])
        self.assertIn(code_obj.code, mail.outbox[0].body)

        # 2. Unverified account cannot log in -> redirected to verify_email
        login_unverified = self.client.post(
            reverse('login'),
            {'email': normalized, 'password': 'StrongPass2026!'},
        )
        self.assertRedirects(login_unverified, reverse('verify_email'))

        # 3. Wrong code increments attempts and stays on verify page
        wrong_code = '000000' if code_obj.code != '000000' else '111111'
        bad_verify = self.client.post(
            reverse('verify_email'),
            {'email': normalized, 'code': wrong_code},
        )
        self.assertEqual(bad_verify.status_code, 200)
        code_obj.refresh_from_db()
        self.assertEqual(code_obj.attempts, 1)
        self.assertFalse(code_obj.is_used)

        # 4. Resend after cooldown invalidates old code and mails a new code
        EmailVerificationCode.objects.filter(pk=code_obj.pk).update(
            created_at=timezone.now() - timedelta(seconds=45)
        )
        resend_resp = self.client.post(
            reverse('resend_verification_code'),
            {'email': normalized},
        )
        self.assertRedirects(resend_resp, reverse('verify_email'))
        code_obj.refresh_from_db()
        self.assertTrue(code_obj.is_used)

        new_code_obj = EmailVerificationCode.objects.get(user=user, is_used=False)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(new_code_obj.code, mail.outbox[1].body)

        # 5. Confirm with valid code -> activates user in DB and logs in
        ok_verify = self.client.post(
            reverse('verify_email'),
            {'email': normalized, 'code': new_code_obj.code},
        )
        self.assertRedirects(ok_verify, reverse('company_create'))
        user.refresh_from_db()
        new_code_obj.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(new_code_obj.is_used)

        # 6. Logout and sign in again strictly by Email + Password (case-insensitive)
        self.client.logout()
        login_ok = self.client.post(
            reverse('login'),
            {'email': 'FOUNDER.NEW@startup.ru', 'password': 'StrongPass2026!'},
        )
        self.assertRedirects(login_ok, reverse('dashboard'), fetch_redirect_response=False)

        # 7. Duplicate registration on active email is rejected
        self.client.logout()
        dup_resp = self.client.post(
            reverse('register'),
            {
                'email': normalized,
                'first_name': 'Другая',
                'last_name': '',
                'password1': 'AnotherPass2026!',
                'password2': 'AnotherPass2026!',
            },
        )
        self.assertEqual(dup_resp.status_code, 200)
        self.assertContains(dup_resp, 'уже зарегистрирован')

