import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function HistoricalAttacksComponent({ token }) {
  const [attacks, setAttacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedAttack, setSelectedAttack] = useState(null);

  const [filterModelId, setFilterModelId] = useState('');
  const [filterMethod, setFilterMethod] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSuccess, setFilterSuccess] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalAttacksCount, setTotalAttacksCount] = useState(0);
  const limit = 10;

  const [availableModels, setAvailableModels] = useState([]);
  const [availableAttackMethods, setAvailableAttackMethods] = useState([]);

  useEffect(() => {
    const fetchDropdownData = async () => {
      try {
        const modelsResponse = await fetch(`${API_BASE_URL}/models?limit=1000`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const modelsData = await modelsResponse.json();
        setAvailableModels(modelsData.data);

        setAvailableAttackMethods(['textfooler', 'fgsm', 'noise_injection']); 
      } catch (err) {
        console.error("Failed to fetch dropdown data:", err);
      }
    };
    fetchDropdownData();
  }, [token]);

  useEffect(() => {
    fetchAttacks();
  }, [token, filterModelId, filterMethod, filterStatus, filterSuccess, sortBy, sortOrder, currentPage]);

  const fetchAttacks = async () => {
    setLoading(true);
    setError('');
    const offset = (currentPage - 1) * limit;
    
    const params = new URLSearchParams({
      skip: offset,
      limit: limit,
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    if (filterModelId) params.append('model_id', filterModelId);
    if (filterMethod) params.append('attack_method_id', filterMethod);
    if (filterStatus) params.append('status', filterStatus);
    if (filterSuccess) params.append('attack_success', filterSuccess);

    try {
      const response = await fetch(`${API_BASE_URL}/attacks?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch attack history');
      }
      const data = await response.json();
      setAttacks(data.data);
      setTotalAttacksCount(data.total);
      setTotalPages(Math.ceil(data.total / limit));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const handlePageChange = (page) => {
    if (page > 0 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const renderDiff = (diffString) => {
    if (!diffString) return 'N/A';
    return diffString.replace(/\x1b\[[0-9;]*m/g, '');
  };

  const completedAttacks = attacks.filter(a => a.status === 'completed');
  const successfulAttacksCount = completedAttacks.filter(a => a.attack_success).length;
  const failedAttacksCount = completedAttacks.filter(a => !a.attack_success).length;
  const totalCompletedAttacks = successfulAttacksCount + failedAttacksCount;
  const successRate = totalCompletedAttacks > 0 ? (successfulAttacksCount / totalCompletedAttacks * 100).toFixed(2) : '0.00';

  const avgAttackTime = totalCompletedAttacks > 0 ? 
    (completedAttacks.reduce((sum, a) => sum + (a.metrics?.attack_time_seconds || 0), 0) / totalCompletedAttacks).toFixed(2) : '0.00';
  
  const avgConfidenceDrop = totalCompletedAttacks > 0 ? 
    (completedAttacks.reduce((sum, a) => sum + Math.abs((a.original_confidence || 0) - (a.adversarial_confidence || 0)), 0) / totalCompletedAttacks).toFixed(4) : '0.0000';

  const attackSuccessPieData = [
    { name: 'Successful', value: successfulAttacksCount },
    { name: 'Failed', value: failedAttacksCount },
  ];
  const PIE_COLORS = ['#4CAF50', '#FF5733'];

  const attackMethodDistribution = completedAttacks.reduce((acc, attack) => {
    acc[attack.attack_method_id] = (acc[attack.attack_method_id] || 0) + 1;
    return acc;
  }, {});
  const attackMethodBarData = Object.keys(attackMethodDistribution).map(method => ({
    name: method,
    count: attackMethodDistribution[method]
  }));


  return (
    <div>
      <h2>Attack History</h2>

      <div className="summary-stats">
        <h3>Summary Analytics</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <h4>Total Attacks:</h4>
            <p>{totalAttacksCount}</p>
          </div>
          <div className="stat-card">
            <h4>Completed Attacks:</h4>
            <p>{totalCompletedAttacks}</p>
          </div>
          <div className="stat-card">
            <h4>Successful Attacks:</h4>
            <p>{successfulAttacksCount}</p>
          </div>
          <div className="stat-card">
            <h4>Success Rate:</h4>
            <p>{successRate}%</p>
          </div>
          <div className="stat-card">
            <h4>Avg Attack Time:</h4>
            <p>{avgAttackTime}s</p>
          </div>
          <div className="stat-card">
            <h4>Avg Confidence Drop:</h4>
            <p>{avgConfidenceDrop}</p>
          </div>
        </div>

        <div className="charts-container">
          <div className="chart-card">
            <h4>Attack Success Distribution</h4>
            {totalCompletedAttacks > 0 ? (
              <PieChart width={300} height={200}>
                <Pie
                  data={attackSuccessPieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {attackSuccessPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            ) : <p>No completed attacks for chart.</p>}
          </div>

          <div className="chart-card">
            <h4>Attacks by Method</h4>
            {attackMethodBarData.length > 0 ? (
              <BarChart width={350} height={200} data={attackMethodBarData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            ) : <p>No attack methods for chart.</p>}
          </div>
        </div>
      </div>

      <div className="filter-sort-controls">
        <div className="form-group inline-group">
          <label htmlFor="filterModelId">Filter by Model:</label>
          <select id="filterModelId" value={filterModelId} onChange={(e) => {setFilterModelId(e.target.value); setCurrentPage(1);}}>
            <option value="">All Models</option>
            {availableModels.map(model => (
              <option key={model.id} value={model.id}>{model.name} ({model.id})</option>
            ))}
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="filterMethod">Filter by Method:</label>
          <select id="filterMethod" value={filterMethod} onChange={(e) => {setFilterMethod(e.target.value); setCurrentPage(1);}}>
            <option value="">All Methods</option>
            {availableAttackMethods.map(method => (
              <option key={method} value={method}>{method}</option>
            ))}
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="filterStatus">Filter by Status:</label>
          <select id="filterStatus" value={filterStatus} onChange={(e) => {setFilterStatus(e.target.value); setCurrentPage(1);}}>
            <option value="">All Statuses</option>
            <option value="queued">Queued</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="filterSuccess">Filter by Success:</label>
          <select id="filterSuccess" value={filterSuccess} onChange={(e) => {setFilterSuccess(e.target.value); setCurrentPage(1);}}>
            <option value="">All</option>
            <option value="true">Successful</option>
            <option value="false">Failed</option>
          </select>
        </div>
        <div className="form-group inline-group">
          <label htmlFor="sortBy">Sort By:</label>
          <select id="sortBy" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="created_at">Launched At</option>
            <option value="completed_at">Completed At</option>
            <option value="model_id">Model ID</option>
            <option value="status">Status</option>
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
        <p>Loading attack history...</p>
      ) : error ? (
        <div className="error-box">Error: {error}</div>
      ) : (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>Attack ID</th>
                <th>Model ID</th>
                <th>Method</th>
                <th>Original Prediction</th>
                <th>Adversarial Prediction</th>
                <th>Success</th>
                <th>Status</th>
                <th>Launched At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((attack) => (
                <tr key={attack.id}>
                  <td>{attack.id.substring(0, 8)}...</td>
                  <td>{attack.model_id}</td>
                  <td>{attack.attack_method_id}</td>
                  <td>{attack.original_prediction} ({attack.original_confidence?.toFixed(2)})</td>
                  <td>{attack.adversarial_prediction} ({attack.adversarial_confidence?.toFixed(2)})</td>
                  <td>{attack.attack_success ? '✅' : '❌'}</td>
                  <td>{attack.status}</td>
                  <td>{formatDate(attack.created_at)}</td>
                  <td>
                    <button onClick={() => setSelectedAttack(attack)}>View Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination-controls">
            <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1}>Previous</button>
            <span>Page {currentPage} of {totalPages}</span>
            <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages}>Next</button>
          </div>

          {selectedAttack && (
            <div className="result-box" style={{ marginTop: '30px' }}>
              <h3>Details for Attack ID: {selectedAttack.id.substring(0, 8)}...</h3>
              <p><strong>Original Input:</strong> {selectedAttack.original_input}</p>
              <p><strong>Adversarial Example:</strong> {selectedAttack.adversarial_example}</p>
              <h4>Perturbation Details:</h4>
              <pre>{renderDiff(selectedAttack.perturbation_details?.diff)}</pre>
              <p>Words Perturbed: {selectedAttack.perturbation_details?.num_words_perturbed || 'N/A'}</p>
              <p>Attack Time: {selectedAttack.metrics?.attack_time_seconds?.toFixed(2) || 'N/A'} seconds</p>
              {selectedAttack.error && <p className="error-text">Error: {selectedAttack.error}</p>}
              <button onClick={() => setSelectedAttack(null)}>Close Details</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default HistoricalAttacksComponent;
