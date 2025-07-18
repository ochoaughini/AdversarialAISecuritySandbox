import React, { useState, useEffect } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function ModelManagementComponent({ token }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newModel, setNewModel] = useState({
    id: '', name: '', type: 'NLP', version: '1.0.0', description: '', model_file_url: ''
  });
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState('');

  const [filterType, setFilterType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 10;

  useEffect(() => {
    fetchModels();
  }, [token, filterType, filterStatus, sortBy, sortOrder, currentPage]);

  const fetchModels = async () => {
    setLoading(true);
    setError('');
    const offset = (currentPage - 1) * limit;
    
    const params = new URLSearchParams({
      skip: offset,
      limit: limit,
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    if (filterType) params.append('type', filterType);
    if (filterStatus) params.append('status', filterStatus);

    try {
      const response = await fetch(`${API_BASE_URL}/models?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch models');
      }
      const data = await response.json();
      setModels(data.data);
      setTotalPages(Math.ceil(data.total / limit));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNewModelChange = (e) => {
    const { name, value } = e.target;
    setNewModel(prev => ({ ...prev, [name]: value }));
  };

  const handleUploadModel = async (e) => {
    e.preventDefault();
    setUploading(true);
    setError('');
    setUploadSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/models`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(newModel),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload model');
      }

      setUploadSuccess('Model registered successfully!');
      setNewModel({ id: '', name: '', type: 'NLP', version: '1.0.0', description: '', model_file_url: '' });
      fetchModels();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handlePageChange = (page) => {
    if (page > 0 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  return (
    <div>
      <h2>Model Management</h2>

      <h3>Register New Model</h3>
      <form onSubmit={handleUploadModel}>
        <div className="form-group">
          <label htmlFor="modelId">Model ID:</label>
          <input type="text" id="modelId" name="id" value={newModel.id} onChange={handleNewModelChange} required />
        </div>
        <div className="form-group">
          <label htmlFor="modelName">Name:</label>
          <input type="text" id="modelName" name="name" value={newModel.name} onChange={handleNewModelChange} required />
        </div>
        <div className="form-group">
          <label htmlFor="modelType">Type:</label>
          <select id="modelType" name="type" value={newModel.type} onChange={handleNewModelChange}>
            <option value="NLP">NLP</option>
            <option value="CV">CV</option>
            <option value="Time Series">Time Series</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="modelVersion">Version:</label>
          <input type="text" id="modelVersion" name="version" value={newModel.version} onChange={handleNewModelChange} required />
        </div>
        <div className="form-group">
          <label htmlFor="modelDescription">Description:</label>
          <textarea id="modelDescription" name="description" value={newModel.description} onChange={handleNewModelChange}></textarea>
        </div>
        <div className="form-group">
          <label htmlFor="modelFileUrl">Model File URL (e.g., S3 path):</label>
          <input type="text" id="modelFileUrl" name="model_file_url" value={newModel.model_file_url} onChange={handleNewModelChange} />
        </div>
        <button type="submit" className="submit-button" disabled={uploading}>
          {uploading ? 'Registering...' : 'Register Model'}
        </button>
        {uploadSuccess && <p style={{ color: 'green', marginTop: '10px' }}>{uploadSuccess}</p>}
      </form>

      <h3 style={{ marginTop: '40px' }}>Available Models</h3>

      <div className="filter-sort-controls">
        <div className="form-group inline-group">
          <label htmlFor="filterType">Filter by Type:</label>
          <select id="filterType" value={filterType} onChange={(e) => {setFilterType(e.target.value); setCurrentPage(1);}}>
            <option value="">All</option>
            <option value="NLP">NLP</option>
            <option value="CV">CV</option>
            <option value="Time Series">Time Series</option>
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="filterStatus">Filter by Status:</label>
          <select id="filterStatus" value={filterStatus} onChange={(e) => {setFilterStatus(e.target.value); setCurrentPage(1);}}>
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="deprecated">Deprecated</option>
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="sortBy">Sort By:</label>
          <select id="sortBy" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="created_at">Created At</option>
            <option value="name">Name</option>
            <option value="type">Type</option>
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="sortOrder">Order:</label>
          <select id="sortOrder" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p>Loading models...</p>
      ) : models.length === 0 ? (
        <p>No models found matching your criteria.</p>
      ) : (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Type</th>
                <th>Version</th>
                <th>Status</th>
                <th>Registered At</th>
              </tr>
            </thead>
            <tbody>
              {models.map(model => (
                <tr key={model.id}>
                  <td>{model.id}</td>
                  <td>{model.name}</td>
                  <td>{model.type}</td>
                  <td>{model.version}</td>
                  <td>{model.status}</td>
                  <td>{new Date(model.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination-controls">
            <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1}>Previous</button>
            <span>Page {currentPage} of {totalPages}</span>
            <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages}>Next</button>
          </div>
        </>
      )}
    </div>
  );
}

export default ModelManagementComponent;
