from django.contrib import admin

from .models import (
    ActivityLog,
    BudgetItem,
    Company,
    CompanyMembership,
    DataRoomDoc,
    Deal,
    EmailVerificationCode,
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


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'code', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_used',)
    search_fields = ('email', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'stage', 'currency', 'initial_cash', 'founded_date')
    list_filter = ('stage', 'currency')
    search_fields = ('name', 'legal_name', 'industry')


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'role', 'joined_at')
    list_filter = ('role',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'department', 'company', 'monthly_salary', 'equity_options_pct', 'status')
    list_filter = ('department', 'status', 'company')
    search_fields = ('full_name', 'position', 'email')


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'category', 'period', 'planned_amount')
    list_filter = ('category', 'period', 'company')
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'category', 'amount', 'expense_date', 'status', 'vendor')
    list_filter = ('status', 'category', 'is_recurring', 'company')
    search_fields = ('title', 'vendor')
    date_hierarchy = 'expense_date'


@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ('name', 'investor_type', 'company', 'contact_name', 'typical_check')
    list_filter = ('investor_type', 'company')
    search_fields = ('name', 'contact_name')


@admin.register(FundingRound)
class FundingRoundAdmin(admin.ModelAdmin):
    list_display = ('round_name', 'company', 'investor', 'stage', 'amount', 'equity_percent', 'status', 'closed_date')
    list_filter = ('status', 'stage', 'company')


@admin.register(InvestmentAllocation)
class InvestmentAllocationAdmin(admin.ModelAdmin):
    list_display = ('bucket_name', 'funding_round', 'category', 'allocated_amount', 'spent_amount')
    list_filter = ('category', 'company')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'assignee', 'priority', 'status', 'due_date')
    list_filter = ('status', 'priority', 'company')
    search_fields = ('title', 'milestone')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')


@admin.register(KPIMetric)
class KPIMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'category', 'current_value', 'target_value', 'unit', 'period_label')
    list_filter = ('category', 'company')


@admin.register(KPIEntry)
class KPIEntryAdmin(admin.ModelAdmin):
    list_display = ('metric', 'recorded_date', 'value', 'note')
    date_hierarchy = 'recorded_date'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'company', 'action_type', 'summary', 'actor')
    list_filter = ('action_type', 'company')


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'company', 'stage', 'amount', 'billing_type', 'probability', 'expected_close_date')
    list_filter = ('stage', 'billing_type', 'company')
    search_fields = ('client_name', 'contact_name')


@admin.register(RoadmapMilestone)
class RoadmapMilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'quarter', 'category', 'status', 'due_date')
    list_filter = ('quarter', 'category', 'status', 'company')


@admin.register(MilestoneCheckItem)
class MilestoneCheckItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'milestone', 'is_done')
    list_filter = ('is_done',)


@admin.register(UnitEconomicsProfile)
class UnitEconomicsProfileAdmin(admin.ModelAdmin):
    list_display = ('company', 'arpu', 'active_customers', 'gross_margin_pct', 'monthly_churn_pct', 'cac')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client_name', 'company', 'amount', 'status', 'issue_date', 'due_date')
    list_filter = ('status', 'vat_included', 'company')
    search_fields = ('invoice_number', 'client_name', 'service_title')


@admin.register(EquityHolder)
class EquityHolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'role', 'ownership_pct', 'vesting_months', 'cliff_months')
    list_filter = ('role', 'company')


@admin.register(GrowthExperiment)
class GrowthExperimentAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'status', 'impact', 'confidence', 'ease', 'owner')
    list_filter = ('status', 'company')


@admin.register(DataRoomDoc)
class DataRoomDocAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'category', 'access_level', 'status', 'version_label', 'updated_at')
    list_filter = ('category', 'access_level', 'status', 'company')

