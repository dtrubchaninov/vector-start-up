"""Django ModelForms with server-side validation and consistent CSS styling."""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import (
    BudgetItem,
    Company,
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
    RoadmapMilestone,
    Task,
    TaskComment,
    UnitEconomicsProfile,
)

User = get_user_model()


class StyledFormMixin:
    """Applies clean semantic CSS classes to every form field automatically."""

    def _apply_field_classes(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-checkbox'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = 'form-select'
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = 'form-textarea'
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs['class'] = 'form-input'


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'founder@startup.ru'}),
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=80,
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'given-name', 'placeholder': 'Алексей'}),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'family-name', 'placeholder': 'Соколов'}),
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()

    def clean_email(self) -> str:
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                'Аккаунт с такой почтой уже зарегистрирован. Войдите по email и паролю.'
            )
        return email

    @staticmethod
    def _build_unique_username(email: str) -> str:
        base = email[:140]
        candidate = base
        counter = 1
        while User.objects.filter(username__iexact=candidate).exists():
            suffix = f'_{counter}'
            candidate = f'{base[: 150 - len(suffix)]}{suffix}'
            counter += 1
        return candidate

    def save(self, commit: bool = True):
        email = self.cleaned_data['email']
        first_name = self.cleaned_data['first_name'].strip()
        last_name = self.cleaned_data.get('last_name', '').strip()
        password = self.cleaned_data['password1']

        existing_inactive = User.objects.filter(email__iexact=email, is_active=False).first()
        if existing_inactive is not None:
            user = existing_inactive
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = False
            user.set_password(password)
            if commit:
                user.save()
            return user

        user = super().save(commit=False)
        user.email = email
        user.username = self._build_unique_username(email)
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = False
        if commit:
            user.save()
        return user


class EmailLoginForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'founder@startup.ru'}),
    )
    password = forms.CharField(
        label='Пароль',
        required=True,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': '••••••••'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()

    def clean_email(self) -> str:
        return self.cleaned_data['email'].strip().lower()


class EmailVerificationForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'founder@startup.ru'}),
    )
    code = forms.CharField(
        label='Код подтверждения (6 цифр)',
        min_length=6,
        max_length=6,
        required=True,
        widget=forms.TextInput(
            attrs={
                'inputmode': 'numeric',
                'autocomplete': 'one-time-code',
                'placeholder': '000000',
                'maxlength': '6',
                'style': 'font-family: var(--font-mono); letter-spacing: 0.25em; font-size: 18px; text-align: center;',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()

    def clean_email(self) -> str:
        return self.cleaned_data['email'].strip().lower()

    def clean_code(self) -> str:
        raw = re.sub(r'\s+', '', self.cleaned_data['code'])
        if not re.fullmatch(r'\d{6}', raw):
            raise forms.ValidationError('Введите 6-значный цифровой код из письма.')
        return raw


class CompanyForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name',
            'legal_name',
            'industry',
            'stage',
            'currency',
            'founded_date',
            'initial_cash',
            'target_mrr',
            'website',
            'description',
        ]
        widgets = {
            'founded_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class BudgetItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = BudgetItem
        fields = ['name', 'category', 'period', 'planned_amount', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class ExpenseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'title',
            'category',
            'budget_item',
            'amount',
            'expense_date',
            'vendor',
            'status',
            'responsible',
            'is_recurring',
            'notes',
        ]
        widgets = {
            'expense_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['budget_item'].queryset = BudgetItem.objects.filter(company=company)
            self.fields['responsible'].queryset = Employee.objects.filter(company=company)
        self._apply_field_classes()


class InvestorForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Investor
        fields = ['name', 'investor_type', 'contact_name', 'email', 'website', 'typical_check', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class FundingRoundForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FundingRound
        fields = [
            'round_name',
            'stage',
            'investor',
            'amount',
            'equity_percent',
            'pre_money_valuation',
            'closed_date',
            'status',
            'notes',
        ]
        widgets = {
            'closed_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['investor'].queryset = Investor.objects.filter(company=company)
        self._apply_field_classes()


class InvestmentAllocationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = InvestmentAllocation
        fields = [
            'funding_round',
            'bucket_name',
            'category',
            'allocated_amount',
            'spent_amount',
            'target_milestone',
        ]

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['funding_round'].queryset = FundingRound.objects.filter(company=company)
        self._apply_field_classes()

    def clean(self):
        cleaned = super().clean()
        funding_round = cleaned.get('funding_round')
        allocated = cleaned.get('allocated_amount')
        spent = cleaned.get('spent_amount')
        if allocated and spent and spent > allocated:
            self.add_error('spent_amount', 'Освоенная сумма не может превышать выделенный лимит.')
        if funding_round and allocated:
            existing = funding_round.allocations.exclude(pk=self.instance.pk)
            total_other = sum(item.allocated_amount for item in existing)
            if total_other + allocated > funding_round.amount:
                self.add_error(
                    'allocated_amount',
                    f'Суммарное распределение превышает объём раунда ({funding_round.amount}).',
                )
        return cleaned


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'full_name',
            'position',
            'department',
            'email',
            'phone',
            'monthly_salary',
            'equity_options_pct',
            'status',
            'hired_at',
        ]
        widgets = {
            'hired_at': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class TaskForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'assignee',
            'priority',
            'status',
            'due_date',
            'milestone',
            'estimated_hours',
        ]
        widgets = {
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['assignee'].queryset = Employee.objects.filter(company=company)
        self._apply_field_classes()


class TaskCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Добавьте обновление по задаче...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class KPIMetricForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = KPIMetric
        fields = [
            'name',
            'category',
            'unit',
            'current_value',
            'target_value',
            'direction',
            'period_label',
            'owner',
            'description',
        ]

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['owner'].queryset = Employee.objects.filter(company=company)
        self._apply_field_classes()


class KPIEntryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = KPIEntry
        fields = ['recorded_date', 'value', 'note']
        widgets = {
            'recorded_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class DealForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Deal
        fields = [
            'client_name',
            'contact_name',
            'contact_email',
            'amount',
            'billing_type',
            'stage',
            'probability',
            'expected_close_date',
            'owner',
            'notes',
        ]
        widgets = {
            'expected_close_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['owner'].queryset = Employee.objects.filter(company=company)
        self._apply_field_classes()


class RoadmapMilestoneForm(StyledFormMixin, forms.ModelForm):
    initial_checklist = forms.CharField(
        label='Пункты чек-листа (каждый с новой строки)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Запустить пилот\nПодписать договор\nОбучить команду'}),
    )

    class Meta:
        model = RoadmapMilestone
        fields = ['title', 'quarter', 'category', 'status', 'due_date', 'owner', 'summary']
        widgets = {
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['owner'].queryset = Employee.objects.filter(company=company)
        if self.instance and self.instance.pk:
            self.fields['initial_checklist'].widget = forms.HiddenInput()
        self._apply_field_classes()


class UnitEconomicsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = UnitEconomicsProfile
        fields = [
            'arpu',
            'active_customers',
            'gross_margin_pct',
            'monthly_churn_pct',
            'cac',
            'monthly_growth_pct',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class InvoiceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_number',
            'client_name',
            'service_title',
            'amount',
            'vat_included',
            'issue_date',
            'due_date',
            'paid_date',
            'status',
        ]
        widgets = {
            'issue_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'paid_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class EquityHolderForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EquityHolder
        fields = ['name', 'role', 'ownership_pct', 'vesting_months', 'cliff_months', 'start_date', 'notes']
        widgets = {
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class GrowthExperimentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = GrowthExperiment
        fields = [
            'title',
            'hypothesis',
            'target_metric',
            'impact',
            'confidence',
            'ease',
            'status',
            'owner',
            'outcome_note',
        ]

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['owner'].queryset = Employee.objects.filter(company=company)
        self._apply_field_classes()


class DataRoomDocForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DataRoomDoc
        fields = [
            'title',
            'category',
            'access_level',
            'status',
            'version_label',
            'doc_url',
            'owner',
            'updated_at',
            'summary',
        ]
        widgets = {
            'updated_at': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields['owner'].queryset = Employee.objects.filter(company=company)
        self._apply_field_classes()

