"""
Sympl Solutions Proposal RAG — Commercial Terms & Pricing Placeholder Handler

Enforces:
  1. Gate A Commercial Rule: Pricing categories must ONLY appear from approved commercial inputs.
  2. Never invent amounts, fee categories, tax treatments, or billing commitments.
  3. Structured placeholder generation when commercial terms are pending.
  4. Attachment of approved conditional disclaimer reference blocks (Backlog, Software, HR Boundary).
"""

from typing import List, Dict, Any, Tuple
from .schema import ClientInput, ApprovedCommercialInputs


class PricingHandler:
    """
    Handles commercial fee category compilation, placeholder formatting, and conditional exclusion notes.
    """

    DISCLAIMER_BLOCKS = {
        "REF_BLOCK_EXCLUSIONS_BACKLOG": {
            "block_key": "REF_BLOCK_EXCLUSIONS_BACKLOG",
            "classification": "CONDITIONAL",
            "render_as": "note",
            "content": "Bookkeeping backlog: Any prior period bookkeeping clean-up or catch-up work will be quoted separately based on the volume and complexity"
        },
        "REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED": {
            "block_key": "REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED",
            "classification": "CONDITIONAL",
            "render_as": "note",
            "content": "Note: Above costs do not include software subscription fees."
        },
        "REF_BLOCK_PAYROLL_HR_BOUNDARY": {
            "block_key": "REF_BLOCK_PAYROLL_HR_BOUNDARY",
            "classification": "CONDITIONAL",
            "render_as": "note",
            "content": "Note: While we manage all payroll accounting and processing, managers must provide timely payroll data (e.g., timesheets, new hires, exits). We do not manage HR functions."
        }
    }

    @classmethod
    def compile_commercial_schedule(cls, client_input: ClientInput) -> Dict[str, Any]:
        """
        Compiles approved fee categories or structured placeholders.
        Emits only categories derived from approved commercial inputs.
        """
        comm = client_input.commercial_terms
        app_scope = client_input.approved_scope
        currency = comm.currency or "CAD"

        fee_items: List[Dict[str, Any]] = []
        is_placeholder = False

        # 1. Monthly Retainer
        if comm.monthly_retainer is not None:
            fee_items.append({
                "category": "Monthly Recurring Retainer",
                "amount": comm.monthly_retainer,
                "currency": currency,
                "billing_frequency": "monthly",
                "description": "Comprehensive recurring accounting, general ledger, and financial operations as scoped.",
                "is_placeholder": False
            })
        elif "monthly_retainer" in comm.approved_categories or comm.pricing_model == "placeholder":
            fee_items.append({
                "category": "Monthly Recurring Retainer",
                "amount": None,
                "currency": currency,
                "placeholder_token": f"[PRICING_PLACEHOLDER: Monthly Retainer Fee ({currency})]",
                "billing_frequency": "monthly",
                "description": "Monthly recurring accounting fee to be confirmed upon final scope sign-off.",
                "is_placeholder": True
            })
            is_placeholder = True

        # 2. One-Time Onboarding / Setup Fee
        if comm.setup_fee is not None:
            fee_items.append({
                "category": "System Onboarding & Setup Fee",
                "amount": comm.setup_fee,
                "currency": currency,
                "billing_frequency": "one_time",
                "description": "Initial chart of accounts review, historical data ingestion, and workflow setup.",
                "is_placeholder": False
            })
        elif "setup_fee" in comm.approved_categories:
            fee_items.append({
                "category": "System Onboarding & Setup Fee",
                "amount": None,
                "currency": currency,
                "placeholder_token": f"[PRICING_PLACEHOLDER: One-Time Onboarding & System Setup Fee ({currency})]",
                "billing_frequency": "one_time",
                "description": "One-time onboarding and setup fee to be confirmed.",
                "is_placeholder": True
            })
            is_placeholder = True

        # 3. Hourly Rate (Out of Scope / Special Advisory)
        if comm.hourly_rate is not None:
            fee_items.append({
                "category": "Out-of-Scope Hourly Advisory",
                "amount": comm.hourly_rate,
                "currency": currency,
                "billing_frequency": "hourly",
                "description": "Hourly rate for pre-approved ad-hoc reporting or out-of-scope advisory tasks.",
                "is_placeholder": False
            })
        elif "hourly_rate" in comm.approved_categories:
            fee_items.append({
                "category": "Out-of-Scope Hourly Advisory",
                "amount": None,
                "currency": currency,
                "placeholder_token": f"[PRICING_PLACEHOLDER: Hourly Out-of-Scope Advisory Rate ({currency})]",
                "billing_frequency": "hourly",
                "description": "Hourly rate for ad-hoc requests to be confirmed.",
                "is_placeholder": True
            })
            is_placeholder = True

        # If zero categories were specified at all, supply the single base monthly retainer placeholder
        if not fee_items:
            fee_items.append({
                "category": "Monthly Recurring Retainer",
                "amount": None,
                "currency": currency,
                "placeholder_token": f"[PRICING_PLACEHOLDER: Monthly Retainer Fee ({currency})]",
                "billing_frequency": "monthly",
                "description": "Commercial fee schedule pending leadership approval.",
                "is_placeholder": True
            })
            is_placeholder = True

        # --------------------------------------------------------------
        # Compile Conditional Disclaimers & Notes
        # --------------------------------------------------------------
        disclaimers: List[Dict[str, Any]] = []

        # Backlog clean-up exclusion
        if comm.include_backlog_exclusion:
            disclaimers.append(cls.DISCLAIMER_BLOCKS["REF_BLOCK_EXCLUSIONS_BACKLOG"])

        # Software subscription pass-through note
        if comm.software_fees_excluded:
            disclaimers.append(cls.DISCLAIMER_BLOCKS["REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED"])

        # Payroll HR boundary note
        if (
            app_scope.payroll is not None and
            app_scope.payroll.sympl_processes_payroll and
            app_scope.payroll.manager_input_responsibility and
            app_scope.payroll.hr_functions_excluded
        ):
            disclaimers.append(cls.DISCLAIMER_BLOCKS["REF_BLOCK_PAYROLL_HR_BOUNDARY"])

        return {
            "pricing_model": comm.pricing_model,
            "currency": currency,
            "billing_schedule": comm.billing_schedule or "Invoiced at the beginning of each service month.",
            "fee_items": fee_items,
            "has_placeholders": is_placeholder,
            "disclaimers": disclaimers
        }
