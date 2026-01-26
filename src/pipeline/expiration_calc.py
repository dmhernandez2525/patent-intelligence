from datetime import date, timedelta

# US Patent term: 20 years from earliest filing date (post-1995)
# Design patents: 15 years from grant date (post-2015)
# Plant patents: 20 years from filing date
STANDARD_TERM_YEARS = 20
DESIGN_TERM_YEARS = 15

# Maintenance fee windows for US utility patents
# Due at 3.5, 7.5, and 11.5 years after grant
MAINTENANCE_FEE_YEARS = [3.5, 7.5, 11.5]
GRACE_PERIOD_MONTHS = 6


def calculate_expiration_date(
    filing_date: date | None,
    grant_date: date | None,
    patent_type: str | None = None,
    pta_days: int = 0,
    pte_days: int = 0,
    terminal_disclaimer_date: date | None = None,
) -> date | None:
    """
    Calculate patent expiration date.

    For US utility patents (post-June 8, 1995):
    - 20 years from earliest filing date + PTA + PTE

    For US design patents (post-May 13, 2015):
    - 15 years from grant date

    For pre-1995 patents:
    - Later of: 17 years from grant OR 20 years from filing
    """
    if not filing_date and not grant_date:
        return None

    patent_type_lower = (patent_type or "").lower()

    if patent_type_lower in ("design", "des"):
        if not grant_date:
            return None
        return grant_date + timedelta(days=DESIGN_TERM_YEARS * 365)

    # Utility and plant patents: 20 years from filing
    if not filing_date:
        # Fallback: estimate filing from grant (average prosecution ~2-3 years)
        if grant_date:
            estimated_filing = grant_date - timedelta(days=3 * 365)
            base_expiration = estimated_filing + timedelta(days=STANDARD_TERM_YEARS * 365)
        else:
            return None
    else:
        base_expiration = filing_date + timedelta(days=STANDARD_TERM_YEARS * 365)

    # Add Patent Term Adjustment (PTA) - USPTO delays
    if pta_days > 0:
        base_expiration += timedelta(days=pta_days)

    # Add Patent Term Extension (PTE) - regulatory delays (pharma)
    if pte_days > 0:
        base_expiration += timedelta(days=pte_days)

    # Terminal disclaimer limits expiration to the disclaimered patent's date
    if terminal_disclaimer_date and terminal_disclaimer_date < base_expiration:
        return terminal_disclaimer_date

    return base_expiration


def calculate_maintenance_fee_dates(
    grant_date: date,
) -> list[dict]:
    """
    Calculate maintenance fee due dates for a US utility patent.

    Returns list of fee windows with due dates and grace period ends.
    """
    if not grant_date:
        return []

    fees = []
    for year_offset in MAINTENANCE_FEE_YEARS:
        due_date = grant_date + timedelta(days=int(year_offset * 365.25))
        grace_end = due_date + timedelta(days=int(GRACE_PERIOD_MONTHS * 30.44))

        fee_year = int(year_offset)
        label = f"Year {fee_year}"
        if year_offset == 3.5:
            label = "3.5 Year"
        elif year_offset == 7.5:
            label = "7.5 Year"
        elif year_offset == 11.5:
            label = "11.5 Year"

        fees.append({
            "fee_year": fee_year,
            "label": label,
            "due_date": due_date,
            "grace_period_end": grace_end,
            "window_open": due_date - timedelta(days=180),  # Can pay 6 months early
        })

    return fees


def determine_patent_status(
    expiration_date: date | None,
    maintenance_fees_paid: list[int] | None = None,
    grant_date: date | None = None,
) -> str:
    """
    Determine current patent status based on expiration and maintenance fees.

    Returns: 'active', 'expired', 'lapsed', or 'unknown'
    """
    if not expiration_date:
        return "unknown"

    today = date.today()

    # Check if past expiration date
    if today > expiration_date:
        return "expired"

    # Check maintenance fee status
    if grant_date and maintenance_fees_paid is not None:
        fee_schedule = calculate_maintenance_fee_dates(grant_date)
        for fee in fee_schedule:
            # If past grace period and fee not paid, patent has lapsed
            if today > fee["grace_period_end"]:
                if fee["fee_year"] not in maintenance_fees_paid:
                    return "lapsed"

    return "active"


def days_until_expiration(expiration_date: date | None) -> int | None:
    """Calculate days until patent expiration."""
    if not expiration_date:
        return None
    delta = expiration_date - date.today()
    return delta.days
