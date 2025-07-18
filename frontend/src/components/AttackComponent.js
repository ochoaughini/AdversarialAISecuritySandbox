import React, { useState, useEffect } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function AttackComponent({ token }) {
  const [inputData, setInputData] = useState('');
  const [fileInput, setFileInput] = useState(null);
  const [attackMethod, setAttackMethod] = useState('');
  const [targetLabel, setTargetLabel] = useState('Neutral');
  const [numWordsToChange, setNumWordsToChange] = useState(3);
  const [maxCandidates, setMaxCandidates] = useState(20);
  const [callbackUrl, setCallbackUrl] = useState('');

  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [selectedModelType, setSelectedModelType] = useState('');

  const [attackId, setAttackId] = useState(null);
  const [attackStatus, setAttackStatus] = useState(null);
  const [attackResult, setAttackResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);

  const attackMethodsByType = {
    'NLP': [{ id: 'textfooler', name: 'TextFooler' }],
    'CV': [{ id: 'fgsm', name: 'FGSM (Mock)' }],
    'Time Series': [{ id: 'noise_injection', name: 'Noise Injection (Mock)' }],
    '': []
  };

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/models`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch models for selection');
        }
        const data = await response.json();
        setModels(data.data);
        if (data.data.length > 0) {
          const defaultModel = data.data.find(m => m.id === 'default-sentiment-model');
          const initialModel = defaultModel || data.data[0];
          setSelectedModelId(initialModel.id);
          setSelectedModelType(initialModel.type);
          setAttackMethod(attackMethodsByType[initialModel.type]?.[0]?.id || '');
        }
      } catch (err) {
        setError(err.message);
      }
    };
    fetchModels();
  }, [token]);

  useEffect(() => {
    const currentModel = models.find(m => m.id === selectedModelId);
    if (currentModel) {
      setSelectedModelType(currentModel.type);
      setInputData('');
      setFileInput(null);
      setAttackMethod(attackMethodsByType[currentModel.type]?.[0]?.id || '');
    }
  }, [selectedModelId, models]);

  const pollAttackStatus = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/attacks/${id}/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get attack status');
      }
      const statusData = await response.json();
      setAttackStatus(statusData);

      if (statusData.status === 'completed' || statusData.status === 'failed') {
        clearInterval(pollingInterval);
        setPollingInterval(null);
        if (statusData.status === 'completed') {
          fetchAttackResults(id);
        } else {
          setError(`Attack failed: ${statusData.error || 'Unknown error'}`);
        }
        setLoading(false);
      }
    } catch (err) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
      setError(`Polling error: ${err.message}`);
      setLoading(false);
    }
  };

  const fetchAttackResults = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/attacks/${id}/results`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get attack results');
      }
      const resultData = await response.json();
      setAttackResult(resultData);
    } catch (err) {
      setError(`Failed to fetch results: ${err.message}`);
    }
  };

  const handleLaunchAttack = async () => {
    if (!selectedModelId) {
      setError('Please select a model to attack.');
      return;
    }
    if (!attackMethod) {
      setError('Please select an attack method.');
      return;
    }

    let processedInput;
    if (selectedModelType === 'CV') {
      if (!fileInput) {
        setError('Please upload an image file for CV model attack.');
        return;
      }
      processedInput = await readFileAsBase64(fileInput);
    } else if (selectedModelType === 'Time Series') {
      try {
        processedInput = inputData.split(',').map(Number);
        if (processedInput.some(isNaN)) {
          throw new Error('Time series data must be comma-separated numbers.');
        }
      } catch (e) {
        setError(e.message);
        return;
      }
    } else { 
      processedInput = inputData;
    }

    if (!processedInput && selectedModelType !== 'CV') {
        setError('Input data cannot be empty.');
        return;
    }

    setError('');
    setAttackResult(null);
    setAttackId(null);
    setAttackStatus(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/attacks/launch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          model_id: selectedModelId,
          attack_method_id: attackMethod,
          input_data: processedInput,
          target_label: selectedModelType === 'NLP' ? targetLabel : undefined,
          attack_parameters: {
            num_words_to_change: parseInt(numWordsToChange),
            max_candidates: parseInt(maxCandidates),
          },
          callback_url: callbackUrl || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to launch attack');
      }

      const data = await response.json();
      setAttackId(data.attack_id);
      setAttackStatus(data);
      
      const interval = setInterval(() => pollAttackStatus(data.attack_id), 2000);
      setPollingInterval(interval);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const readFileAsBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = error => reject(error);
      reader.readAsDataURL(file);
    });
  };

  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  const renderInputArea = () => {
    switch (selectedModelType) {
      case 'CV':
        return (
          <div className="form-group">
            <label htmlFor="imageInputAttack">Upload Image (Base64 simulated):</label>
            <input type="file" id="imageInputAttack" accept="image/*" onChange={(e) => setFileInput(e.target.files[0])} />
            {fileInput && <p>File selected: {fileInput.name}</p>}
          </div>
        );
      case 'Time Series':
        return (
          <div className="form-group">
            <label htmlFor="timeSeriesInputAttack">Time Series Data (comma-separated numbers):</label>
            <input
              type="text"
              id="timeSeriesInputAttack"
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              placeholder="e.g., 10,20,30,150,40,50"
            />
          </div>
        );
      case 'NLP':
      default:
        return (
          <div className="form-group">
            <label htmlFor="attackInput">Input Text:</label>
            <textarea
              id="attackInput"
              rows="5"
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              placeholder="Enter text to attack (e.g., 'This movie was delightful!')"
            ></textarea>
          </div>
        );
    }
  };

  const renderAttackParameters = () => {
    if (selectedModelType === 'NLP') {
      return (
        <>
          <div className="form-group">
            <label htmlFor="targetLabel">Target Label (for targeted attack):</label>
            <select
              id="targetLabel"
              value={targetLabel}
              onChange={(e) => setTargetLabel(e.target.value)}
            >
              <option value="Positive">Positive</option>
              <option value="Negative">Negative</option>
              <option value="Neutral">Neutral</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="numWordsToChange">Max Words to Change:</label>
            <input
              type="number"
              id="numWordsToChange"
              value={numWordsToChange}
              onChange={(e) => setNumWordsToChange(e.target.value)}
              min="1"
              max="10"
            />
          </div>

          <div className="form-group">
            <label htmlFor="maxCandidates">Max Candidates per Word:</label>
            <input
              type="number"
              id="maxCandidates"
              value={maxCandidates}
              onChange={(e) => setMaxCandidates(e.target.value)}
              min="1"
              max="50"
            />
          </div>
        </>
      );
    }
    return <p>No specific attack parameters for {selectedModelType} models yet.</p>;
  };

  return (
    <div>
      <h2>Launch Adversarial Attack</h2>
      <div className="form-group">
        <label htmlFor="modelSelectAttack">Select Target Model:</label>
        <select
          id="modelSelectAttack"
          value={selectedModelId}
          onChange={(e) => setSelectedModelId(e.target.value)}
          disabled={loading || models.length === 0}
        >
          {models.length === 0 ? (
            <option value="">Loading Models...</option>
          ) : (
            models.map(model => (
              <option key={model.id} value={model.id}>
                {model.name} ({model.version} - {model.type})
              </option>
            ))
          )}
        </select>
        {models.length === 0 && !loading && !error && <p className="info-message">No models available. Please register one in the "Models" tab.</p>}
      </div>

      {renderInputArea()}

      <div className="form-group">
        <label htmlFor="attackMethod">Attack Method:</label>
        <select
          id="attackMethod"
          value={attackMethod}
          onChange={(e) => setAttackMethod(e.target.value)}
          disabled={!selectedModelType || attackMethodsByType[selectedModelType]?.length === 0}
        >
          {attackMethodsByType[selectedModelType]?.length > 0 ? (
            attackMethodsByType[selectedModelType].map(method => (
              <option key={method.id} value={method.id}>{method.name}</option>
            ))
          ) : (
            <option value="">No methods for {selectedModelType || 'selected type'}</option>
          )}
        </select>
      </div>

      {renderAttackParameters()}
      
      <div className="form-group">
        <label htmlFor="callbackUrl">Webhook Callback URL (Optional):</label>
        <input
          type="text"
          id="callbackUrl"
          value={callbackUrl}
          onChange={(e) => setCallbackUrl(e.target.value)}
          placeholder="e.g., https://your-webhook-listener.com/attack-complete"
        />
      </div>

      <button className="submit-button" onClick={handleLaunchAttack} disabled={loading || !selectedModelId || !attackMethod}>
        {loading ? 'Launching Attack...' : 'Launch Attack'}
      </button>

      {error && <div className="error-box">{error}</div>}

      {attackId && (
        <div className="result-box">
          <h3>Attack Status: {attackStatus?.status} (Progress: {attackStatus?.perturbation_details?.progress_percentage || 0}%)</h3>
          <p><strong>Attack ID:</strong> {attackId}</p>
          <p><strong>Current Stage:</strong> {attackStatus?.perturbation_details?.current_stage || attackStatus?.status}</p>
          {attackStatus?.error && <p><strong>Error:</strong> {attackStatus.error}</p>}

          {attackResult && (
            <div>
              <h3>Attack Results:</h3>
              <p><strong>Original Input:</strong> {attackResult.original_input}</p>
              <p><strong>Original Prediction:</strong> {attackResult.original_prediction} (Confidence: {attackResult.original_confidence?.toFixed(4)})</p>
              <p><strong>Adversarial Example:</strong> {attackResult.adversarial_example}</p>
              <p><strong>Adversarial Prediction:</strong> {attackResult.adversarial_prediction} (Confidence: {attackResult.adversarial_confidence?.toFixed(4)})</p>
              <p><strong>Attack Success:</strong> {attackResult.attack_success ? 'True' : 'False'}</p>
              {attackResult.perturbation_details && (
                <div>
                  <h4>Perturbation Details:</h4>
                  <pre>{attackResult.perturbation_details.diff}</pre>
                  <p>Words Perturbed: {attackResult.perturbation_details.num_words_perturbed}</p>
                </div>
              )}
              <p><strong>Attack Time:</strong> {attackResult.metrics?.attack_time_seconds?.toFixed(2)} seconds</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AttackComponent;
