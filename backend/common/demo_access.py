"""Customer demo visibility. Existing record permissions still apply."""
HIDDEN_API_MODULES = (
    'leads', 'invoices', 'estimates', 'recurring-invoices', 'solutions',
    'documents', 'timesheets', 'timesheet', 'goals', 'sales-goals',
    'products', 'packs', 'api-settings', 'webforms', 'knowledge-base',
    'cases/solutions', 'time-entries', 'business-hours', 'macros',
)


def unavailable_in_demo(path):
    return any(path == '/api/' + module or path.startswith('/api/' + module + '/')
               for module in HIDDEN_API_MODULES)
