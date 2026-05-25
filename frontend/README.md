# Frontend - ESG Data Ingestion UI

React-based user interface for the ESG Data Ingestion platform.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (opens http://localhost:3000)
npm start

# Build for production
npm run build
```

## Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── App.js              # Main app component with tab navigation
│   ├── index.js            # React entry point
│   ├── index.css           # Base styles
│   ├── components/
│   │   └── index.js        # Header, UploadForm, Modals
│   ├── pages/
│   │   └── index.js        # Dashboard, ReviewTable, AuditTrail
│   ├── services/
│   │   └── api.js          # API client (axios)
│   └── styles/
│       └── App.css         # Main stylesheet
├── package.json
└── README.md
```

## Components

### Header
Organization selector and branding. Persists selected org to localStorage.

### UploadForm
File upload for data sources. Creates FormData and calls API upload endpoint.

Features:
- Data source selector
- File input
- Upload button with loading state
- Error handling

### RowApprovalModal
Modal dialog for approving a normalized row with optional notes.

### FlagModal
Modal dialog for flagging suspicious rows with reason and notes.

## Pages

### Dashboard
Statistics and overview including total rows, approved, flagged, pending, amounts, and scope distribution.

### ReviewTable
Interactive table for reviewing normalized rows with sorting, filtering, and approval/flagging actions.

### AuditTrail
Approval history with user, action, timestamp, and notes.

## Features

**Dashboard:**
- Real-time statistics
- Data type breakdown
- Scope 1/2/3 distribution
- Total amount calculation

**Review Table:**
- Sortable columns
- Advanced filtering (type, status, date range)
- Pagination (50 rows/page)
- Approve/Flag actions
- Status indicators

**Audit Trail:**
- Complete approval history
- User tracking
- Action logging
- Notes and timestamps

## Running Locally

1. **Ensure backend is running:**
```bash
cd backend
python manage.py runserver
```

2. **In another terminal:**
```bash
cd frontend
npm install
npm start
```

3. **Browser opens automatically to:**
```
http://localhost:3000
```

## Building for Production

```bash
npm run build
```

Creates optimized production build in `build/` directory.

## Configuration

Backend API URL is configured in `src/services/api.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

For production, use environment variables:
```
REACT_APP_API_URL=https://api.esg.example.com/api
```

## Workflow

1. **Select Organization** - Choose org from dropdown in header
2. **Upload Data** - Go to "Upload Data" tab, select source, upload file
3. **Review Data** - Go to "Review Data" tab, sort/filter, approve/flag rows
4. **Check Audit Trail** - Go to "Audit Trail" tab to see approval history
5. **Monitor Dashboard** - Dashboard shows real-time statistics

## Error Handling

- API errors displayed in error banner
- Upload errors shown in red
- Network errors displayed as connection warnings
- Validation errors shown inline or in modals

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers

## Troubleshooting

### CORS Errors
Ensure backend has `http://localhost:3000` in CORS_ALLOWED_ORIGINS

### File Upload Not Working
- Check file format matches data source type
- Check browser console for errors
- Verify backend is running

### Data Not Refreshing
- Click "Refresh" button in Review Data tab
- Check browser console for API errors
- Verify organization is selected

## Dependencies

- **React 18**: UI library
- **Axios**: HTTP client
- **CSS**: No additional CSS frameworks (vanilla CSS with responsive design)

## Development

Key scripts:
- `npm start` - Development server
- `npm run build` - Production build
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App (irreversible)

See [Create React App documentation](https://create-react-app.dev) for more details.
