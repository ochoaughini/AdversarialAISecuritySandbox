import React, { useState, useEffect } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function PredictionComponent({ token }) {
  const [inputData, setInputData] = useState('');
  const [fileInput, setFileInput] = useState(null);
  const [predictionResult, setPredictionResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [selectedModelType, setSelectedModelType] = useState('');

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
    }
  }, [selectedModelId, models]);


  const handlePredict = async () => {
    if (!selectedModelId) {
      setError('Please select a model.');
      return;
    }
    
    let processedInput;
    if (selectedModelType === 'CV') {
      if (!fileInput) {
        setError('Please upload an image file for CV model.');
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
    setPredictionResult(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ model_id: selectedModelId, input_data: processedInput }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get prediction');
      }

      const data = await response.json();
      setPredictionResult(data);
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

  const renderInputArea = () => {
    switch (selectedModelType) {
      case 'CV':
        return (
          <div className="form-group">
            <label htmlFor="imageInput">Upload Image (Base64 simulated):</label>
            <input type="file" id="imageInput" accept="image/*" onChange={(e) => setFileInput(e.target.files[0])} />
            {fileInput && <p>File selected: {fileInput.name}</p>}
          </div>
        );
      case 'Time Series':
        return (
          <div className="form-group">
            <label htmlFor="timeSeriesInput">Time Series Data (comma-separated numbers):</label>
            <input
              type="text"
              id="timeSeriesInput"
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
            <label htmlFor="predictionInput">Input Text:</label>
            <textarea
              id="predictionInput"
              rows="5"
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              placeholder="Enter text for prediction (e.g., 'This product is amazing!')"
            ></textarea>
          </div>
        );
    }
  };

  return (
    <div>
      <h2>Get Model Prediction</h2>
      <div className="form-group">
        <label htmlFor="modelSelect">Select Model:</label>
        <select
          id="modelSelect"
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

      <button className="submit-button" onClick={handlePredict} disabled={loading || !selectedModelId}>
        {loading ? 'Predicting...' : 'Get Prediction'}
      </button>

      {error && <div className="error-box">{error}</div>}

      {predictionResult && (
        <div className="result-box">
          <h3>Prediction Result:</h3>
          <p><strong>Model ID:</strong> {predictionResult.model_id}</p>
          <p><strong>Prediction:</strong> {predictionResult.prediction}</p>
          <p><strong>Confidence:</strong> {predictionResult.confidence.toFixed(4)}</p>
        </div>
      )}
    </div>
  );
}

export default PredictionComponent;
