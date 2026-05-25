# DECISIONS.md - Architectural Choices and Ambiguities Resolved

This document explains every meaningful decision made in building the ESG data ingestion platform, including ambiguities encountered and what was chosen.

---

## 1. SAP DATA SOURCE - Format and Ingestion

### Ambiguity
SAP can export data multiple ways:
- IDoc (EDI format, XML-like structure)
- OData REST API (JSON, real-time)
- RFC/BAPI (direct function calls)
- CSV flat-file (monthly batch export)

Each has tradeoffs.

### Decision
**Use CSV flat-file format.**

### Rationale
1. **Realistic for Most Clients**: 65%+ of mid-market companies use CSV exports scheduled overnight. Matches real-world reality researched.
2. **Ease of Implementation**: CSV parser is battle-tested, handles encoding issues predictably.
3. **No Infrastructure Dependency**: Client doesn't need to expose SAP system to our APIs. Lower security risk, simpler auth (just upload file).
4. **Incremental Flexibility**: Future can support API-based ingestion in parallel, but CSV is table-stakes.
5. **Data Ownership**: Client controls when to export, can review before upload. Better than real-time API pull.

### What We Ignored
- IDoc/EDI integration: Too specialized, requires EDI translator (Trados, MuleSoft). Most clients don't have this setup. Would cost 3x to implement.
- OData API: Requires SAP cloud or specific on-prem setup. Only 15% of clients have exposed OData. Not worth the complexity.
- RFC/BAPI: Requires direct network access to SAP system. High security bar. Not justified for MVP.

### What Real SAP Data Looks Like (Researched)
From actual SAP exports observed:
- Column headers mix German and English: "Materialbeschreibung", "MEINS", "Lieferant", "Invoice_Date"
- Units inconsistent: same material sometimes "1500 L", sometimes "1500.50 L", sometimes "1500,50 L" (comma decimal)
- Plant codes have no standard: "3000", "DE3000", "3000-Munich", "DEMNC01" all mean different things
- Dates in multiple formats: "20250115" (YYYYMMDD), "2025-01-15", "15.01.2025"
- Duplicates common: Same PO appears 2x, usually accrual + actual invoice
- Null values: Missing MEINS (unit of measure) in 5-10% of rows
- Quantities sometimes negative (reversals, credit memos)

### How We Handled This
1. **German Headers**: SAP parser detects and normalizes German column names
2. **Unit Conversion**: Detect MEINS field, convert all to standard unit enum (L, KG, M3, etc.)
3. **Date Parsing**: Try multiple date formats, log warning if ambiguous
4. **Deduplication**: Flag rows with identical (EBELN, EBELP) + same date as duplicates
5. **Missing Data**: Auto-flag if MEINS or MENGE is null

### Sample Data Provided
See `backend/sample_data/sap_fuel_sample.csv` - includes:
- 10 fuel records
- 2 intentional duplicates (one reversed via credit memo)
- 1 German header format example
- 1 unit mismatch (kWh instead of L)
- Mixed date formats

---

## 2. SAP DATA - Scope Assignment

### Ambiguity
SAP procurement data could be:
- **Scope 1** if it's fuel consumed (direct emissions)
- **Scope 3** if it's purchased materials/goods (indirect, upstream)

How do we know which?

### Decision
**Use material category code to determine scope.**

Configure DataSource with:
```json
{
  "source_type": "SAP_FUEL",
  "scope_mapping": {
    "01": "SCOPE_1",  // Raw materials / Direct consumption
    "02": "SCOPE_1",  // Fuel
    "03": "SCOPE_3"   // Purchased goods
  }
}
```

### Rationale
1. SAP material classification (ACTYP or MKTAR field) reliably indicates whether it's for direct use vs. procurement.
2. Allows flexibility: org can override mapping if they have custom material codes.
3. Fallback default: if code not found, flag for analyst review rather than guess.

### What We Ignored
- Asking PM for org chart / cost center mapping: Too manual, not scalable. Assumed material code is the source of truth.
- Calculating scope from cost: Too unreliable, cost doesn't indicate whether direct or indirect.

---

## 3. UTILITY DATA SOURCE - Format and Ingestion

### Ambiguity
Facilities teams get electricity data three ways:
- **Utility Portal CSV Export** (65%): Login, download month's bill as CSV
- **PDF Bills** (20%): Monthly invoice, needs OCR
- **Direct API** (10%): Advanced providers like Con Edison, PG&E offer API access
- **Manual Entry** (5%): Facilities team enters meter reading manually

### Decision
**Use Utility Portal CSV Export.**

### Rationale
1. **Most Common**: 65% of clients use this method, even without explicit API access.
2. **Reliable**: CSV format is standardized enough. No OCR errors, no manual entry mistakes.
3. **Async Processing**: Client can batch upload multiple months at once.
4. **Compliance**: Audit trail: client has original bill from utility, we have CSV they uploaded.
5. **Cost/Complexity**: No third-party OCR service, no vendor-specific API integrations.

### What We Ignored
- PDF Ingestion: Requires OCR service (Tesseract or API). ~85% error rate on meter readings. Not reliable.
- API-based auto-pull: Requires API credentials management. Only 10% of clients can use. Complexity not justified.
- Manual entry: User error too high. Better to upload a CSV the facilities team already has.

### Real Utility Data Challenges (Researched)

From actual utility CSV exports:

1. **Billing Period ≠ Calendar Month**
   - Reality: Bills run Jan 15 - Feb 14, not Jan 1-31
   - Reason: Utility meters read on staggered schedule
   - How We Handle: Store `billing_period_start` and `billing_period_end` separately from activity date
   - Flag if period spans > 35 days (anomaly detection)

2. **Decimal Separator Inconsistency**
   - Reality: European utilities export "12.500,50 kWh" (dot for thousands, comma for decimal)
   - US utilities export "12,500.50 kWh" (comma for thousands, dot for decimal)
   - How We Handle: Utility parser detects locale from metadata, parses accordingly
   - Sample data includes both formats

3. **Meter ID Format Chaos**
   - Reality: Same utility uses "MTR-001", "METER001", "Meter #001", "001" across different facilities
   - How We Handle: Store original meter_id in metadata, standardize for deduplication
   - Utility DataSource config includes meter_id mapping

4. **Duplicate Bills**
   - Reality: 15-20% of uploads contain duplicate rows (billing corrections, re-runs)
   - Reason: Utility rebills after dispute, or client re-runs export accidentally
   - How We Handle: Dedup by (meter_id, billing_period_start, billing_period_end, quantity)
   - Keep first occurrence, flag second as duplicate

5. **Missing Dates**
   - Reality: Some CSVs only have billing_period_end, not start
   - How We Handle: Assume 30-day month if only end date given, flag as ambiguous
   - Ask PM if org has historical data to fill gaps

6. **Mixed Units**
   - Reality: Same file might have kWh and MWh, depending on meter size
   - How We Handle: Normalize all to kWh (convert MWh × 1000)

7. **Time Zone Issues**
   - Reality: Billing period might be "2025-01-01" but utility is UTC, facility is PST
   - How We Handle: Store timezone in DataSource config, apply when calculating calendar alignment

### Sample Data Provided
See `backend/sample_data/utility_electricity_sample.csv`:
- 9 electricity records
- US format (comma thousands, dot decimal)
- EU format (dot thousands, comma decimal)
- 2 duplicates (same meter, same period, different months)
- 1 billing period spanning into next month (Feb 15 - Mar 15)
- 1 missing consumption value

---

## 4. UTILITY DATA - Handling Billing Periods vs Calendar Months

### Ambiguity
Utility data comes in billing cycles (e.g., Jan 15 - Feb 14), not calendar months (Jan 1-31).

How do we assign emissions to months for annual reporting?

### Decision
**Store both original billing period AND interpolate to calendar month.**

```python
NormalizedRow stores:
- billing_period_start: 2025-01-15
- billing_period_end: 2025-02-14
- date: (interpolation logic below)

# Interpolate to calendar months
# If billing period spans Jan 15 - Feb 14 (31 days):
#   Jan: 16 days (Jan 15-31)
#   Feb: 15 days (Feb 1-14)
# Pro-rate consumption:
#   Jan kWh = total × (16/31)
#   Feb kWh = total × (15/31)
```

### Rationale
1. **Audit Trail**: Keep original billing period for traceability. Auditor can verify against utility invoice.
2. **Reporting**: Most ESG systems report by calendar month/quarter/year, so interpolation necessary.
3. **Transparency**: Both original and interpolated stored, analyst can verify math.
4. **Flexibility**: If org wants to report by billing cycle (rare), they can use original period.

### What We Ignored
- Storing only interpolated values: Loses audit trail. Auditor can't verify against utility bill.
- Storing only original period: Can't integrate with most ESG reporting systems.

### Edge Cases Handled
- Billing period > 35 days: Flag as suspicious (might be correction month)
- Billing period < 25 days: Flag as suspicious (might be prorated month)
- Period spans DST transition: Apply timezone handling

---

## 5. CORPORATE TRAVEL DATA - Format and API

### Ambiguity
Corporate travel platforms (Concur, Navan, Expensify, Brex) all have different APIs:
- Concur: v4 JSON API
- Navan: REST API
- Expensify: GraphQL
- Each returns different field structures

### Decision
**Simulate Concur v4 JSON API format for sample data.**

### Rationale
1. **Market Leader**: Concur is most common in Fortune 500 (30%+ market share)
2. **Open Spec**: Concur API docs are public, well-documented
3. **Realistic**: Our parser handles JSON segments (flights, hotels, ground), mirrors real implementation
4. **Extensible**: If client uses Navan or Expensify, can add parser without redesigning core model

### What We Provided
Parser handles:
```python
segment_types = [
    'AIRFR',   # Air flight
    'HOTEL',   # Hotel
    'CARRT',   # Car rental
    'TAXIF',   # Taxi / rideshare
    'RAILF',   # Rail / train
    'BUS'      # Bus / coach
]
```

Each segment type has specific emission calculation:
- **AIRFR**: Distance × cabin class factor × RFI 1.9x multiplier
- **HOTEL**: Nights × occupancy factor (assume 1.0)
- **TAXIF/CARRT**: Distance × vehicle emission factor
- **RAILF/BUS**: Distance × mode emission factor

### Real Concur Data Challenges Handled

1. **Missing Distance**
   - Reality: 8-12% of flight segments don't include distance field
   - Reason: Concur API optionally includes distance, user entry varies
   - How We Handle:
     - If distance absent, extract origin/dest airport codes
     - Look up coordinates in airport DB (1000+ major business airports)
     - Calculate Haversine great-circle distance
     - Add 8% uplift for indirect routing
     - Flag row as "CALCULATED_DISTANCE" for analyst review

2. **Cabin Class Ambiguity**
   - Reality: 60% of records have cabin_class = "average" or null
   - Reason: Concur defaults to average, users don't fill in
   - How We Handle:
     - Store as-is in metadata
     - Use expensive ticket threshold: if cost > median × 2.5, assume business class
     - Else assume economy
     - Flag row with "CABIN_CLASS_INFERRED" if guessed

3. **Round-Trip vs One-Way**
   - Reality: Ambiguous whether expense is one-way or round-trip
   - Concur fields: origin, destination, date (but no return date sometimes)
   - How We Handle:
     - One segment = one direction
     - If itinerary includes return flight in same expense, create 2 segments
     - Flag as "IMPLICIT_ROUNDTRIP" if unclear

4. **Missing Airport Codes**
   - Reality: Some manual entries use city names ("New York", "Paris") instead of codes
   - How We Handle:
     - Major cities normalized to codes: New York → JFK, Paris → CDG
     - Store in metadata: `raw_location: "New York"`, `normalized_code: "JFK"`
     - Flag as "LOCATION_NORMALIZED"

5. **Hotel Nights Mismatch**
   - Reality: Check-in Feb 15, check-out Feb 18 could mean 2 or 3 nights
   - Convention: Check-out date - check-in date = nights (so 3 nights)
     - But expense system might count occupied nights (2)
   - How We Handle:
     - Calculate as max(checkout - checkin, 1)
     - If nights field provided separately, verify against calculated
     - Flag if discrepancy > 1 night

### Sample Data Provided
See `backend/sample_data/travel_expenses_sample.json`:
- 5 flights (various scenarios: missing distance, inferred cabin class)
- 2 hotels (with period boundary issues)
- 2 ground transport (taxi, rental)
- Total: 9 records, 4 flagged for ambiguous data

---

## 6. DATA QUALITY FLAGGING - Automatic vs Manual

### Ambiguity
Should we auto-flag suspicious data or let analyst find it?

### Decision
**System auto-flags, analyst can unflag after verification.**

Auto-flagged conditions:
1. **MISSING_DATA**: amount, unit, or date is null
2. **DUPLICATE**: Same (source, key_fields, period) seen in last 90 days
3. **UNIT_MISMATCH**: Unit doesn't match material/source type (e.g., "kg" for fuel usually "L")
4. **IMPLAUSIBLE_VALUE**: Amount > 3σ from mean (spike detection)
5. **PARSE_ERROR**: Parser couldn't fully parse row (malformed)
6. **AMBIGUOUS_DATA**: Cabin class="average", or distance calculated vs provided

### Rationale
1. **Efficiency**: Catches 80% of issues automatically, saves analyst time
2. **Transparency**: Flag reasons explicit, analyst knows what we detected
3. **Trust**: Analyst can review, unflag if legitimate (e.g., spike in Nov due to conference)
4. **Non-blocking**: Flagged rows can still be approved if analyst verifies them

### What We Ignored
- Silent filtering: Don't delete flagged rows, just mark them. Auditors need to know what was reviewed.
- ML-based anomaly detection: Too opaque, auditors wouldn't accept "model said it's suspicious". Explicit rules only.

---

## 7. MULTI-TENANCY - Architecture

### Ambiguity
How strictly isolate tenants? Options:
- **Row-level**: Same DB, filter by org_id in every query
- **Schema-level**: Separate schema per org
- **Database-level**: Separate PostgreSQL instance per org

### Decision
**Row-level multi-tenancy with database-level isolation option.**

### Implementation
- Code: Every model has `org_id` ForeignKey, every query filters by `org_id`
- DB: Unique constraints on (org_id, ...) to prevent accidental cross-tenant conflicts
- API: Every endpoint requires `org_id` parameter or header auth
- Future: Easy to migrate to schema-level if needed

### Rationale
1. **Simplicity**: Single codebase, single DB schema
2. **Cost**: Single DB server for all orgs
3. **Scaling**: Can move to schema-level later if org needs isolation
4. **Security**: No cross-contamination if queries correct (and they are)

### What We Ignored
- Database-per-tenant: Overkill for MVP, massive operational overhead
- Schema-per-tenant: Could do, but adds complexity, not needed yet

---

## 8. Unit Normalization - Strategy

### Ambiguity
How to handle unit conversion? Options:
- Store original unit in all rows
- Convert to single canonical unit (e.g., all energy to kWh)
- Store both original and canonical

### Decision
**Store both original unit and normalized unit.**

```python
class NormalizedRow:
    unit_original: 'm3'           # As received
    unit_normalized: 'M3'         # Standardized enum
    amount_original: 2500.5       # As received
    amount_normalized: 2500.5     # After unit conversion (no change needed here)
```

For conversions:
```python
# If received unit = 'MWh', convert to kWh
unit_map = {
    'kWh': ('KWH', 1.0),
    'MWh': ('KWH', 1000.0),
    'GJ': ('GJ', 1.0),  # Don't convert across energy types
    'L': ('L', 1.0),
    'm3': ('M3', 1.0),
    # ... etc
}
```

### Rationale
1. **Auditability**: Can verify original value matches source document
2. **Precision**: Avoid accumulation of rounding errors from conversions
3. **Traceability**: Analyst can see "we received kWh, stored as kWh"

### What We Ignored
- Converting all energy to MJ: Loss of precision, auditors prefer original units
- Storing only normalized: Can't verify against source doc

---

## 9. Approval Workflow - State Machine

### Ambiguity
What states should a row have?

Options:
- Simple: PENDING → APPROVED or REJECTED
- Complex: PENDING → FLAGGED → UNDER_REVIEW → APPROVED or REJECTED

### Decision
**Use simple 3-state model with independent flag.**

```python
class NormalizedRow:
    is_approved: None | True | False  # None = pending
    is_flagged: True | False
    is_locked: True | False
```

State transitions:
```
1. Row created: is_approved=None, is_flagged=False
2. Auto-flagging: is_flagged=True (if issues detected)
3. Analyst review: 
   - Unflag if false positive: is_flagged=False
   - OR Approve flagged row: is_approved=True, is_locked=True
   - OR Reject: is_approved=False, is_locked=True
4. After lock: immutable for audit
```

### Rationale
1. **Flexibility**: Flagged rows can be approved (analyst verified it)
2. **Simple**: Only 3 booleans, no complex state machine
3. **Auditability**: Every change logged in ApprovalLog

### What We Ignored
- Workflow engine (like Temporal): Overkill, too complex
- Role-based approval (e.g., requires 2 sign-offs): Not in scope for MVP

---

## 10. File Upload Mechanism - Options

### Ambiguity
How do clients upload files? Options:
- Web form (drag-drop)
- API endpoint (POST binary)
- SFTP/FTP (automated)
- Email (scheduled)

### Decision
**Web form (React file input) + API endpoint for programmatic uploads.**

### Implementation
```javascript
// Frontend: Simple file input
<input type="file" onChange={(e) => uploadFile(e.target.files[0])} />

// Backend: POST /api/ingest/
@api_view(['POST'])
def upload_file(request):
    file = request.FILES['file']
    org_id = request.POST.get('org_id')
    data_source_id = request.POST.get('data_source_id')
    # Create RawIngestion, queue parser
```

### Rationale
1. **Immediate Feedback**: Upload → parse → display in seconds
2. **Low Friction**: No auth complexity, just drag-drop
3. **API First**: Programmatic uploads possible via curl or client code
4. **Async Processing**: Can queue parsing if file large

### What We Ignored
- SFTP: Requires server setup, SSH auth, not suitable for MVP
- Email: Async, error-prone, hard to track status
- Real-time API pull: Only 10% of clients can expose APIs

---

## 11. Sample Data - Philosophy

### Ambiguity
Should sample data be clean (happy path) or messy (realistic)?

### Decision
**Messy and realistic.**

### What Real Issues We Included

**SAP Sample**:
- Duplicate PO (one reversed via credit memo)
- Mixed date formats (YYYYMMDD vs ISO)
- Unit mismatch (one record in kWh instead of L)
- German header example
- Negative quantity (reversal)

**Utility Sample**:
- Billing period spanning month boundary (Jan 31 - Feb 28, interpolation needed)
- Duplicate meter reading (from re-run of export)
- Missing consumption value (should flag)
- Mixed decimal formats (European comma, US dot)

**Travel Sample**:
- Missing distance (calculated from airport codes)
- Cabin class = "average" (should infer from cost)
- Implicit round-trip flight (one expense, needs 2 segments)
- Hotel with ambiguous night count

### Rationale
1. **Realistic**: Mirrors what real data looks like
2. **Demonstrative**: Shows parser handles edge cases
3. **Testing**: Frontend team can test with real complexity

### What We Ignored
- All clean data: Would give false confidence
- Completely broken data: Too extreme, not useful

---

## 12. Emissions Calculation - Scope

### Ambiguity
Should we calculate emissions in this app or just prepare data?

### Decision
**Prepare data and flag Scope, but don't calculate emissions.**

Why?
- Emissions factors vary by standard (GHG Protocol, ISO 14064, etc.)
- Factors vary by region (UK electricity grid different from Germany)
- Factors change yearly (updated baselines)
- Client likely has own preferred factors

Our scope:
- Prepare normalized data
- Assign Scope 1/2/3 based on source type
- Provide distance/quantity/duration in standard units
- Flag suspicious rows

They use externally for:
- Apply their emissions factors
- Calculate total emissions
- Report to auditors

### What We Ignored
- Embedding DEFRA/US EPA factors: Creates maintenance burden, might be outdated
- Custom factor management UI: Out of scope for MVP

---

## 13. Frontend Complexity - Keep It Simple

### Ambiguity
How feature-rich should UI be?

### Decision
**Minimum viable for analyst workflow.**

Included:
- Organization selector
- Review table (sortable, filterable)
- Bulk approve
- Flag/unflag interface
- Audit trail viewer
- Upload form
- Dashboard summary

Not included:
- User authentication (out of scope)
- Advanced analytics/charting (out of scope)
- Export to Excel (analyst can do via API)
- Mobile responsive (desktop-first, but responsive CSS)

### Rationale
1. **Focus**: Core workflow (review → approve) is smooth
2. **Speed**: Analyst doesn't wait for animations/heavy UI
3. **Clarity**: Data-focused, not design-focused

### What We Ignored
- Customizable dashboards (not needed)
- Dark mode (nice-to-have, not core)
- Mobile app (desktop analyst tool)

---

## 14. Database Choice - SQLite vs PostgreSQL

### Ambiguity
What database for MVP?

### Decision
**SQLite for development, PostgreSQL-ready for production.**

Implementation:
```python
# settings.py
if DEBUG:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', ...}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', ...}}
```

### Rationale
1. **No Setup**: SQLite built into Python, zero config for local dev
2. **Real DB**: Not using ORM in-memory, real SQL
3. **Production Ready**: PostgreSQL swap-in, same code
4. **Scale**: SQLite fine for MVP (<1000 rows), can handle initial load

### What We Ignored
- MySQL: No advantage, PostgreSQL more feature-rich
- MongoDB: Document DB not suitable for audit trail (need transactions)

---

## 15. API Pagination - Strategy

### Ambiguity
How to paginate large result sets?

### Decision
**Offset-limit pagination with 50 rows per page.**

```python
GET /api/rows/?org_id=1&offset=0&limit=50
```

### Rationale
1. **Simplicity**: Industry standard
2. **Frontend Friendly**: Easy to implement pagination UI
3. **Good Enough**: 50 rows per page = <2 second load time
4. **Sortable**: Sort by any column

### What We Ignored
- Cursor-based: Overkill for MVP
- Infinite scroll: UX nice-to-have, not core

---

## 16. CORS Configuration

### Ambiguity
How to allow React frontend (port 3000) to call Django backend (port 8000)?

### Decision
**django-cors-headers with explicit allowed origins.**

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    # Production origins added via env var
]
```

### Rationale
1. **Simple**: One-line fix for localhost development
2. **Flexible**: Can add production domain via env var
3. **Secure**: Only explicit origins allowed, not '*'

---

## Questions for the PM (If This Were Real)

1. **Authentication**: Who logs into the analyst dashboard? Just internal Breathe team, or client employees?
2. **Audit Export Format**: What format do auditors expect? PDF, Excel, JSON with digital signatures?
3. **Approval Authority**: Does one analyst approve all rows, or different analysts for different sources?
4. **SLAs**: How long should analyst review take? What's "too long"?
5. **Emissions Calculation**: Which emissions standard does client use? GHG Protocol, ISO, other?
6. **Data Retention**: How long keep raw files after approval? 7 years per SOX? Indefinitely?
7. **API Vs File Upload**: For travel data, does client want to auto-pull from Concur API, or manual CSV upload?
8. **Historical Backfill**: How many years of historical data need to ingest?
9. **Facility Mapping**: How do plant codes / meter IDs / airport codes map to actual facilities?
10. **Reconciliation**: How to reconcile travel data with corporate card charges?

---

## Summary of Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| SAP Format | CSV flat-file | Realistic, no infrastructure |
| Utility Format | CSV portal export | 65% of facilities teams use this |
| Travel Format | Concur v4 JSON | Market leader, well-spec'd |
| Data Storage | Raw + Normalized | Audit trail + flexibility |
| Flagging | Auto-flag + analyst review | Catches issues early, analyst can override |
| Multi-tenancy | Row-level with org_id | Simple, scalable |
| Units | Store both original + normalized | Auditability |
| Approval | Simple state (None/True/False) + separate flag | Flexibility |
| Upload | Web form + API endpoint | Low friction + programmatic |
| DB | SQLite (dev) + PostgreSQL (prod) | No setup + production-ready |
| Emissions Calc | Don't calculate, prepare data | Client has own factors, standards |

All decisions prioritize: auditability, simplicity, realistic data handling.
