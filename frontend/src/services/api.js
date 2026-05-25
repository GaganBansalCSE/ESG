import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Organizations
export const getOrganizations = () => api.get('/organizations/');
export const createOrganization = (data) => api.post('/organizations/', data);

// Data Sources
export const getDataSources = (orgId) => 
  api.get('/data-sources/', { params: { org_id: orgId } });
export const createDataSource = (data) => api.post('/data-sources/', data);

// Raw Ingestions
export const getRawIngestions = (orgId) => 
  api.get('/raw-ingestions/', { params: { org_id: orgId } });
export const uploadFile = (formData) => 
  api.post('/raw-ingestions/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// Normalized Rows
export const getNormalizedRows = (orgId, filters = {}) => 
  api.get('/rows/', { 
    params: { org_id: orgId, ...filters } 
  });

export const approveRow = (rowId, notes = '') => 
  api.post(`/rows/${rowId}/approve/`, { notes });

export const flagRow = (rowId, reason, notes = '') => 
  api.post(`/rows/${rowId}/flag/`, { reason, notes });

export const unflagRow = (rowId, notes = '') => 
  api.post(`/rows/${rowId}/unflag/`, { notes });

// Approval Logs
export const getApprovalLogs = (orgId, filters = {}) => 
  api.get('/approval-logs/', { 
    params: { org_id: orgId, ...filters } 
  });

// Dashboard
export const getDashboardStats = (orgId) => 
  api.get('/dashboard/stats/', { params: { org_id: orgId } });

export default api;
