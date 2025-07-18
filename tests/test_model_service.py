from fastapi.testclient import TestClient
from services.model-service.main import app, load_model_instance, PredictionRequest, ModelCreate, model_cache 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import time
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TestingBase = declarative_base()

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer
from datetime import datetime

class Model(TestingBase):
    __tablename__ = "models"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    version = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="active")
    model_file_url = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def override_get_db():
    db = TestingSessionLocal()
    try:
        TestingBase.metadata.create_all(bind=engine)
        models_to_seed = [
            Model(id="default-sentiment-model", name="Default Sentiment", type="NLP", version="1.0.0"),
            Model(id="negative-bias-model", name="Negative Bias", type="NLP", version="1.0.0"),
            Model(id="positive-bias-model", name="Positive Bias", type="NLP", version="1.0.0"),
            Model(id="cv-object-detector", name="CV Detector", type="CV", version="1.0.0"),
            Model(id="ts-anomaly-detector", name="TS Anomaly", type="Time Series", version="1.0.0"),
            Model(id="model-A", name="Model A", type="NLP", version="1.0.0"),
            Model(id="model-B", name="Model B", type="NLP", version="1.0.0"),
            Model(id="model-C", name="Model C", type="NLP", version="1.0.0"),
            Model(id="model-D", name="Model D", type="NLP", version="1.0.0"),
            Model(id="model-E", name="Model E", type="NLP", version="1.0.0"),
            Model(id="model-F", name="Model F", type="NLP", version="1.0.0"),
        ]
        for model_data in models_to_seed:
            db.add(model_data)
        db.commit()
        yield db
    finally:
        db.close()
        TestingBase.metadata.drop_all(bind=engine)

app.dependency_overrides[services.database.get_db] = override_get_db 

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Model Service is operational!"}

def test_create_model():
    model_data = {
        "id": "new-test-model-api-001",
        "name": "API Created Model",
        "type": "NLP",
        "version": "1.0.0",
        "description": "Model created via API call.",
        "status": "active"
    }
    response = client.post("/models", json=model_data)
    assert response.status_code == 201
    created_model = response.json()
    assert created_model["id"] == "new-test-model-api-001"
    assert created_model["name"] == "API Created Model"
    assert "created_at" in created_model

def test_create_duplicate_model_fails():
    model_data = {
        "id": "duplicate-model",
        "name": "Duplicate Model",
        "type": "NLP",
        "version": "1.0.0"
    }
    response1 = client.post("/models", json=model_data)
    assert response1.status_code == 201

    response2 = client.post("/models", json=model_data)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


def test_get_model_details():
    response = client.get("/models/default-sentiment-model")
    assert response.status_code == 200
    assert response.json()["id"] == "default-sentiment-model"
    assert response.json()["name"] == "Default Sentiment"

def test_get_non_existent_model():
    response = client.get("/models/non-existent-model-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Model 'non-existent-model-id' not found."

def test_list_models():
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 10 
    assert isinstance(data["data"], list)
    assert any(m["id"] == "default-sentiment-model" for m in data["data"])

def test_list_models_filter_by_type():
    response = client.get("/models?type=CV")
    assert response.status_code == 200
    data = response.json()
    assert all(m["type"] == "CV" for m in data["data"])
    assert any(m["id"] == "cv-object-detector" for m in data["data"])
    assert not any(m["type"] == "NLP" for m in data["data"])

def test_list_models_sort_by_name_asc():
    response = client.get("/models?sort_by=name&sort_order=asc")
    assert response.status_code == 200
    data = response.json()
    if len(data["data"]) > 1:
        assert data["data"][0]["name"] <= data["data"][1]["name"]

def test_list_models_pagination():
    response_page1 = client.get("/models?limit=2&skip=0")
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    assert len(data_page1["data"]) == 2

    response_page2 = client.get("/models?limit=2&skip=2")
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    assert len(data_page2["data"]) == 2

    assert data_page1["data"][0]["id"] != data_page2["data"][0]["id"]

# --- Tests for Dynamic Prediction Logic (including type validation) ---
def test_predict_default_sentiment_model():
    response = client.post(
        "/predict",
        json={"model_id": "default-sentiment-model", "input_data": "This is a truly neutral sentence."}
    )
    assert response.status_code == 200
    assert response.json()["prediction"] == "Neutral"
    assert response.json()["model_id"] == "default-sentiment-model"

def test_predict_positive_sentiment_model():
    response = client.post(
        "/predict",
        json={"model_id": "positive-bias-model", "input_data": "This is a truly neutral sentence."}
    )
    assert response.status_code == 200
    assert response.json()["prediction"] == "Positive"
    assert response.json()["model_id"] == "positive-bias-model"

def test_predict_negative_sentiment_model():
    response = client.post(
        "/predict",
        json={"model_id": "negative-bias-model", "input_data": "This is a truly neutral sentence."}
    )
    assert response.status_code == 200
    assert response.json()["prediction"] == "Negative"
    assert response.json()["model_id"] == "negative-bias-model"

def test_predict_cv_model():
    response = client.post(
        "/predict",
        json={"model_id": "cv-object-detector", "input_data": "base64encodedcatimage"}
    )
    assert response.status_code == 200
    assert response.json()["prediction"] == "Cat"

def test_predict_ts_model():
    response = client.post(
        "/predict",
        json={"model_id": "ts-anomaly-detector", "input_data": [10, 20, 150, 30]}
    )
    assert response.status_code == 200
    assert response.json()["prediction"] == "Anomaly Detected"

def test_predict_non_existent_model_instance():
    response = client.post(
        "/predict",
        json={"model_id": "non-existent-instance", "input_data": "some text"}
    )
    assert response.status_code == 404
    assert "Model 'non-existent-instance' not found." in response.json()["detail"]

def test_predict_model_with_wrong_input_type():
    response = client.post(
        "/predict",
        json={"model_id": "default-sentiment-model", "input_data": 123}
    )
    assert response.status_code == 400
    assert "Input data for NLP (transformers) model must be a string." in response.json()["detail"]

    response = client.post(
        "/predict",
        json={"model_id": "ts-anomaly-detector", "input_data": "not_a_list"}
    )
    assert response.status_code == 200 
    assert response.json()["prediction"] == "Normal" 

# --- LRU Cache Specific Tests ---
def test_lru_cache_basic_operation():
    model_cache.cache.clear()
    model_cache.capacity = 3 

    client.post("/predict", json={"model_id": "model-A", "input_data": "test"}, headers={}) 
    client.post("/predict", json={"model_id": "model-B", "input_data": "test"}, headers={})
    client.post("/predict", json={"model_id": "model-C", "input_data": "test"}, headers={})

    assert "model-A" in model_cache.cache
    assert "model-B" in model_cache.cache
    assert "model-C" in model_cache.cache
    assert len(model_cache.cache) == 3

    client.post("/predict", json={"model_id": "model-A", "input_data": "test"}, headers={})
    assert list(model_cache.cache.keys())[-1] == "model-A" 

    client.post("/predict", json={"model_id": "model-D", "input_data": "test"}, headers={})
    assert "model-D" in model_cache.cache
    assert "model-B" not in model_cache.cache 
    assert "model-C" in model_cache.cache 
    assert "model-A" in model_cache.cache 

    assert len(model_cache.cache) == 3

def test_lru_cache_capacity_zero():
    original_capacity = model_cache.capacity
    model_cache.capacity = 0
    model_cache.cache.clear()

    client.post("/predict", json={"model_id": "model-A", "input_data": "test"}, headers={})
    assert len(model_cache.cache) == 0 

    model_cache.capacity = original_capacity 

def test_lru_cache_large_capacity_does_not_evict():
    model_cache.cache.clear()
    model_cache.capacity = 100 

    seeded_model_ids = ["default-sentiment-model", "negative-bias-model", "positive-bias-model", "cv-object-detector", "ts-anomaly-detector", "model-A", "model-B", "model-C", "model-D", "model-E", "model-F"]
    for model_id in seeded_model_ids:
        client.post("/predict", json={"model_id": model_id, "input_data": "test"}, headers={})
    
    assert len(model_cache.cache) == len(seeded_model_ids)
    for model_id in seeded_model_ids:
        assert model_id in model_cache.cache
