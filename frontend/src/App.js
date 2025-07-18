import React, { useState, useEffect } from 'react';
import './App.css';
import PredictionComponent from './components/PredictionComponent';
import AttackComponent from './components/AttackComponent';
import HistoricalAttacksComponent from './components/HistoricalAttacksComponent';
import ModelManagementComponent from './components/ModelManagementComponent';
import LoginComponent from './components/LoginComponent';

function App() {
  const [activeTab, setActiveTab] = useState('predict');
  const [token, setToken] = useState(localStorage.getItem('access_token'));

  useEffect(() => {
    if (token) {
      // Future: validate token expiry here, refresh if needed
    }
  }, [token]);

  const handleLoginSuccess = (newToken) => {
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
  };

  if (!token) {
    return (
      <div className="App">
        <header className="App-header-top">
          <h1>AI Adversarial Sandbox - Professional Edition</h1>
        </header>
        <main className="App-main">
          <LoginComponent onLoginSuccess={handleLoginSuccess} />
        </main>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header-top">
        <h1>AI Adversarial Sandbox - Professional Edition</h1>
        <nav>
          <button 
            className={`nav-button ${activeTab === 'predict' ? 'active' : ''}`} 
            onClick={() => setActiveTab('predict')}
          >
            Predict
          </button>
          <button 
            className={`nav-button ${activeTab === 'attack' ? 'active' : ''}`} 
            onClick={() => setActiveTab('attack')}
          >
            Launch Attack
          </button>
          <button 
            className={`nav-button ${activeTab === 'history' ? 'active' : ''}`} 
            onClick={() => setActiveTab('history')}
          >
            Attack History
          </button>
          <button 
            className={`nav-button ${activeTab === 'models' ? 'active' : ''}`} 
            onClick={() => setActiveTab('models')}
          >
            Models
          </button>
          <button className="nav-button logout-button" onClick={handleLogout}>
            Logout
          </button>
        </nav>
      </header>
      <main className="App-main">
        {activeTab === 'predict' && <PredictionComponent token={token} />}
        {activeTab === 'attack' && <AttackComponent token={token} />}
        {activeTab === 'history' && <HistoricalAttacksComponent token={token} />}
        {activeTab === 'models' && <ModelManagementComponent token={token} />}
      </main>
    </div>
  );
}

export default App;
