# ESG Data Ingestion Platform

A production-quality Django REST + React application for ingesting, parsing, normalizing, and reviewing environmental, social, and governance (ESG) data from multiple sources.

## Overview

This platform provides:

- **Multi-tenant data ingestion** from SAP, utility providers, and corporate travel systems
- **Intelligent data parsing** with unit normalization, German header support, and data quality flagging
- **Interactive review interface** for approving/flagging suspicious data
- **Audit trail** for compliance and data governance
- **Dashboard** with real-time statistics

## Architecture

### Backend (Django REST)

**Key Features:**
- Multi-tenant organization model
- Support for multiple data source types (SAP Fuel/Procurement, Utility Electricity, Corporate Travel)
- Automated data parsing and normalization
- Data validation and flagging for quality issues
- RESTful API with comprehensive filtering and search

**Models:**
- `Organization` - Multi-tenant support
- `DataSource` - Configuration for data sources
- `RawIngestion` - Raw uploaded/pulled data
- `NormalizedRow` - Parsed and normalized data
- `ApprovalLog` - Audit trail

**Parsers:**
- `SAPParser` - Handles SAP CSV with German headers, unit conversion (L, m³, kg, tonnes)
- `UtilityParser` - Handles utility CSV with billing period deduplication
- `TravelParser` - Handles Concur/Navan JSON with segment extraction

### Frontend (React)

**Features:**
- Organization and data source selection
- File upload interface
- Interactive data review table with sorting and filtering
- Approval/flagging modals
- Audit trail viewer
- Real-time dashboard with statistics

## Setup and Installation

### Backend Setup

1. **Install dependencies:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Run migrations:**
```bash
python manage.py migrate
```

3. **Load sample data (optional):**
```bash
python manage.py shell
# Then run the populate_sample_data.py commands or:
```

4. **Create superuser (optional, for Django admin):**
```bash
python manage.py createsuperuser
```

5. **Start the development server:**
```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000/api/`

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start the development server:**
```bash
npm start
```

The app will open at: `http://localhost:3000`

## API Endpoints

### Organizations
- `GET /api/organizations/` - List organizations
- `POST /api/organizations/` - Create organization

### Data Sources
- `GET /api/data-sources/?org_id=<id>` - List data sources for organization
- `POST /api/data-sources/` - Create data source

### Data Ingestion
- `POST /api/raw-ingestions/upload/` - Upload and parse a file
  - Required fields: `org_id`, `data_source_id`, `file`
  - Response: RawIngestion record with parsing results

### Normalized Rows
- `GET /api/rows/?org_id=<id>` - List normalized rows with optional filters:
  - `data_type` - Filter by SAP, UTILITY, TRAVEL
  - `flagged` - true/false
  - `approved` - true/false
  - `start_date`, `end_date` - Date range filtering
- `POST /api/rows/{id}/approve/` - Approve a row
- `POST /api/rows/{id}/flag/` - Flag a row with reason
- `POST /api/rows/{id}/unflag/` - Remove flag

### Approval Logs
- `GET /api/approval-logs/?org_id=<id>` - List audit trail

### Dashboard
- `GET /api/dashboard/stats/?org_id=<id>` - Get dashboard statistics

## Sample Data

Sample data files are included in `backend/sample_data/`:

- **sap_fuel.csv** - SAP fuel procurement data with:
  - German headers (MATNR, WERKS, Menge, MEINS)
  - Unit inconsistencies (L, m³, kg, tonnes)
  - Duplicate rows (data quality issue)
  - Missing values
  
- **utility_electricity.csv** - Utility electricity billing with:
  - Billing periods not aligned to calendar months
  - Decimal separator variations (comma vs dot)
  - Duplicate billing periods (corrections)
  
- **travel_expenses.json** - Corporate travel in Concur/Navan format with:
  - Multiple segment types (AIRFR, HOTEL, TAXIF)
  - Missing cabin classes (flagged)
  - Missing distances (flagged)
  - Round-trip indication

## Data Parsing and Normalization

### SAP Parser
- Detects and normalizes German headers
- Converts units:
  - Fuel: L (liters), m³ (cubic meters), kg (kilograms), tonnes → kg
  - Energy: kWh, MWh, Wh → kWh
- Flags:
  - Missing or inconsistent units
  - Duplicate rows (same material, plant, date, quantity)
  - Invalid dates or prices
  - Unknown currencies

### Utility Parser
- Handles decimal separators (1.000,50 German format)
- Deduplicates by (meter_id, billing_period_start, billing_period_end)
- Flags:
  - Missing meter IDs
  - Billing periods not aligned to calendar months
  - Duplicate billing periods (billing corrections)

### Travel Parser
- Extracts flight, hotel, train, and ground transport segments
- Calculates distances from origin/destination
- Flags:
  - Missing cabin class (affects emission factors)
  - Missing distances
  - Missing hotel locations
  - Missing trip durations

## Usage

### 1. Create an Organization
```bash
curl -X POST http://localhost:8000/api/organizations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company"}'
```

### 2. Create a Data Source
```bash
curl -X POST http://localhost:8000/api/data-sources/ \
  -H "Content-Type: application/json" \
  -d '{
    "org": 1,
    "source_type": "SAP_FUEL",
    "name": "SAP Fuel Data",
    "config": {}
  }'
```

### 3. Upload and Parse Data
```bash
curl -X POST http://localhost:8000/api/raw-ingestions/upload/ \
  -F "org_id=1" \
  -F "data_source_id=1" \
  -F "file=@sample_data/sap_fuel.csv"
```

### 4. Review Data
Visit `http://localhost:3000`, select organization, and use the "Review Data" tab to:
- View normalized rows in a table
- Sort and filter by data type, status, date range
- Approve rows
- Flag suspicious rows

### 5. View Audit Trail
Use the "Audit Trail" tab to see all approvals, flags, and unflaggs with timestamps and user information.

## Data Fields and Scope Classification

### Scope 1 (Direct Emissions)
- SAP fuel data (vehicle fuel, heating)
- On-site energy generation

### Scope 2 (Indirect Energy Emissions)
- Utility electricity consumption
- Purchased steam/heating

### Scope 3 (Other Indirect Emissions)
- Corporate travel (flights, hotels, ground transport)
- Employee commuting
- Waste disposal

## Error Handling

The platform provides detailed error reporting:

- **Parsing errors** are captured and displayed in the RawIngestion error_message field
- **Row-level flags** indicate data quality issues with specific reasons
- **Validation errors** in API responses include detailed error messages

## Development

### Running Tests
```bash
cd backend
python manage.py test
```

### Database Management
```bash
# Create migrations after model changes
python manage.py makemigrations

# View migration status
python manage.py showmigrations

# Migrate specific app
python manage.py migrate core
```

### Django Admin
Access admin interface at `http://localhost:8000/admin/` with superuser credentials.

## Production Deployment

### Backend
- Use environment variables for settings (DEBUG, SECRET_KEY, ALLOWED_HOSTS, DB credentials)
- Use PostgreSQL instead of SQLite
- Set `DEBUG=False`
- Configure proper CORS origins
- Use gunicorn/uWSGI for serving

### Frontend
- Run `npm run build` to create optimized production build
- Deploy static files to CDN or web server
- Configure API_BASE_URL for production environment

## Project Structure

```
.
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── sample_data/
│   │   ├── sap_fuel.csv
│   │   ├── utility_electricity.csv
│   │   └── travel_expenses.json
│   ├── core/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── parsers/
│   │   │   ├── sap_parser.py
│   │   │   ├── utility_parser.py
│   │   │   ├── travel_parser.py
│   │   │   └── validators.py
│   │   └── migrations/
│   └── config/
│       ├── settings.py
│       ├── urls.py
│       └── wsgi.py
└── frontend/
    ├── package.json
    ├── public/
    ├── src/
    │   ├── App.js
    │   ├── index.js
    │   ├── pages/
    │   │   └── index.js
    │   ├── components/
    │   │   └── index.js
    │   ├── services/
    │   │   └── api.js
    │   └── styles/
    │       └── App.css
```

## Troubleshooting

### CORS Errors
Make sure frontend URL is in CORS_ALLOWED_ORIGINS in backend/config/settings.py

### Database Locked
SQLite can have locking issues. Consider using PostgreSQL for development.

### Port Already in Use
- Backend: `python manage.py runserver 8001`
- Frontend: `PORT=3001 npm start`

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `python manage.py test`
4. Submit a pull request

## License

Proprietary - ESG Data Ingestion Platform

## Support

For issues or questions, contact the development team.