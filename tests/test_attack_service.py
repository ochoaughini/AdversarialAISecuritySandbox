from fastapi.testclient import TestClient
from services.attack-service.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import time
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TestingBase = declarative_base()

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer

class AttackResult(TestingBase):
    __tablename__ = "attack_results"
    id = Column(String, primary_key=True, index=True)
    model_id = Column(String, index=True, nullable=False)
    attack_method_id = Column(String, nullable=False)
    original_input = Column(String, nullable=False)
    original_prediction = Column(String, nullable=False)
    original_confidence = Column(Float, nullable=False)
    adversarial_example = Column(String, nullable=False)
    adversarial_prediction = Column(String, nullable=False)
    adversarial_confidence = Column(Float, nullable=False)
    attack_success = Column(Boolean, nullable=False)
    perturbation_details = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    status = Column(String, default="completed")
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


def override_get_db():
    db = TestingSessionLocal()
    try:
        TestingBase.metadata.create_all(bind=engine)
        yield db
    finally:
        db.close()
        TestingBase.metadata.drop_all(bind=engine)

app.dependency_overrides[services.database.get_db] = override_get_db 


client = TestClient(app)

class MockRemoteModelWrapper:
    def __init__(self):
        self.mock_predictions = {}

    async def __call__(self, text_input_list, model_id: str = "default-sentiment-model"):
        predictions = []
        label_map = {"Negative": 0, "Neutral": 1, "Positive": 2}
        for text_input in text_input_list:
            if "positive_input_mock" in text_input:
                predictions.append(label_map["Positive"])
            elif "negative_input_mock" in text_input:
                predictions.append(label_map["Negative"])
            elif "neutral_input_mock" in text_input:
                predictions.append(label_map["Neutral"])
            elif text_input in self.mock_predictions:
                predictions.append(self.mock_predictions[text_input])
            else:
                predictions.append(label_map["Neutral"]) 
        import numpy as np
        return np.array(predictions)

services.attack-service.main.remote_model_wrapper_instance = MockRemoteModelWrapper()


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Attack Service is operational!"}

def test_launch_attack_endpoint_initial():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "This is a positive_input_mock sentence.",
        "target_label": "Negative",
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    response = client.post("/launch", json=attack_request_data)
    assert response.status_code == 200
    assert "attack_id" in response.json()
    assert response.json()["status"] == "initiated"
    assert response.json()["message"] == "Attack initiated successfully. Check status endpoint for progress."

def test_get_attack_status_after_launch():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "Another positive_input_mock to check status.",
        "target_label": "Negative",
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    launch_response = client.post("/launch", json=attack_request_data)
    attack_id = launch_response.json()["attack_id"]

    max_retries = 15
    for i in range(max_retries):
        status_response = client.get(f"/attacks/{attack_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] in ["completed", "failed"]:
            break
        time.sleep(1) 
    else:
        raise Exception(f"Attack {attack_id} did not complete within {max_retries} seconds.")
    
    assert status_data["status"] == "completed" 
    assert status_data["attack_id"] == attack_id
    assert status_data["perturbation_details"]["progress_percentage"] == 100
    assert status_data["completed_at"] is not None
    assert status_data["original_input"] == attack_request_data["input_data"]
    assert status_data["original_prediction"] == "Positive" 
    assert status_data["adversarial_prediction"] == "Negative" 

def test_get_attack_results_after_completion():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "A final neutral_input_mock for results.",
        "target_label": "Positive", 
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    launch_response = client.post("/launch", json=attack_request_data)
    attack_id = launch_response.json()["attack_id"]

    time.sleep(5) 

    results_response = client.get(f"/attacks/{attack_id}/results")
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["attack_id"] == attack_id
    assert results_data["status"] == "completed"
    assert results_data["original_input"] == attack_request_data["input_data"]
    assert results_data["original_prediction"] == "Neutral" 
    assert results_data["adversarial_prediction"] == "Positive" 
    assert results_data["attack_success"] is True 
    assert "perturbation_details" in results_data
    assert "diff" in results_data["perturbation_details"]
    assert "metrics" in results_data
    assert "attack_time_seconds" in results_data["metrics"]

def test_list_attacks():
    response = client.get("/attacks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["total"] >= 2 
    if data["data"]:
        for attack_result in data["data"]:
            assert "id" in attack_result
            assert "model_id" in attack_result
            assert "status" in attack_result

def test_get_non_existent_attack_status():
    response = client.get("/attacks/non-existent-attack-id/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Attack ID not found"

def test_get_results_for_incomplete_attack():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "This attack will be incomplete.",
        "target_label": "Negative",
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    launch_response = client.post("/launch", json=attack_request_data)
    attack_id = launch_response.json()["attack_id"]

    response = client.get(f"/attacks/{attack_id}/results")
    assert response.status_code == 409
    assert response.json()["detail"] == "Attack is not yet completed"
