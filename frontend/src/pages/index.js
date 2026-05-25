import React, { useEffect, useState } from 'react';
import * as api from '../services/api';

export const Dashboard = ({ selectedOrg }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedOrg) {
      fetchStats();
    }
  }, [selectedOrg]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await api.getDashboardStats(selectedOrg);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedOrg) {
    return <div className="section"><p>Please select an organization</p></div>;
  }

  if (loading) {
    return <div className="loading">Loading stats...</div>;
  }

  if (!stats) {
    return <div className="section"><p>No data available</p></div>;
  }

  return (
    <div className="dashboard">
      <div className="stat-card">
        <div className="label">Total Rows</div>
        <div className="value">{stats.total_rows}</div>
      </div>
      <div className="stat-card">
        <div className="label">Approved</div>
        <div className="value" style={{ color: '#4caf50' }}>{stats.approved_rows}</div>
      </div>
      <div className="stat-card">
        <div className="label">Flagged</div>
        <div className="value" style={{ color: '#f44336' }}>{stats.flagged_rows}</div>
      </div>
      <div className="stat-card">
        <div className="label">Pending</div>
        <div className="value" style={{ color: '#ff9800' }}>{stats.pending_rows}</div>
      </div>
      <div className="stat-card">
        <div className="label">Total Amount</div>
        <div className="value" style={{ fontSize: '24px' }}>
          ${stats.total_amount ? stats.total_amount.toFixed(2) : '0.00'}
        </div>
      </div>
      <div className="stat-card">
        <div className="label">Recent Uploads</div>
        <div className="value">{stats.recent_uploads}</div>
      </div>
    </div>
  );
};

export const ReviewTable = ({ selectedOrg, refresh }) => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    data_type: '',
    flagged: '',
    approved: '',
    start_date: '',
    end_date: '',
  });
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    if (selectedOrg) {
      fetchRows();
    }
  }, [selectedOrg, filters, sortBy, sortOrder, refresh]);

  const fetchRows = async () => {
    setLoading(true);
    try {
      const filterParams = Object.entries(filters).reduce((acc, [key, val]) => {
        if (val) acc[key] = val;
        return acc;
      }, {});
      filterParams.ordering = `${sortOrder === 'asc' ? '' : '-'}${sortBy}`;

      const response = await api.getNormalizedRows(selectedOrg, filterParams);
      setRows(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching rows:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters({ ...filters, [field]: value });
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  if (!selectedOrg) {
    return <div className="section"><p>Please select an organization</p></div>;
  }

  return (
    <div className="section">
      <h2>Review Data</h2>
      
      <div className="filters">
        <select 
          value={filters.data_type} 
          onChange={(e) => handleFilterChange('data_type', e.target.value)}
        >
          <option value="">All Data Types</option>
          <option value="SAP">SAP</option>
          <option value="UTILITY">Utility</option>
          <option value="TRAVEL">Travel</option>
        </select>

        <select 
          value={filters.flagged} 
          onChange={(e) => handleFilterChange('flagged', e.target.value)}
        >
          <option value="">All Status</option>
          <option value="true">Flagged</option>
          <option value="false">Not Flagged</option>
        </select>

        <select 
          value={filters.approved} 
          onChange={(e) => handleFilterChange('approved', e.target.value)}
        >
          <option value="">All Approval Status</option>
          <option value="true">Approved</option>
          <option value="false">Not Approved</option>
        </select>

        <input 
          type="date" 
          value={filters.start_date}
          onChange={(e) => handleFilterChange('start_date', e.target.value)}
          placeholder="Start Date"
        />

        <input 
          type="date" 
          value={filters.end_date}
          onChange={(e) => handleFilterChange('end_date', e.target.value)}
          placeholder="End Date"
        />

        <button onClick={fetchRows}>Refresh</button>
      </div>

      {loading ? (
        <div className="loading">Loading rows...</div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('source_row_id')}>Row ID {sortBy === 'source_row_id' && (sortOrder === 'asc' ? '↑' : '↓')}</th>
                <th onClick={() => handleSort('data_type')}>Type {sortBy === 'data_type' && (sortOrder === 'asc' ? '↑' : '↓')}</th>
                <th onClick={() => handleSort('amount_normalized')}>Amount {sortBy === 'amount_normalized' && (sortOrder === 'asc' ? '↑' : '↓')}</th>
                <th>Unit</th>
                <th onClick={() => handleSort('date')}>Date {sortBy === 'date' && (sortOrder === 'asc' ? '↑' : '↓')}</th>
                <th>Location</th>
                <th>Scope</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.source_row_id}</td>
                  <td>{row.data_type}</td>
                  <td>{row.amount_normalized ? row.amount_normalized.toFixed(2) : '-'}</td>
                  <td>{row.unit_normalized || '-'}</td>
                  <td>{row.date || '-'}</td>
                  <td>{row.location || '-'}</td>
                  <td>
                    {row.scope && (
                      <span className="scope-badge">Scope {row.scope}</span>
                    )}
                  </td>
                  <td>
                    {row.flagged ? (
                      <span className="flag-badge flagged">Flagged</span>
                    ) : row.approved_by ? (
                      <span className="flag-badge approved">Approved</span>
                    ) : (
                      <span className="flag-badge pending">Pending</span>
                    )}
                  </td>
                  <td>
                    <div className="actions">
                      {!row.approved_by && (
                        <button className="btn btn-success" onClick={() => onApproveClick && onApproveClick(row)}>
                          Approve
                        </button>
                      )}
                      {!row.flagged && (
                        <button className="btn btn-warning" onClick={() => onFlagClick && onFlagClick(row)}>
                          Flag
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export const AuditTrail = ({ selectedOrg }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedOrg) {
      fetchLogs();
    }
  }, [selectedOrg]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await api.getApprovalLogs(selectedOrg);
      setLogs(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching logs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedOrg) {
    return <div className="section"><p>Please select an organization</p></div>;
  }

  return (
    <div className="section">
      <h2>Approval Audit Trail</h2>
      
      {loading ? (
        <div className="loading">Loading audit trail...</div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Row ID</th>
                <th>Action</th>
                <th>User</th>
                <th>Timestamp</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.normalized_row}</td>
                  <td>
                    <span 
                      className={`flag-badge ${
                        log.action === 'APPROVED' ? 'approved' : 
                        log.action === 'FLAGGED' ? 'flagged' : 'pending'
                      }`}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td>{log.user_name || 'System'}</td>
                  <td>{new Date(log.timestamp).toLocaleString()}</td>
                  <td>{log.notes || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
