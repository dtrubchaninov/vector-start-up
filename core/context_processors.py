"""Template context processor exposing the active company and user's company list."""

from .models import Company


def active_company_context(request):
    if not request.user.is_authenticated:
        return {
            'user_companies': [],
            'active_company': None,
        }

    companies = list(
        Company.objects.filter(memberships__user=request.user)
        .distinct()
        .order_by('name')
    )
    active_id = request.session.get('active_company_id')
    active_company = next((c for c in companies if c.id == active_id), None)

    if active_company is None and companies:
        active_company = companies[0]
        request.session['active_company_id'] = active_company.id

    return {
        'user_companies': companies,
        'active_company': active_company,
    }
