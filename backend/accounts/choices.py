from common.utils import INDCHOICES

COMPANY_INDUSTRIES = (
    ("AGRICULTURE", "Agriculture"),
    ("AUTOMOTIVE", "Automotive"),
    ("BEAUTY & PERSONAL CARE", "Beauty & Personal Care"),
    ("CONSTRUCTION", "Construction"),
    ("EDUCATION", "Education"),
    ("ENERGY & UTILITIES", "Energy & Utilities"),
    ("FINANCE & INSURANCE", "Finance & Insurance"),
    ("FOOD & BEVERAGE", "Food & Beverage"),
    ("HEALTHCARE", "Healthcare"),
    ("HOME IMPROVEMENT", "Home Improvement"),
    ("HOSPITALITY & TOURISM", "Hospitality & Tourism"),
    ("MANUFACTURING", "Manufacturing"),
    ("MEDIA & ENTERTAINMENT", "Media & Entertainment"),
    ("NONPROFIT", "Nonprofit"),
    ("PROFESSIONAL SERVICES", "Professional Services"),
    ("REAL ESTATE", "Real Estate"),
    ("RETAIL & E-COMMERCE", "Retail & E-commerce"),
    ("HOME & LOCAL SERVICES", "Home & Local Services"),
    ("TECHNOLOGY", "Technology"),
    ("TRANSPORTATION & LOGISTICS", "Transportation & Logistics"),
    ("WHOLESALE & DISTRIBUTION", "Wholesale & Distribution"),
    ("OTHER", "Other"),
)

# Keep existing values valid without offering narrow legacy categories on new forms.
ACCOUNT_INDUSTRIES = COMPANY_INDUSTRIES + tuple(
    (value, label.title())
    for value, label in INDCHOICES
    if value not in dict(COMPANY_INDUSTRIES)
)
