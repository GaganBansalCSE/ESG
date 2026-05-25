import React, { useEffect, useState } from 'react';
import './styles/App.css';
import { Header, UploadForm, RowApprovalModal, FlagModal } from './components';
import { Dashboard, ReviewTable, AuditTrail } from './pages';
import * as api from './services/api';

function App() {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [dataSources, setDataSources] = useState([]);
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [approvalModal, setApprovalModal] = useState({ isOpen: false, row: null });
  const [flagModal, setFlagModal] = useState({ isOpen: false, row: null });
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      fetchDataSources();
      localStorage.setItem('selectedOrgId', selectedOrg);
    }
  }, [selectedOrg]);

  const fetchOrganizations = async () => {
    try {
      const response = await api.getOrganizations();
      setOrganizations(response.data.results || response.data);
    } catch (error) {
      showMessage('Error fetching organizations', 'error');
    }
  };

  const fetchDataSources = async () => {
    try {
      const response = await api.getDataSources(selectedOrg);
      setDataSources(response.data.results || response.data);
    } catch (error) {
      showMessage('Error fetching data sources', 'error');
    }
  };

  const handleOrgChange = (orgId) => {
    setSelectedOrg(orgId);
  };

  const handleUpload = async (formData) => {
    setLoading(true);
    try {
      await api.uploadFile(formData);
      showMessage('File uploaded and parsed successfully', 'success');
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      showMessage('Error uploading file: ' + (error.response?.data?.error || error.message), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveClick = (row) => {
    setApprovalModal({ isOpen: true, row });
  };

  const handleApprove = async (notes) => {
    try {
      await api.approveRow(approvalModal.row.id, notes);
      showMessage('Row approved successfully', 'success');
      setApprovalModal({ isOpen: false, row: null });
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      showMessage('Error approving row', 'error');
    }
  };

  const handleFlagClick = (row) => {
    setFlagModal({ isOpen: true, row });
  };

  const handleFlag = async (reason, notes) => {
    try {
      await api.flagRow(flagModal.row.id, reason, notes);
      showMessage('Row flagged successfully', 'success');
      setFlagModal({ isOpen: false, row: null });
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      showMessage('Error flagging row', 'error');
    }
  };

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 3000);
  };

  return (
    <div className="app">
      <Header 
        organizations={organizations} 
        selectedOrg={selectedOrg} 
        onOrgChange={handleOrgChange}
      />
      
      <div className="container">
        {message && (
          <div className={messageType}>
            {message}
          </div>
        )}

        <div className="nav-tabs">
          <button 
            className={currentTab === 'dashboard' ? 'active' : ''} 
            onClick={() => setCurrentTab('dashboard')}
          >
            Dashboard
          </button>
          <button 
            className={currentTab === 'upload' ? 'active' : ''} 
            onClick={() => setCurrentTab('upload')}
          >
            Upload Data
          </button>
          <button 
            className={currentTab === 'review' ? 'active' : ''} 
            onClick={() => setCurrentTab('review')}
          >
            Review Data
          </button>
          <button 
            className={currentTab === 'audit' ? 'active' : ''} 
            onClick={() => setCurrentTab('audit')}
          >
            Audit Trail
          </button>
        </div>

        {currentTab === 'dashboard' && (
          <Dashboard selectedOrg={selectedOrg} />
        )}

        {currentTab === 'upload' && (
          <div className="section">
            <h2>Upload Data Files</h2>
            {selectedOrg ? (
              <UploadForm 
                dataSources={dataSources} 
                onUpload={handleUpload}
                loading={loading}
              />
            ) : (
              <p>Please select an organization first</p>
            )}
          </div>
        )}

        {currentTab === 'review' && (
          <ReviewTable 
            selectedOrg={selectedOrg} 
            refresh={refreshTrigger}
            onApproveClick={handleApproveClick}
            onFlagClick={handleFlagClick}
          />
        )}

        {currentTab === 'audit' && (
          <AuditTrail selectedOrg={selectedOrg} />
        )}
      </div>

      <RowApprovalModal 
        isOpen={approvalModal.isOpen}
        row={approvalModal.row}
        onApprove={handleApprove}
        onCancel={() => setApprovalModal({ isOpen: false, row: null })}
      />

      <FlagModal 
        isOpen={flagModal.isOpen}
        row={flagModal.row}
        onFlag={handleFlag}
        onCancel={() => setFlagModal({ isOpen: false, row: null })}
      />
    </div>
  );
}

export default App;
