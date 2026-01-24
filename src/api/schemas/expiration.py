from datetime import date

from pydantic import BaseModel


class ExpiringPatentItem(BaseModel):
    patent_number: str
    title: str
    expiration_date: date
    assignee_organization: str | None = None
    cpc_codes: list[str] | None = None
    days_until_expiration: int
    maintenance_fee_status: str | None = None

    model_config = {"from_attributes": True}


class ExpirationDashboardResponse(BaseModel):
    expiring_30_days: list[ExpiringPatentItem]
    expiring_90_days: list[ExpiringPatentItem]
    expiring_365_days: list[ExpiringPatentItem]
    recently_lapsed: list[ExpiringPatentItem]
    total_expiring_soon: int
