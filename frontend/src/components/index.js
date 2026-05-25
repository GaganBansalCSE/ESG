import React from 'react';

export const Header = ({ organizations, selectedOrg, onOrgChange }) => {
  return (
    <div className="header">
      <h1>ESG Data Ingestion Platform</h1>
      <div className="org-selector">
        <label>Organization:</label>
        <select value={selectedOrg} onChange={(e) => onOrgChange(e.target.value)}>
          <option value="">Select Organization</option>
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export const UploadForm = ({ dataSources, onUpload, loading }) => {
  const [dataSourceId, setDataSourceId] = React.useState('');
  const [file, setFile] = React.useState(null);

  const handleUpload = async () => {
    if (!dataSourceId || !file) {
      alert('Please select a data source and file');
      return;
    }

    const orgId = localStorage.getItem('selectedOrgId');
    if (!orgId) {
      alert('Please select an organization first');
      return;
    }

    const formData = new FormData();
    formData.append('org_id', orgId);
    formData.append('data_source_id', dataSourceId);
    formData.append('file', file);

    await onUpload(formData);
    setDataSourceId('');
    setFile(null);
  };

  return (
    <div className="upload-form">
      <select 
        value={dataSourceId} 
        onChange={(e) => setDataSourceId(e.target.value)}
      >
        <option value="">Select Data Source</option>
        {dataSources.map((ds) => (
          <option key={ds.id} value={ds.id}>
            {ds.name} ({ds.get_source_type_display || ds.source_type})
          </option>
        ))}
      </select>
      <input 
        type="file" 
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? 'Uploading...' : 'Upload'}
      </button>
    </div>
  );
};

export const RowApprovalModal = ({ isOpen, row, onApprove, onCancel }) => {
  const [notes, setNotes] = React.useState('');

  const handleApprove = () => {
    onApprove(notes);
    setNotes('');
  };

  return (
    <div className={`modal ${isOpen ? 'active' : ''}`}>
      <div className="modal-content">
        <button className="close-btn" onClick={onCancel}>×</button>
        <div className="modal-header">
          <h2>Approve Row</h2>
        </div>
        {row && (
          <div className="modal-body">
            <div className="form-group">
              <label>Row ID: {row.source_row_id}</label>
            </div>
            <div className="form-group">
              <label>Data Type: {row.data_type}</label>
            </div>
            <div className="form-group">
              <label>Amount: {row.amount_normalized} {row.currency}</label>
            </div>
            <div className="form-group">
              <label htmlFor="notes">Approval Notes:</label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any notes about this approval..."
              />
            </div>
          </div>
        )}
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={handleApprove}>
            Approve
          </button>
          <button className="btn" onClick={onCancel} style={{ background: '#ccc' }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export const FlagModal = ({ isOpen, row, onFlag, onCancel }) => {
  const [reason, setReason] = React.useState('');
  const [notes, setNotes] = React.useState('');

  const handleFlag = () => {
    if (!reason) {
      alert('Please provide a reason for flagging');
      return;
    }
    onFlag(reason, notes);
    setReason('');
    setNotes('');
  };

  return (
    <div className={`modal ${isOpen ? 'active' : ''}`}>
      <div className="modal-content">
        <button className="close-btn" onClick={onCancel}>×</button>
        <div className="modal-header">
          <h2>Flag Row for Review</h2>
        </div>
        {row && (
          <div className="modal-body">
            <div className="form-group">
              <label>Row ID: {row.source_row_id}</label>
            </div>
            <div className="form-group">
              <label htmlFor="reason">Reason for Flag:</label>
              <input
                id="reason"
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g., Missing cabin class, Invalid date format, etc."
              />
            </div>
            <div className="form-group">
              <label htmlFor="flag-notes">Additional Notes:</label>
              <textarea
                id="flag-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any additional context..."
              />
            </div>
          </div>
        )}
        <div className="modal-footer">
          <button className="btn btn-danger" onClick={handleFlag}>
            Flag
          </button>
          <button className="btn" onClick={onCancel} style={{ background: '#ccc' }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
