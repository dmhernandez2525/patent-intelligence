# Phase 4: Expiration Intelligence - Software Design Document

## Overview

The Expiration Intelligence module provides comprehensive patent expiration tracking, maintenance fee monitoring, and lapsed patent opportunity discovery. It enables users to identify patents approaching expiration, track fee payment deadlines, and discover lapsed patents for potential licensing or freedom-to-operate analysis.

## Architecture

```
Frontend (ExpirationPage)
    |
    v
GET /api/expiration/{dashboard|upcoming|lapsed|maintenance-fees|stats}
    |
    v
ExpirationService
    |
    +-- get_expiring_patents()      --> Patents with upcoming expiration dates
    +-- get_lapsed_patents()        --> Recently expired/lapsed patents
    +-- get_upcoming_maintenance_fees() --> Fee deadlines within time window
    +-- get_expiration_stats()      --> Aggregate statistics and timeline
    |
    v
Patent + MaintenanceFee models (PostgreSQL)
```

## Components

### 1. Expiration Service (`src/services/expiration_service.py`)

#### ExpirationService

Singleton service providing expiration data access:

**get_expiring_patents(days, country, cpc_code, assignee, page, per_page)**
- Queries active patents with expiration dates within the specified window
- Supports filtering by country, CPC code, and assignee
- Returns patents ordered by expiration date (soonest first)
- Includes maintenance fee status computed from related MaintenanceFee records

**get_lapsed_patents(days_back, country, cpc_code, assignee, page, per_page)**
- Queries patents with status "lapsed" or "expired" within the lookback window
- Identifies patents that lapsed due to non-payment of maintenance fees
- Ordered by expiration date (most recent first)

**get_upcoming_maintenance_fees(days, page, per_page)**
- Joins MaintenanceFee with Patent to show upcoming fee deadlines
- Filters to pending fees within the time window
- Includes fee amount, grace period end date, and days until due

**get_expiration_stats(country)**
- Aggregates expiration counts by time window (30d, 90d, 180d, 365d)
- Counts recently lapsed patents and pending maintenance fees
- Computes top CPC sectors with expiring patents
- Builds 12-month expiration timeline for visualization

**Maintenance Fee Status Logic:**
- `overdue`: Pending fee with due_date in the past
- `due_soon`: Next pending fee due within 90 days
- `current`: Next pending fee due > 90 days away
- `all_paid`: All fees have status "paid"
- `no_fees`: No maintenance fee records

### 2. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/expiration/dashboard` | GET | Combined dashboard data (stats + previews) |
| `/api/expiration/upcoming` | GET | Paginated list of expiring patents |
| `/api/expiration/lapsed` | GET | Paginated list of lapsed patents |
| `/api/expiration/maintenance-fees` | GET | Upcoming fee deadlines |
| `/api/expiration/stats` | GET | Aggregate statistics |

**Common Query Parameters:**
- `country` - Filter by country code
- `cpc_code` - Filter by CPC classification
- `assignee` - Filter by assignee (partial match)
- `days` / `days_back` - Time window
- `page`, `per_page` - Pagination

### 3. Response Schemas

**ExpiringPatentItem:** Full patent details plus:
- `days_until_expiration` - Computed countdown
- `maintenance_fee_status` - Current fee status
- `next_fee_date` / `next_fee_amount` - Next upcoming fee

**MaintenanceFeeItem:** Fee details plus:
- `days_until_due` - Days until fee deadline
- `grace_period_end` - End of grace period

**ExpirationStatsResponse:**
- Window counts (30d, 90d, 180d, 365d)
- `top_sectors` - CPC codes with most expiring patents
- `monthly_timeline` - 12-month expiration counts for charting

### 4. Frontend (`frontend/src/pages/ExpirationPage.tsx`)

**Tabs:**
- **Overview** - Stats cards, bar chart timeline, top sectors, previews
- **Expiring Soon** - Filterable paginated list with urgency indicators
- **Lapsed** - Recently lapsed patents with opportunity indicators
- **Maintenance Fees** - Fee deadline table

**Components:**
- `StatCard` - Colored stat card with icon
- `FilterBar` - Country/CPC/assignee/time window filters
- `PatentList` - Paginated patent cards with expiration countdown
- `ExpirationCard` - Patent card with fee status badges and countdown
- `FeesList` - Maintenance fee deadline table

**Visual Indicators:**
- Red: Expiring in ≤30 days or overdue fees
- Orange: Expiring in ≤90 days or fees due soon
- Yellow: Expiring in >90 days
- Green: Current/all-paid fee status

## Design Decisions

1. **Separate service layer**: ExpirationService is decoupled from the route layer for testability and reuse.

2. **Eager-load maintenance fees**: Uses SQLAlchemy `selectinload` to avoid N+1 queries when computing fee status.

3. **Dashboard endpoint combines calls**: Single endpoint reduces frontend round-trips for the overview tab.

4. **12-month timeline**: Provides actionable forward-looking view without overwhelming data.

5. **Fee status computed at query time**: Avoids stale cached status; fees are always evaluated against current date.

## Performance Considerations

- `expiration_date` is indexed for range queries
- `maintenance_fees.due_date` and `maintenance_fees.status` are indexed
- Dashboard stats use COUNT queries (no full row loads)
- Timeline uses 12 individual COUNT queries (bounded, cacheable)
- Pagination prevents large result sets

## Business Value

- 50% of US patents lapse due to non-payment of maintenance fees
- Early detection of expiring patents enables:
  - Freedom-to-operate for new products
  - Licensing opportunity identification
  - Competitive intelligence on R&D direction changes
  - Technology acquisition at reduced cost
