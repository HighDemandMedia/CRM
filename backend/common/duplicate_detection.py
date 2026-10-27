"""
Duplicate detection service for CRM entities.

Provides methods to find potential duplicate records based on
email, phone, name, and other identifying fields.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accounts.models import Account
    from contacts.models import Contact
    from leads.models import Lead


class DuplicateDetector:
    """Service for detecting potential duplicate records."""

    @staticmethod
    def normalize_phone(phone: str) -> str:
        from common.validators import normalize_phone

        return normalize_phone(phone)

    @staticmethod
    def normalize_domain(website: str) -> str:
        """Extract and normalize domain from a website URL."""
        from common.record_identity import company_domain

        return company_domain(website)

    @classmethod
    def find_duplicate_contacts(
        cls,
        org,
        email: str | None = None,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        exclude_id=None,
    ) -> list["Contact"]:
        """
        Find potential duplicate contacts based on email or phone.

        Args:
            org: The organization to search within
            email: Email address to match
            phone: Phone number to match (normalized)
            first_name: First name for fuzzy matching
            last_name: Last name for fuzzy matching
            exclude_id: ID to exclude from results (for updates)

        Returns:
            List of potential duplicate Contact objects
        """
        from contacts.models import Contact

        duplicates = []
        base_qs = Contact.objects.filter(org=org, is_active=True)

        if exclude_id:
            base_qs = base_qs.exclude(pk=exclude_id)

        # Exact email match (case-insensitive)
        if email:
            email_matches = base_qs.filter(email__iexact=email)
            duplicates.extend(list(email_matches))

        # Normalized phone match
        if phone:
            normalized = cls.normalize_phone(phone)
            if len(normalized) >= 7:
                # Get all contacts with phones and filter in Python
                phone_candidates = base_qs.exclude(phone__isnull=True).exclude(phone="")
                for contact in phone_candidates:
                    if cls.normalize_phone(contact.phone) == normalized:
                        if contact not in duplicates:
                            duplicates.append(contact)

        return duplicates

    @classmethod
    def find_duplicate_leads(
        cls,
        org,
        email: str | None = None,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        exclude_id=None,
    ) -> list["Lead"]:
        """
        Find potential duplicate leads based on email, phone, name, or company.

        Args:
            org: The organization to search within
            email: Email address to match
            phone: Phone number to match (normalized)
            first_name: First name for fuzzy matching
            last_name: Last name for fuzzy matching
            company_name: Company name for fuzzy matching
            exclude_id: ID to exclude from results (for updates)

        Returns:
            List of potential duplicate Lead objects
        """
        from leads.models import Lead

        duplicates = []
        base_qs = Lead.objects.filter(org=org, is_active=True)

        if exclude_id:
            base_qs = base_qs.exclude(pk=exclude_id)

        # Exact email match (case-insensitive)
        if email:
            email_matches = base_qs.filter(email__iexact=email)
            duplicates.extend(list(email_matches))

        # Normalized phone match
        if phone:
            normalized = cls.normalize_phone(phone)
            if len(normalized) >= 7:
                phone_candidates = base_qs.exclude(phone__isnull=True).exclude(phone="")
                for lead in phone_candidates:
                    if cls.normalize_phone(lead.phone) == normalized:
                        if lead not in duplicates:
                            duplicates.append(lead)

        # Name match
        if first_name and last_name:
            name_matches = base_qs.filter(
                first_name__iexact=first_name, last_name__iexact=last_name
            )
            for lead in name_matches:
                if lead not in duplicates:
                    duplicates.append(lead)

        # Company name match (fuzzy - contains)
        if company_name and len(company_name) >= 3:
            company_matches = base_qs.filter(company_name__icontains=company_name)
            for lead in company_matches:
                if lead not in duplicates:
                    duplicates.append(lead)

        return duplicates

    @classmethod
    def find_duplicate_accounts(
        cls,
        org,
        name: str | None = None,
        email: str | None = None,
        website: str | None = None,
        phone: str | None = None,
        exclude_id=None,
    ) -> list["Account"]:
        """
        Find potential duplicate accounts based on the website domain.

        Args:
            org: The organization to search within
            name: Account name to match (fuzzy)
            email: Email address to match
            website: Website URL to match (domain normalized)
            phone: Phone number to match (normalized)
            exclude_id: ID to exclude from results (for updates)

        Returns:
            List of potential duplicate Account objects
        """
        from accounts.models import Account

        base_qs = Account.objects.filter(org=org, is_active=True)

        if exclude_id:
            base_qs = base_qs.exclude(pk=exclude_id)

        domain = cls.normalize_domain(website)
        return list(base_qs.filter(domain_match_key=domain)) if domain else []
