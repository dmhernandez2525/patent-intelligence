from pydantic import BaseModel


class ExpiringPatentItem(BaseModel):
    patent_number: str
    title: str
    abstract: str | None = None
    expiration_date: str | None = None
    filing_date: str | None = None
    grant_date: str | None = None
    assignee_organization: str | None = None
    cpc_codes: list[str] | None = None
    country: str
    status: str
    days_until_expiration: int
    maintenance_fee_status: str
    next_fee_date: str | None = None
    next_fee_amount: float | None = None
    citation_count: int | None = None
    patent_type: str | None = None

    model_config = {"from_attributes": True}


class MaintenanceFeeItem(BaseModel):
    patent_number: str
    title: str
    assignee_organization: str | None = None
    fee_year: int
    due_date: str
    grace_period_end: str | None = None
    amount_usd: float | None = None
    days_until_due: int
    status: str


class ExpirationTimelineEntry(BaseModel):
    month: str
    count: int


class TopSectorEntry(BaseModel):
    cpc_code: str
    count: int


class ExpirationStatsResponse(BaseModel):
    expiring_30_days: int
    expiring_90_days: int
    expiring_180_days: int
    expiring_365_days: int
    recently_lapsed: int
    pending_maintenance_fees: int
    top_sectors: list[TopSectorEntry]
    monthly_timeline: list[ExpirationTimelineEntry]


class ExpirationListResponse(BaseModel):
    patents: list[ExpiringPatentItem]
    total: int
    page: int
    per_page: int


class MaintenanceFeeListResponse(BaseModel):
    fees: list[MaintenanceFeeItem]
    total: int
    page: int
    per_page: int


class ExpirationDashboardResponse(BaseModel):
    stats: ExpirationStatsResponse
    expiring_soon: list[ExpiringPatentItem]
    recently_lapsed: list[ExpiringPatentItem]
    upcoming_fees: list[MaintenanceFeeItem]
