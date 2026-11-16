"""URL routing for core application (100% pure Django SSR HTML routes, zero JS)."""

from django.urls import path

from . import views, views_growth

urlpatterns = [
    # Auth
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.UserLogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register_view, name='register'),
    path('accounts/verify-email/', views.verify_email_view, name='verify_email'),
    path('accounts/verify-email/resend/', views.resend_verification_code_view, name='resend_verification_code'),

    # Dashboard & Global Search & Investor Report
    path('', views.dashboard_view, name='dashboard'),
    path('search/', views_growth.global_search_view, name='global_search'),
    path('investor-report/', views_growth.investor_report_view, name='investor_report'),

    # Financial Model & Runway Simulator + SaaS Unit Economics
    path('simulator/', views_growth.finance_simulator_view, name='finance_simulator'),

    # B2B Sales CRM Pipeline
    path('sales/', views_growth.sales_pipeline_view, name='sales_pipeline'),
    path('sales/new/', views_growth.deal_create, name='deal_create'),
    path('sales/export-csv/', views_growth.deal_export_csv, name='deal_export_csv'),
    path('sales/<int:pk>/edit/', views_growth.deal_edit, name='deal_edit'),
    path('sales/<int:pk>/stage/', views_growth.deal_change_stage, name='deal_change_stage'),
    path('sales/<int:pk>/delete/', views_growth.deal_delete, name='deal_delete'),

    # Invoices & Receivables
    path('invoices/', views_growth.invoice_list, name='invoice_list'),
    path('invoices/new/', views_growth.invoice_create, name='invoice_create'),
    path('invoices/export-csv/', views_growth.invoice_export_csv, name='invoice_export_csv'),
    path('invoices/<int:pk>/edit/', views_growth.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/mark-paid/', views_growth.invoice_mark_paid, name='invoice_mark_paid'),
    path('invoices/<int:pk>/download/', views_growth.invoice_download_doc, name='invoice_download_doc'),
    path('invoices/<int:pk>/delete/', views_growth.invoice_delete, name='invoice_delete'),

    # Quarterly Roadmap & Checklists
    path('roadmap/', views_growth.roadmap_list, name='roadmap_list'),
    path('roadmap/new/', views_growth.milestone_create, name='milestone_create'),
    path('roadmap/<int:pk>/edit/', views_growth.milestone_edit, name='milestone_edit'),
    path('roadmap/<int:pk>/status/', views_growth.milestone_status, name='milestone_status'),
    path('roadmap/<int:pk>/delete/', views_growth.milestone_delete, name='milestone_delete'),
    path('roadmap/<int:pk>/check-add/', views_growth.milestone_check_add, name='milestone_check_add'),
    path('roadmap/check/<int:pk>/toggle/', views_growth.milestone_check_toggle, name='milestone_check_toggle'),

    # Cap Table, Vesting & Round Dilution Simulator
    path('cap-table/', views_growth.cap_table_view, name='cap_table'),
    path('cap-table/new/', views_growth.equity_holder_create, name='equity_holder_create'),
    path('cap-table/<int:pk>/edit/', views_growth.equity_holder_edit, name='equity_holder_edit'),
    path('cap-table/<int:pk>/delete/', views_growth.equity_holder_delete, name='equity_holder_delete'),

    # Growth Experiments (ICE Scoring)
    path('experiments/', views_growth.experiment_list, name='experiment_list'),
    path('experiments/new/', views_growth.experiment_create, name='experiment_create'),
    path('experiments/<int:pk>/edit/', views_growth.experiment_edit, name='experiment_edit'),
    path('experiments/<int:pk>/status/', views_growth.experiment_status, name='experiment_status'),
    path('experiments/<int:pk>/delete/', views_growth.experiment_delete, name='experiment_delete'),

    # Investor Data Room
    path('data-room/', views_growth.data_room_list, name='data_room_list'),
    path('data-room/new/', views_growth.data_room_create, name='data_room_create'),
    path('data-room/<int:pk>/edit/', views_growth.data_room_edit, name='data_room_edit'),
    path('data-room/<int:pk>/status/', views_growth.data_room_status, name='data_room_status'),
    path('data-room/<int:pk>/delete/', views_growth.data_room_delete, name='data_room_delete'),

    # Companies
    path('companies/', views.company_list, name='company_list'),
    path('companies/new/', views.company_create, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    path('companies/<int:pk>/switch/', views.company_switch, name='company_switch'),
    path('companies/<int:pk>/delete/', views.company_delete, name='company_delete'),

    # Budgets
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/new/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/export-csv/', views.expense_export_csv, name='expense_export_csv'),
    path('expenses/new/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/mark-paid/', views.expense_mark_paid, name='expense_mark_paid'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Ventures, Investors & Allocations
    path('ventures/', views.ventures_overview, name='ventures_overview'),
    path('ventures/investors/new/', views.investor_create, name='investor_create'),
    path('ventures/investors/<int:pk>/edit/', views.investor_edit, name='investor_edit'),
    path('ventures/investors/<int:pk>/delete/', views.investor_delete, name='investor_delete'),
    path('ventures/rounds/new/', views.round_create, name='round_create'),
    path('ventures/rounds/<int:pk>/edit/', views.round_edit, name='round_edit'),
    path('ventures/rounds/<int:pk>/delete/', views.round_delete, name='round_delete'),
    path('ventures/allocations/new/', views.allocation_create, name='allocation_create'),
    path('ventures/allocations/<int:pk>/edit/', views.allocation_edit, name='allocation_edit'),
    path('ventures/allocations/<int:pk>/delete/', views.allocation_delete, name='allocation_delete'),

    # Team & Employees
    path('team/', views.employee_list, name='employee_list'),
    path('team/new/', views.employee_create, name='employee_create'),
    path('team/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('team/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('team/<int:pk>/delete/', views.employee_delete, name='employee_delete'),

    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/status/', views.task_change_status, name='task_change_status'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),

    # KPIs
    path('kpis/', views.kpi_list, name='kpi_list'),
    path('kpis/new/', views.kpi_create, name='kpi_create'),
    path('kpis/<int:pk>/', views.kpi_detail, name='kpi_detail'),
    path('kpis/<int:pk>/edit/', views.kpi_edit, name='kpi_edit'),
    path('kpis/<int:pk>/delete/', views.kpi_delete, name='kpi_delete'),
]
