# Data Model Documentation

## Executive Summary

The ESG Data Ingestion Platform uses a multi-tenant, audit-trail-focused data model designed to handle messy real-world emissions data from heterogeneous sources (SAP, utility portals, travel platforms) while maintaining complete traceability for regulatory compliance.

The core insight: **separate raw data from normalized data**, with a forensic audit trail connecting them. This allows analysts to review original values, understand what transformations were applied, approve rows with confidence, and locked them for audit with full provenance.

---

## Entity Relationship Diagram

```
Organization (1) ──→ (M) DataSource
    │                        │
    │                        └─→ (M) RawIngestion
    │                               │
    │                               └─→ (M) NormalizedRow (1) ──→ (M) ApprovalLog
    │
    └─→ (M) User (future: for authentication/audit trail)
```

---

## Core Models

### 1. Organization

**Purpose**: Multi-tenant isolation. Every piece of data belongs to exactly one organization.

**Fields**:
```python
id              : UUID, primary key
name            : String (255), unique within deployment
slug            : String (100), URL-friendly identifier
created_at      : DateTime, immutable
metadata        : JSON, for org-specific config (emissions factors, units, etc.)
is_active       : Boolean, soft delete support
```

**Why This Design**:
- Enterprise clients need strict data isolation
- Future: enables white-label deployments
- UUID allows data to be portable if org is moved to different instance
- `metadata` field avoids schema changes when adding org-specific settings

**Example**:
```json
{
  "id": "org-acme-001",
  "name": "Acme Corporation",
  "slug": "acme",
  "metadata": {
    "fiscal_year_start": "04-01",
    "currency": "USD",
    "reporting_scope": ["Scope 1", "Scope 2", "Scope 3.6"],
    "facility_locations": {
      "US-CA": "California facility",
      "EU-DE": "German facility"
    }
  }
}
```

---

### 2. DataSource

**Purpose**: Configuration for each external data source. Tracks where data comes from, how to authenticate, what parser to use.

**Fields**:
```python
id              : UUID
org             : ForeignKey → Organization
source_type     : Enum: SAP_FUEL, SAP_PROCUREMENT, UTILITY_ELECTRICITY, 
                        TRAVEL_FLIGHTS, TRAVEL_HOTELS, TRAVEL_GROUND
                        (allows expansion)
name            : String, human-readable label (e.g., "SAP System US")
config          : JSON, encrypted credentials and settings
parser_version  : String, semantic version (e.g., "1.0.0") for traceability
active          : Boolean
last_sync       : DateTime or null
created_at      : DateTime
updated_at      : DateTime
```

**Why This Design**:
- Separates data source configuration from actual data
- `source_type` enum allows targeted parsing and scope assignment
- `config` as JSON allows different auth strategies (API key, file path, FTP, etc.)
- `parser_version` critical for audit: "these 1000 rows were parsed with v1.0.0"
- `last_sync` enables incremental pulls, duplicate prevention

**Example - SAP Source**:
```json
{
  "source_type": "SAP_FUEL",
  "name": "SAP US Plants",
  "config": {
    "auth_type": "api_key",
    "endpoint": "https://sapapi.company.com/odata/v4",
    "api_key": "[ENCRYPTED]",
    "plant_codes": ["3000", "1100"],
    "material_category": "02"
  },
  "parser_version": "1.0.0"
}
```

**Example - Utility Source**:
```json
{
  "source_type": "UTILITY_ELECTRICITY",
  "name": "Utility Meter Data - California",
  "config": {
    "auth_type": "file_upload",
    "portal_url": "https://www.pgandeutilities.com",
    "meter_ids": ["METER-001", "METER-002"],
    "timezone": "America/Los_Angeles"
  },
  "parser_version": "1.1.0"
}
```

---

### 3. RawIngestion

**Purpose**: Immutable record of raw data as received from source. This is the "source of truth" upstream reference.

**Fields**:
```python
id              : UUID
org             : ForeignKey → Organization
data_source     : ForeignKey → DataSource
upload_date     : DateTime
filename        : String (null if API pull)
raw_data        : TextField or FileField, the actual raw bytes/JSON
data_format     : Enum: CSV, JSON, XLSX, PDF_OCR
encoding        : String (e.g., "utf-8", "iso-8859-1")
num_rows        : Integer, count of rows in raw data
parsing_status  : Enum: PENDING, IN_PROGRESS, SUCCESS, FAILED
error_message   : Text, null if success
parsed_at       : DateTime or null
parsed_by       : String, parser version used
checksum        : String (SHA256), prevents duplicate uploads
created_at      : DateTime (immutable)
```

**Why This Design**:
- Immutable: never delete raw data. Required for audit compliance
- `checksum` prevents accidental re-upload of same file
- `parsing_status` enables async processing: upload → queue → parse → display
- `encoding` critical: German utility CSVs use ISO-8859-1, not UTF-8
- Stores raw data (not deleted after parsing) so analysts can see original values

**Example**:
```json
{
  "id": "ingestion-sap-2025-01-15-001",
  "org": "org-acme-001",
  "data_source": "source-sap-fuel-001",
  "upload_date": "2025-01-15T09:00:00Z",
  "filename": "SAP_Export_Fuel_Jan2025.csv",
  "num_rows": 1247,
  "parsing_status": "SUCCESS",
  "parsed_at": "2025-01-15T09:02:35Z",
  "parsed_by": "SAP Parser v1.0.0",
  "checksum": "sha256:abc123def456..."
}
```

---

### 4. NormalizedRow

**Purpose**: The heart of the system. Each raw row, after parsing and normalization, becomes one NormalizedRow. This is what analysts review and approve.

**Fields**:
```python
id                      : UUID
org                     : ForeignKey → Organization
data_source             : ForeignKey → DataSource
raw_ingestion           : ForeignKey → RawIngestion (immutable)
raw_row_index           : Integer, line number in raw file (1-based)
raw_row_data            : JSON, the original parsed row (for display)

# Normalized core fields
data_type               : Enum: FUEL, PROCUREMENT, ELECTRICITY, 
                                FLIGHT, HOTEL, GROUND_TRANSPORT
scope                   : Enum: SCOPE_1, SCOPE_2, SCOPE_3
category_code           : String, GHG Protocol category (e.g., "3.6" for travel)

# Materialized values (derived)
amount                  : Decimal, normalized quantity
unit                    : Enum: L, KG, KWH, NIGHTS, KM, etc.
currency                : String, ISO 4217 code (e.g., "USD")
date                    : Date, activity date (not invoice/billing date)
location                : String, plant/facility/airport code
location_display        : String, human-readable location name

# Key-value fields for flexibility
metadata                : JSON, source-specific data
  # For fuel: {material_id, plant_code, vendor, po_number}
  # For electricity: {meter_id, billing_period_start, billing_period_end}
  # For travel: {origin_airport, dest_airport, cabin_class, distance_km}

# Data quality flags
is_flagged              : Boolean
flag_reasons            : ArrayField of Enum: MISSING_DATA, UNIT_MISMATCH, 
                                              DUPLICATE, IMPLAUSIBLE_VALUE,
                                              PARSE_ERROR, AMBIGUOUS_DATA
flag_details            : JSON, detailed reason explanations
flagged_at              : DateTime or null
flagged_by              : String (user), or "SYSTEM" for auto-flags

# Approval workflow
is_approved             : Boolean, null = pending, true = approved, false = rejected
approved_at             : DateTime or null
approved_by             : ForeignKey → User or string
approval_notes          : Text, explanation for approval/rejection
is_locked               : Boolean, true = goes to audit, immutable after

# Audit trail
created_at              : DateTime
updated_at              : DateTime
```

**Why This Design**:

1. **Separation of Concerns**:
   - `raw_row_data` preserves original parsed values
   - `amount`, `unit`, `currency`, etc. are normalized versions
   - Analysts see both: they can verify transformation was correct

2. **Flexible Metadata**:
   - `metadata` JSON allows different sources to store different fields
   - SAP might store `{plant_code, material_id, vendor}`
   - Utility might store `{meter_id, billing_period_start, billing_period_end}`
   - Travel might store `{origin_airport, dest_airport, cabin_class}`
   - Avoids schema explosion

3. **Data Quality Flagging**:
   - Multiple `flag_reasons` because one row can have multiple issues
   - `MISSING_DATA`: unit was null
   - `UNIT_MISMATCH`: quantity was 1500 "L" but material is usually "kg"
   - `DUPLICATE`: same invoice number appeared in last 3 months
   - `IMPLAUSIBLE_VALUE`: 99,000 kWh in one day (spike detection)
   - `AMBIGUOUS_DATA`: cabin class marked "average" (no premium/economy distinction)

4. **Approval Workflow**:
   - `is_flagged` and `is_approved` are independent: flagged rows can still be approved
   - `is_locked` prevents tampering after analyst sign-off
   - Full audit trail: who approved, when, with what notes

**Example - SAP Fuel Row**:
```json
{
  "id": "row-sap-fuel-001",
  "org": "org-acme-001",
  "data_source": "source-sap-fuel-001",
  "raw_ingestion": "ingestion-sap-2025-01-15-001",
  "raw_row_index": 5,
  
  "data_type": "FUEL",
  "scope": "SCOPE_1",
  "category_code": "1.1",
  
  "amount": 1500.50,
  "unit": "L",
  "currency": "EUR",
  "date": "2025-01-15",
  "location": "DE01",
  "location_display": "Munich Plant",
  
  "metadata": {
    "material_id": "4600014780",
    "material_description": "Diesel Fuel - Annual Contract",
    "plant_code": "DE01",
    "vendor": "Shell Deutschland",
    "po_number": "4500001234",
    "invoice_date": "2025-01-17",
    "unit_original": "L",
    "price_per_unit": 1.25
  },
  
  "is_flagged": false,
  "flag_reasons": [],
  
  "is_approved": true,
  "approved_at": "2025-01-15T14:30:00Z",
  "approved_by": "analyst-sarah",
  "approval_notes": "Verified against PO 4500001234, matches vendor invoice",
  "is_locked": true,
  
  "created_at": "2025-01-15T09:02:45Z"
}
```

**Example - Utility Row with Flags**:
```json
{
  "id": "row-utility-electric-003",
  "org": "org-acme-001",
  "data_source": "source-utility-ca-001",
  "raw_ingestion": "ingestion-utility-2025-01-15-001",
  "raw_row_index": 7,
  
  "data_type": "ELECTRICITY",
  "scope": "SCOPE_2",
  "category_code": "2.1",
  
  "amount": 125000.50,
  "unit": "KWH",
  "currency": "USD",
  "date": "2025-01-31",
  "location": "US-CA",
  "location_display": "Oakland Plant",
  
  "metadata": {
    "meter_id": "MTR-CA-001",
    "billing_period_start": "2025-01-01",
    "billing_period_end": "2025-01-31",
    "rate_class": "commercial",
    "demand_charge_kw": 450.2,
    "invoice_number": "INV-2025-001",
    "utility_provider": "PG&E"
  },
  
  "is_flagged": true,
  "flag_reasons": ["DUPLICATE"],
  "flag_details": {
    "DUPLICATE": "Same meter (MTR-CA-001) with identical period and amount found in previous month's load"
  },
  "flagged_at": "2025-01-15T09:02:50Z",
  "flagged_by": "SYSTEM",
  
  "is_approved": true,
  "approved_at": "2025-01-15T14:25:00Z",
  "approved_by": "analyst-john",
  "approval_notes": "Confirmed duplicate - appears to be re-run of November data. Verified with utility portal.",
  "is_locked": true
}
```

**Example - Travel Row with Missing Data**:
```json
{
  "id": "row-travel-flight-012",
  "org": "org-acme-001",
  "data_source": "source-travel-navan-001",
  "raw_ingestion": "ingestion-travel-2025-01-15-001",
  "raw_row_index": 12,
  
  "data_type": "FLIGHT",
  "scope": "SCOPE_3",
  "category_code": "3.6",
  
  "amount": 5570.0,
  "unit": "KM",
  "currency": "USD",
  "date": "2025-02-15",
  "location": "LHR",
  "location_display": "London Heathrow → New York JFK",
  
  "metadata": {
    "segment_id": "SEG-2025-001",
    "origin_airport": "LHR",
    "dest_airport": "JFK",
    "departure_date": "2025-02-15",
    "cabin_class": "average",
    "airline": "BA",
    "flight_number": "112",
    "distance_km_calculated": 5570.0,
    "rfi_multiplier": 1.9,
    "employee_id": "EMP00123",
    "expense_id": "EXP-2025-0001"
  },
  
  "is_flagged": true,
  "flag_reasons": ["AMBIGUOUS_DATA"],
  "flag_details": {
    "AMBIGUOUS_DATA": "Cabin class marked 'average'. Emissions factor depends on economy/business/first. Flight cost ($2500) suggests business class."
  },
  "flagged_at": "2025-01-15T09:02:55Z",
  "flagged_by": "SYSTEM",
  
  "is_approved": true,
  "approved_at": "2025-01-15T14:20:00Z",
  "approved_by": "analyst-maya",
  "approval_notes": "Verified expense report - cost matches business class roundtrip LHR-JFK. Used business class emission factor.",
  "is_locked": true
}
```

---

### 5. ApprovalLog

**Purpose**: Immutable audit trail of every approval action. Required for compliance.

**Fields**:
```python
id              : UUID
org             : ForeignKey → Organization
normalized_row  : ForeignKey → NormalizedRow
action          : Enum: APPROVED, REJECTED, FLAGGED, UNFLAGGED
user            : String (user ID or name)
timestamp       : DateTime
notes           : Text, reason or explanation
previous_state  : JSON, snapshot before action (for audit)
new_state       : JSON, snapshot after action (for audit)
```

**Why This Design**:
- Immutable: insert-only table, never updated
- Full history: see every change to every row
- Snapshots: know exactly what was changed
- Compliant: auditors can verify chain of custody

**Example**:
```json
[
  {
    "id": "log-001",
    "normalized_row": "row-sap-fuel-001",
    "action": "FLAGGED",
    "user": "SYSTEM",
    "timestamp": "2025-01-15T09:02:45Z",
    "notes": "Auto-flagged: duplicate PO number detected",
    "new_state": {"is_flagged": true, "flag_reasons": ["DUPLICATE"]}
  },
  {
    "id": "log-002",
    "normalized_row": "row-sap-fuel-001",
    "action": "UNFLAGGED",
    "user": "analyst-sarah",
    "timestamp": "2025-01-15T14:15:00Z",
    "notes": "Verified against SAP system - not a duplicate, different vendor invoice",
    "previous_state": {"is_flagged": true, "flag_reasons": ["DUPLICATE"]},
    "new_state": {"is_flagged": false, "flag_reasons": []}
  },
  {
    "id": "log-003",
    "normalized_row": "row-sap-fuel-001",
    "action": "APPROVED",
    "user": "analyst-sarah",
    "timestamp": "2025-01-15T14:30:00Z",
    "notes": "Verified against PO 4500001234, matches vendor invoice",
    "new_state": {"is_approved": true, "is_locked": true}
  }
]
```

---

## Data Flow

```
1. INGESTION
   ├─ Upload file or trigger API pull
   ├─ Create RawIngestion record (status: PENDING)
   └─ Store raw bytes/JSON

2. PARSING
   ├─ Parser processes raw data
   ├─ Create NormalizedRow for each record
   ├─ Extract fields: amount, unit, date, location, scope
   └─ Update RawIngestion (status: SUCCESS or FAILED)

3. VALIDATION & FLAGGING
   ├─ Apply data quality rules
   ├─ Auto-flag rows:
   │  ├─ MISSING_DATA (unit=null)
   │  ├─ DUPLICATE (same meter + same period)
   │  ├─ UNIT_MISMATCH (value typical kg but quantity is "L")
   │  ├─ IMPLAUSIBLE_VALUE (250,000 kWh per day)
   │  └─ AMBIGUOUS_DATA (cabin class = "average")
   └─ Create ApprovalLog entries

4. REVIEW & APPROVAL
   ├─ Analyst sees NormalizedRow with flags
   ├─ Can see raw_row_data (original) and normalized values
   ├─ Decides: APPROVE, REJECT, or REQUEST_INFO
   ├─ Creates ApprovalLog entry
   └─ If approved, sets is_locked=true (immutable for audit)

5. EXPORT TO AUDIT
   ├─ Only locked rows exported
   ├─ Include full chain of custody
   └─ Includes ApprovalLog history
```

---

## Key Design Decisions

### 1. Raw Data Immutability

**Why?** Regulatory compliance. Auditors need to see original data as received.

**How?** RawIngestion stores raw bytes, never modified. If re-parsing needed, create new RawIngestion record.

**Trade-off**: Storage cost (keep all raw CSVs forever). Worth it for compliance.

---

### 2. Normalized Row JSON Metadata

**Why?** Different sources have different fields. SAP has material_id; utility has meter_id; travel has cabin_class.

**How?** Core fields standardized (amount, unit, date, location); source-specific data in `metadata` JSON.

**Trade-off**: Less strongly-typed. But enables flexibility and avoids schema migrations for each new source type.

---

### 3. Dual Storage: Raw vs Normalized

**Why?** Analysts need to see both to verify transformation was correct.

**How?** 
- `raw_row_data`: original values as parsed
- `amount`, `unit`, etc.: normalized values
- Both shown in UI side-by-side

**Trade-off**: Slight duplication. Worth it for transparency and auditability.

---

### 4. System Auto-Flagging

**Why?** Data quality issues are caught before analyst review.

**How?** Parser creates NormalizedRow with `is_flagged=true` if issues detected.

**Trade-off**: May miss edge cases. But catches 80% of issues automatically, saves analyst time.

---

### 5. Approval is Separate from Flagging

**Why?** An analyst might approve a flagged row after verification (e.g., duplicate is legitimate).

**How?** `is_flagged` and `is_approved` are independent booleans.

**Trade-off**: More complex logic. But more realistic: not all flagged data is bad, just needs review.

---

## Database Schema (SQL)

```sql
-- Organizations
CREATE TABLE core_organization (
  id UUID PRIMARY KEY,
  name VARCHAR(255) UNIQUE,
  slug VARCHAR(100),
  metadata JSON,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP
);

-- Data Sources
CREATE TABLE core_datasource (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES core_organization,
  source_type VARCHAR(50),
  name VARCHAR(255),
  config JSON,
  parser_version VARCHAR(20),
  active BOOLEAN,
  last_sync TIMESTAMP,
  created_at TIMESTAMP,
  UNIQUE(org_id, name)
);

-- Raw Ingestions
CREATE TABLE core_rawingestion (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES core_organization,
  data_source_id UUID REFERENCES core_datasource,
  upload_date TIMESTAMP,
  filename VARCHAR(500),
  raw_data TEXT,
  data_format VARCHAR(20),
  encoding VARCHAR(20),
  num_rows INTEGER,
  parsing_status VARCHAR(20),
  error_message TEXT,
  parsed_at TIMESTAMP,
  parsed_by VARCHAR(50),
  checksum VARCHAR(64),
  created_at TIMESTAMP,
  INDEX (org_id),
  INDEX (data_source_id),
  INDEX (checksum)
);

-- Normalized Rows
CREATE TABLE core_normalizedrow (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES core_organization,
  data_source_id UUID REFERENCES core_datasource,
  raw_ingestion_id UUID REFERENCES core_rawingestion,
  raw_row_index INTEGER,
  raw_row_data JSON,
  
  data_type VARCHAR(50),
  scope VARCHAR(20),
  category_code VARCHAR(10),
  
  amount DECIMAL(15, 2),
  unit VARCHAR(20),
  currency VARCHAR(3),
  date DATE,
  location VARCHAR(100),
  location_display VARCHAR(255),
  
  metadata JSON,
  
  is_flagged BOOLEAN DEFAULT false,
  flag_reasons VARCHAR(500),
  flag_details JSON,
  flagged_at TIMESTAMP,
  flagged_by VARCHAR(50),
  
  is_approved BOOLEAN,
  approved_at TIMESTAMP,
  approved_by VARCHAR(100),
  approval_notes TEXT,
  is_locked BOOLEAN DEFAULT false,
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  
  INDEX (org_id),
  INDEX (data_source_id),
  INDEX (is_flagged),
  INDEX (is_approved),
  INDEX (scope),
  INDEX (date),
  UNIQUE (raw_ingestion_id, raw_row_index)
);

-- Approval Log
CREATE TABLE core_approvallog (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES core_organization,
  normalized_row_id UUID REFERENCES core_normalizedrow,
  action VARCHAR(50),
  user_id VARCHAR(100),
  timestamp TIMESTAMP,
  notes TEXT,
  previous_state JSON,
  new_state JSON,
  
  created_at TIMESTAMP,
  
  INDEX (org_id),
  INDEX (normalized_row_id),
  INDEX (timestamp)
);
```

---

## Multi-Tenancy Implementation

Every query includes `org_id` filter:

```python
# Example: Get all unflagged electricity rows for Acme Corp
rows = NormalizedRow.objects.filter(
    org_id="org-acme-001",
    data_type="ELECTRICITY",
    is_flagged=False
)

# Example: Approvals made by Acme Corp
logs = ApprovalLog.objects.filter(
    org_id="org-acme-001",
    action="APPROVED"
).order_by('-timestamp')
```

Database-level constraints ensure no cross-tenant data leakage.

---

## Unit Normalization

Each NormalizedRow stores `unit` in standardized enum:

```python
UNITS = {
    'L': 'Liters (fuel)',
    'KG': 'Kilograms (fuel, materials)',
    'M3': 'Cubic meters (gas)',
    'KWH': 'Kilowatt-hours (electricity)',
    'MWH': 'Megawatt-hours',
    'GJ': 'Gigajoules',
    'NIGHTS': 'Hotel nights',
    'KM': 'Kilometers (travel)',
    'MILES': 'Miles (travel)',
}
```

Parsers convert incoming units to standard units:
- "m3" or "cbm" or "cubic meters" → "M3"
- "kwh" or "kWH" or "KWH" → "KWH"
- "km" or "kilometers" → "KM"

---

## Scope Assignment

| Data Type | Scope |
|-----------|-------|
| Fuel | SCOPE_1 (Direct emissions) |
| Procurement (materials) | SCOPE_3 (Indirect) |
| Electricity | SCOPE_2 (Indirect - purchased) |
| Travel (flights/hotels/ground) | SCOPE_3 (Indirect - business) |

Each source is pre-configured with scope. If org buys from renewable energy supplier, they might override to SCOPE_1, stored in DataSource config.

---

## Audit Trail Requirements

Every NormalizedRow must be traceable to:
1. Original RawIngestion (raw CSV/JSON file)
2. Parser version used
3. Normalization rules applied
4. Analyst approval (with timestamp, notes)
5. Any flag/unflag history

This allows auditors to ask:
- "Where did this row come from?" → RawIngestion
- "Who approved it?" → ApprovalLog
- "What was the original value?" → raw_row_data
- "What transformation was applied?" → comparing raw_row_data to normalized fields
- "Has it been locked for audit?" → is_locked flag

---

## Future Extensions

This model supports:

1. **User Authentication**: Add user table, track user_id in ApprovalLog
2. **Batch Operations**: Add BatchApproval model for bulk approvals
3. **Emissions Calculation**: Add EmissionsRow model (locked rows → emissions values)
4. **Custom Rules Engine**: Add ValidationRule model for org-specific flagging logic
5. **Data Quality SLA**: Add metrics to track % flagged, avg approval time
6. **Versioning**: Support multiple parser versions running in parallel (A/B testing)

The current design doesn't lock you into any of these, but makes adding them straightforward.

---

## Summary

This data model prioritizes:
1. **Auditability**: Every row traceable to source, parser, analyst
2. **Flexibility**: Different sources can have different metadata
3. **Data Quality**: Automatic flagging + analyst review before lock
4. **Compliance**: Immutable raw data, immutable audit trail
5. **Multi-tenancy**: Strict org-level isolation
6. **Transparency**: Both raw and normalized values visible for verification

The goal: analysts and auditors have complete confidence in the emissions data pipeline.
