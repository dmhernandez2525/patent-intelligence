# Phase 10: Watchlist, Alerts & Production Polish - Software Design Document

## Overview

Provides a comprehensive watchlist system for tracking patents, CPC codes, assignees, and inventors with automated alert generation for expirations, maintenance fees, and other events. Includes a real-time dashboard statistics service and system health monitoring.

## Architecture

```
Frontend (WatchlistPage, Dashboard)
    |
    v
GET/POST/PATCH/DELETE /api/watchlist
GET /api/watchlist/alerts
GET /api/stats
GET /api/status
    |
    v
+-- WatchlistService
|       +-- get_watchlist()           --> Paginated user watchlist
|       +-- add_to_watchlist()        --> Add patent/CPC/assignee/inventor
|       +-- update_watchlist_item()   --> Modify notification settings
|       +-- remove_from_watchlist()   --> Delete tracked item
|       +-- get_alerts()              --> Paginated user alerts
|       +-- mark_alert_read()         --> Mark alert as read
|       +-- dismiss_alert()           --> Dismiss alert
|       +-- generate_alerts()         --> Create alerts from watchlist
|       +-- get_alert_summary()       --> Dashboard alert counts
|
+-- StatsService
        +-- get_dashboard_stats()     --> Aggregate statistics
        +-- get_system_status()       --> Component health checks
    |
    v
WatchlistItem, Alert, Patent, MaintenanceFee models (SQLAlchemy)
```

## Components

### 1. Database Models (`src/models/watchlist.py`)

**WatchlistItem**
```python
class WatchlistItem:
    id: int                    # Primary key
    user_id: str               # User identifier (default: "default")
    item_type: str             # "patent", "cpc_code", "assignee", "inventor"
    item_value: str            # The watched value (patent number, CPC, etc.)
    patent_id: int | None      # FK to patents table (for patent type)
    name: str | None           # User-friendly display name
    notes: str | None          # User notes

    # Notification settings
    notify_expiration: bool    # Alert on patent expiration (default: True)
    notify_maintenance: bool   # Alert on maintenance fees (default: True)
    notify_citations: bool     # Alert on new citations (default: False)
    notify_new_patents: bool   # Alert on new patents in CPC (default: False)

    # Lead times
    expiration_lead_days: int  # Days before expiration to alert (default: 90)
    maintenance_lead_days: int # Days before maintenance due (default: 30)

    is_active: bool            # Active/paused status
    alerts: list[Alert]        # Related alerts (cascade delete)
```

**Alert**
```python
class Alert:
    id: int                      # Primary key
    watchlist_item_id: int       # FK to watchlist_items
    alert_type: str              # "expiration", "maintenance_fee", "new_citation", etc.
    priority: str                # "low", "medium", "high", "critical"
    title: str                   # Alert headline
    message: str                 # Detailed description

    related_patent_number: str   # Associated patent number
    related_data: dict           # Additional JSON data (fee_id, etc.)

    trigger_date: datetime       # When alert was generated
    due_date: datetime | None    # When action is required

    is_read: bool                # Read status
    is_dismissed: bool           # Dismissed status
    read_at: datetime | None     # When marked read
    dismissed_at: datetime | None # When dismissed
```

**Enums**
- `WatchItemType`: PATENT, CPC_CODE, ASSIGNEE, INVENTOR
- `AlertType`: EXPIRATION, MAINTENANCE_FEE, NEW_CITATION, STATUS_CHANGE, NEW_PATENT
- `AlertPriority`: LOW, MEDIUM, HIGH, CRITICAL

### 2. Watchlist Service (`src/services/watchlist_service.py`)

**CRUD Operations**

| Method | Description |
|--------|-------------|
| `get_watchlist(user_id, item_type, include_inactive, page, per_page)` | Paginated watchlist with alert counts |
| `add_to_watchlist(item_type, item_value, user_id, name, notes, ...)` | Add item with notification settings |
| `update_watchlist_item(item_id, user_id, **updates)` | Update allowed fields |
| `remove_from_watchlist(item_id, user_id)` | Delete with cascade to alerts |

**Alert Management**

| Method | Description |
|--------|-------------|
| `get_alerts(user_id, unread_only, alert_type, page, per_page)` | Paginated alerts, excludes dismissed |
| `mark_alert_read(alert_id, user_id)` | Set is_read=True with timestamp |
| `dismiss_alert(alert_id, user_id)` | Set is_dismissed=True with timestamp |
| `get_alert_summary(user_id)` | Counts by type and priority |

**Alert Generation**

`generate_alerts(user_id)` scans active patent watchlist items:

1. **Expiration Alerts**
   - Checks patent expiration_date against expiration_lead_days
   - Priority: critical (≤30 days), high (≤60 days), medium (>60 days)
   - Skips if identical alert already exists and not dismissed

2. **Maintenance Fee Alerts**
   - Finds next pending MaintenanceFee for watched patents
   - Checks due_date against maintenance_lead_days
   - Priority: high (≤14 days), medium (>14 days)
   - Stores fee_id in related_data for tracking

### 3. Stats Service (`src/services/stats_service.py`)

**get_dashboard_stats(user_id)**
Returns:
```python
{
    "patents": {
        "total": int,           # Total patents in database
        "expiring_90_days": int # Active patents expiring in 90 days
    },
    "trends": {
        "top_cpc": [{"cpc_code": str, "count": int}, ...]  # Top 5 CPC codes
    },
    "watchlist": {
        "count": int,           # User's active watchlist items
        "unread_alerts": int    # User's unread, undismissed alerts
    },
    "ingestion": {
        "last_run": str | None,    # ISO timestamp
        "last_source": str | None, # "uspto", "epo"
        "last_status": str | None  # "completed", "failed"
    }
}
```

**get_system_status()**
Checks component health:
```python
{
    "api_server": "operational",      # Always operational if responding
    "database": "operational|error",  # SELECT NOW() test
    "uspto_ingestion": "operational|pending",  # Has USPTO patents?
    "epo_integration": "operational|pending",  # Has EPO patents?
    "embedding_service": "operational|pending" # Has embeddings?
}
```

### 4. API Endpoints (`src/api/routes/watchlist.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/watchlist` | GET | List watchlist items (paginated) |
| `/api/watchlist` | POST | Add item to watchlist |
| `/api/watchlist/{item_id}` | PATCH | Update watchlist item |
| `/api/watchlist/{item_id}` | DELETE | Remove from watchlist |
| `/api/watchlist/alerts` | GET | List alerts (paginated) |
| `/api/watchlist/alerts/summary` | GET | Alert counts by type/priority |
| `/api/watchlist/alerts/{alert_id}/read` | POST | Mark alert as read |
| `/api/watchlist/alerts/{alert_id}/dismiss` | POST | Dismiss alert |

**Health Endpoints (`src/api/routes/health.py`)**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Dashboard statistics |
| `/api/status` | GET | System component health |

### 5. Frontend Components

**WatchlistPage (`frontend/src/pages/WatchlistPage.tsx`)**
- Add watchlist form with type selector and notification toggles
- Watchlist table with unread alert badges
- Inline edit/delete actions
- Alerts panel with priority-colored indicators
- Read/dismiss action buttons
- Empty states for no items/alerts

**Dashboard (`frontend/src/pages/Dashboard.tsx`)**
- Fetches real data from `/api/stats` and `/api/status`
- Patent count cards with trend indicators
- System status panel with operational badges
- Quick action cards linking to features
- Top CPC trends display
- Watchlist alert summary

## Design Decisions

1. **User-scoped watchlists**: All operations filter by user_id, enabling multi-tenant deployment. Default "default" user allows single-user mode without authentication.

2. **Soft-delete alerts via dismiss**: Dismissed alerts remain in database for audit trail but are excluded from queries. Hard delete on watchlist item cascade-deletes its alerts.

3. **Configurable lead times**: Per-item expiration_lead_days and maintenance_lead_days allow users to customize urgency thresholds for different patents.

4. **Priority escalation**: Alert priority automatically escalates as due dates approach (90→60→30 day thresholds for expiration).

5. **Duplicate prevention**: Alert generation checks for existing non-dismissed alerts before creating new ones, preventing notification spam.

6. **Related data flexibility**: JSONB related_data field on alerts allows storing context-specific metadata (fee IDs, citation counts, etc.) without schema changes.

7. **Eager loading alerts**: Watchlist queries use selectinload for alerts relationship, enabling unread count calculation without N+1 queries.

8. **Stats service separation**: Dashboard statistics in dedicated service keeps health endpoints lightweight and enables caching strategies.

## Database Indexes

```sql
-- WatchlistItem
CREATE INDEX ix_watchlist_user_type ON watchlist_items(user_id, item_type);
CREATE UNIQUE INDEX ix_watchlist_user_value ON watchlist_items(user_id, item_value);
CREATE INDEX ix_watchlist_items_item_type ON watchlist_items(item_type);
CREATE INDEX ix_watchlist_items_item_value ON watchlist_items(item_value);
CREATE INDEX ix_watchlist_items_patent_id ON watchlist_items(patent_id);
CREATE INDEX ix_watchlist_items_user_id ON watchlist_items(user_id);

-- Alert
CREATE INDEX ix_alerts_unread ON alerts(watchlist_item_id, is_read);
CREATE INDEX ix_alerts_trigger ON alerts(trigger_date);
CREATE INDEX ix_alerts_alert_type ON alerts(alert_type);
CREATE INDEX ix_alerts_watchlist_item_id ON alerts(watchlist_item_id);
```

## Security Considerations

1. **User isolation**: All queries include user_id filter to prevent cross-user data access.

2. **Ownership verification**: Alert read/dismiss operations verify the alert belongs to a watchlist item owned by the requesting user.

3. **Input validation**: Pydantic schemas validate item_type against allowed enum values.

4. **Cascade delete**: Removing a watchlist item automatically removes associated alerts, preventing orphaned data.

## Future Enhancements

- Email/webhook notification delivery
- Bulk alert management (mark all read)
- Scheduled alert generation via Celery
- Alert history/archive view
- Custom alert rules (citation threshold, assignee changes)
