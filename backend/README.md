# Backend - ESG Data Ingestion API

Django REST API for ESG data ingestion, parsing, normalization, and approval workflow.

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Migrate database
python manage.py migrate

# Run server
python manage.py runserver

# API available at http://localhost:8000/api/
```

## Project Structure

```
backend/
├── config/                 # Django settings and main URL config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                   # Main app
│   ├── models.py          # Organization, DataSource, RawIngestion, NormalizedRow, ApprovalLog
│   ├── views.py           # API ViewSets
│   ├── serializers.py     # DRF Serializers
│   ├── urls.py            # App URL routing
│   ├── parsers/           # Data parsing modules
│   │   ├── sap_parser.py
│   │   ├── utility_parser.py
│   │   ├── travel_parser.py
│   │   └── validators.py
│   ├── migrations/        # Database migrations
│   └── admin.py
├── sample_data/           # Sample CSV/JSON files for testing
│   ├── sap_fuel.csv
│   ├── utility_electricity.csv
│   └── travel_expenses.json
├── manage.py
└── requirements.txt
```

## Models

### Organization
Multi-tenant organization. All data is scoped to organizations.

```python
{
  "id": 1,
  "name": "Acme Corporation",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### DataSource
Configuration for a specific data source within an organization.

```python
{
  "id": 1,
  "org": 1,
  "source_type": "SAP_FUEL",
  "name": "SAP Fuel Data",
  "config": {},
  "created_at": "2024-01-15T10:00:00Z"
}
```

### RawIngestion
Raw uploaded/imported data before parsing.

```python
{
  "id": 1,
  "org": 1,
  "data_source": 1,
  "file_name": "sap_fuel.csv",
  "raw_data": [...],  # Original CSV/JSON data as list of dicts
  "parsing_status": "SUCCESS",
  "error_message": null,
  "row_count": 10,
  "upload_date": "2024-01-15T10:00:00Z"
}
```

### NormalizedRow
Parsed and normalized row, ready for review and approval.

```python
{
  "id": 1,
  "org": 1,
  "data_source": 1,
  "raw_ingestion": 1,
  "source_row_id": "sap_1",
  "data_type": "SAP",
  "data": {...},  # Full parsed row data
  "scope": 1,  # Scope 1, 2, or 3
  "unit_normalized": "L",
  "amount_normalized": 1000.0,
  "currency": "EUR",
  "location": "Plant-A",
  "date": "2024-01-15",
  "flagged": false,
  "flag_reason": null,
  "approved_at": "2024-01-16T14:30:00Z",
  "approved_by": 1,
  "created_at": "2024-01-15T10:00:00Z"
}
```

### ApprovalLog
Audit trail of all approvals, flags, and unflaggs.

```python
{
  "id": 1,
  "org": 1,
  "normalized_row": 1,
  "action": "APPROVED",
  "user": 1,
  "user_name": "john_doe",
  "timestamp": "2024-01-16T14:30:00Z",
  "notes": "Looks good"
}
```

## API Endpoints

All endpoints require org_id parameter (either in URL params or request body).

### Organizations
- `GET /api/organizations/` - List all organizations
- `POST /api/organizations/` - Create organization

### Data Sources
- `GET /api/data-sources/?org_id=<id>` - List data sources for org
- `POST /api/data-sources/` - Create data source

### Raw Ingestions
- `GET /api/raw-ingestions/?org_id=<id>` - List raw ingestions
- `POST /api/raw-ingestions/upload/` - Upload and parse file

Example:
```bash
curl -X POST http://localhost:8000/api/raw-ingestions/upload/ \
  -F "org_id=1" \
  -F "data_source_id=1" \
  -F "file=@sample_data/sap_fuel.csv"
```

### Normalized Rows
- `GET /api/rows/?org_id=<id>` - List rows with optional filters
  - `data_type` - SAP, UTILITY, TRAVEL
  - `flagged` - true/false
  - `approved` - true/false
  - `start_date`, `end_date` - Date filtering
  - `ordering` - Sort field (prefix with `-` for descending)
  - `search` - Search by location/material/meter ID
  
- `POST /api/rows/{id}/approve/` - Approve a row
  - Body: `{"notes": "Optional notes"}`
  
- `POST /api/rows/{id}/flag/` - Flag a row
  - Body: `{"reason": "...", "notes": "..."}`
  
- `POST /api/rows/{id}/unflag/` - Remove flag
  - Body: `{"notes": "..."}`

### Approval Logs
- `GET /api/approval-logs/?org_id=<id>` - List audit trail
  - Optional filters: `action`, `days`

### Dashboard
- `GET /api/dashboard/stats/?org_id=<id>` - Get statistics

Response:
```json
{
  "total_rows": 28,
  "approved_rows": 10,
  "flagged_rows": 5,
  "pending_rows": 13,
  "by_data_type": {
    "SAP": 10,
    "UTILITY": 9,
    "TRAVEL": 9
  },
  "by_scope": {
    "1": 19,
    "2": 9,
    "3": 9
  },
  "total_amount": 45000.50,
  "recent_uploads": 3
}
```

## Data Parsers

### SAPParser
Parses SAP CSV export files with support for:
- German headers (MATNR, WERKS, Menge, MEINS, Budat, etc.)
- Unit normalization:
  - Fuel: L, liter, m³, kg, tonnes (tonnes → kg * 1000)
  - Energy: kWh, MWh (MWh → kWh * 1000), Wh
- Duplicate detection (same material, plant, date, qty)
- Currency and date validation

**Flags:**
- Invalid quantity format
- Unknown unit
- Invalid date
- Invalid price
- Unknown currency
- Duplicate row

### UtilityParser
Parses utility provider CSV files with support for:
- Meter ID, billing period start/end, quantity, unit, cost, currency, location
- Decimal separators (comma and dot: 1.000,50 → 1000.50)
- Automatic deduplication by (meter_id, start_date, end_date)
- Billing period alignment checking

**Flags:**
- Missing meter ID
- Invalid quantity format
- Invalid cost format
- Unknown currency
- Invalid date format
- Billing period not aligned to calendar month
- Duplicate billing period (billing correction)

### TravelParser
Parses Concur/Navan JSON files with support for:
- Multiple segment types: AIRFR (flight), HOTEL, TAXIF (ground), RAILF (train), CARHIRE
- Automatic segment extraction from single or array format
- Distance tracking
- Round-trip indication

**Flags:**
- Missing cabin class (affects emission calculation)
- Missing distance (calculated from origin/destination)
- Missing origin/destination
- Missing hotel location
- Unable to determine hotel stay duration
- Invalid dates or costs

## Data Quality Issues Detected

### By Data Type

**SAP:**
1. Unit inconsistencies (L vs liter, m³ vs cbm, kg vs t)
2. German header names (MATNR instead of MATERIAL_NUMBER)
3. Duplicate rows (same material, plant, date, quantity)
4. Missing cost centers or PO numbers
5. Mismatched units (very large quantities in liters indicate they should be in m³)

**Utility:**
1. Billing periods spanning multiple months (non-standard billing cycles)
2. Duplicate billing periods (billing corrections/adjustments)
3. Decimal separator issues (European format: 1.000,50)
4. Missing or inconsistent meter IDs
5. Very high/low consumption (potential data errors)

**Travel:**
1. Missing cabin class (economy vs business affects emissions)
2. Missing distance data (required for emission calculation)
3. Missing hotel location
4. Missing round-trip indication
5. Incomplete segment information

## Sample Data

Sample files in `sample_data/` include realistic data quality issues:

### sap_fuel.csv
```
MATNR,WERKS,Menge,MEINS,Budat,Netpr,WAERS,KOSTL,Ebeln
MAT-001,P001,1000,L,2024-01-15,0.85,EUR,CC-100,PO-2024-001
MAT-002,P001,500,L,2024-01-20,1.25,EUR,CC-100,PO-2024-002
MAT-001,P001,1000,L,2024-01-15,0.85,EUR,CC-100,PO-2024-001
...
```

Issues included:
- Duplicate row (row 1 and 3)
- Empty quantity (row 7)
- Varying unit formats (KG vs kg vs Kilogram)
- Missing PO number (row 10)

### utility_electricity.csv
```
Meter_ID,Billing_Period_Start,Billing_Period_End,Quantity,Unit,Cost,Currency,Location
METER-001,2024-01-01,2024-01-31,12500,kWh,1250.00,EUR,Plant-A
...
```

Issues included:
- Duplicate billing period (rows 1 and 3)
- Mid-month billing period (rows 2, 7)
- Decimal separator variation (European: "1.850,00")
- MWh instead of kWh (row 6)

### travel_expenses.json
```json
[
  {
    "id": "EXP-2024-001",
    "employee_id": "EMP-101",
    "segments": [
      {
        "type": "AIRFR",
        "start_date": "2024-01-15",
        "origin": "NYC",
        "destination": "LAX",
        "distance": 2451,
        "cabin_class": "Business",
        "cost": 1250.00
      }
    ]
  }
]
```

Issues included:
- Missing cabin class (row 2)
- Missing distance
- Round-trip without explicit indication

## Running Locally

1. **Setup environment:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Database:**
```bash
python manage.py migrate
python manage.py shell
# Load sample data using the populate script
```

3. **Create admin user (optional):**
```bash
python manage.py createsuperuser
```

4. **Run server:**
```bash
python manage.py runserver
```

5. **Access:**
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Frontend: http://localhost:3000/

## Testing API

```bash
# Create organization
curl -X POST http://localhost:8000/api/organizations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Corp"}'

# Create data source
curl -X POST http://localhost:8000/api/data-sources/ \
  -H "Content-Type: application/json" \
  -d '{"org": 1, "source_type": "SAP_FUEL", "name": "SAP", "config": {}}'

# Upload file
curl -X POST http://localhost:8000/api/raw-ingestions/upload/ \
  -F "org_id=1" \
  -F "data_source_id=1" \
  -F "file=@sample_data/sap_fuel.csv"

# List rows
curl http://localhost:8000/api/rows/?org_id=1

# Approve row
curl -X POST http://localhost:8000/api/rows/1/approve/ \
  -H "Content-Type: application/json" \
  -d '{"notes": "Approved"}'

# Flag row
curl -X POST http://localhost:8000/api/rows/2/flag/ \
  -H "Content-Type: application/json" \
  -d '{"reason": "Missing cabin class", "notes": ""}'

# View stats
curl http://localhost:8000/api/dashboard/stats/?org_id=1
```

## Configuration

Key settings in `config/settings.py`:
- `DEBUG` - Set to False in production
- `SECRET_KEY` - Use environment variable in production
- `ALLOWED_HOSTS` - Configure for production
- `DATABASES` - SQLite for dev, PostgreSQL for prod
- `CORS_ALLOWED_ORIGINS` - Frontend URLs
- `REST_FRAMEWORK` - DRF pagination (50 rows/page)

## Admin Interface

Access at http://localhost:8000/admin/ with superuser credentials to:
- View/edit organizations
- View/edit data sources
- View raw ingestions and normalized rows
- View approval logs

## Performance

- Database indexes on frequently filtered fields (org, data_type, date, flagged, approved_by)
- Pagination (50 rows per page by default)
- Async file uploads and parsing for large files
- Query optimization with select_related/prefetch_related

## Error Handling

All API errors return standard format:
```json
{
  "error": "Description of error",
  "details": "Additional details if available"
}
```

Parsing errors are captured in RawIngestion.error_message and don't block row creation.
