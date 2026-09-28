"""Customer demo visibility. Existing record permissions still apply."""
HIDDEN_API_MODULES = (
    'leads', 'invoices', 'estimates', 'recurring-invoices', 'solutions',
    'documents', 'timesheets', 'timesheet', 'goals', 'sales-goals',
    'products', 'packs', 'api-settings', 'webforms', 'knowledge-base',
    'cases/solutions', 'time-entries', 'business-hours', 'macros',
    'cases/routing-rules', 'cases/escalation-policies', 'cases/reopen-policy',
    'cases/approval-rules', 'cases/mailboxes', 'org/api-key', 'org/tokens',
    'profile/tokens',
)


def unavailable_in_demo(path):
    return any(path == '/api/' + module or path.startswith('/api/' + module + '/')
               for module in HIDDEN_API_MODULES)
