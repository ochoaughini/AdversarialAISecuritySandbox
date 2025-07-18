from fastapi.testclient import TestClient
from services.api-gateway.main import app, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
import time

client = TestClient(app)

def get_auth_token():
    response = client.post(
        "/token",
        data={"username": "admin", "password": "password"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    raise Exception(f"Failed to get auth token: {response.text}")

TEST_ACCESS_TOKEN = get_auth_token()
HEADERS = {"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API Gateway is operational!"}

def test_login_for_access_token_success():
    response = client.post(
        "/token",
        data={"username": "admin", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_for_access_token_failure():
    response = client.post(
        "/token",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"

def test_protected_endpoint_unauthorized():
    response = client.post(
        "/predict",
        json={"model_id": "test-model", "input_data": "hello"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_predict_endpoint_success_default_model():
    response = client.post(
        "/predict",
        json={"model_id": "default-sentiment-model", "input_data": "This is a wonderful test case!"},
        headers=HEADERS
    )
    assert response.status_code == 200
    assert "prediction" in response.json()
    assert response.json()["prediction"] == "Neutral" 
    assert "confidence" in response.json()

def test_predict_endpoint_success_negative_bias_model():
    response = client.post(
        "/predict",
        json={"model_id": "negative-bias-model", "input_data": "This is a neutral statement."}, 
        headers=HEADERS
    )
    assert response.status_code == 200
    assert "prediction" in response.json()
    assert response.json()["prediction"] == "Negative" 

def test_predict_endpoint_model_not_found():
    response = client.post(
        "/predict",
        json={"model_id": "non-existent-model", "input_data": "dummy"},
        headers=HEADERS
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Model 'non-existent-model' not found."

def test_launch_attack_endpoint_success():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "I love this product, it's great!",
        "target_label": "Negative",
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    response = client.post("/attacks/launch", json=attack_request_data, headers=HEADERS)
    assert response.status_code == 200
    assert "attack_id" in response.json()
    assert response.json()["status"] == "initiated"

def test_get_attack_status_and_results_flow():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "This is an important test sentence.",
        "target_label": "Negative",
        "attack_parameters": {"num_words_to_change": 2, "max_candidates": 10}
    }
    launch_response = client.post("/attacks/launch", json=attack_request_data, headers=HEADERS)
    assert launch_response.status_code == 200
    attack_id = launch_response.json()["attack_id"]

    max_retries = 15
    for i in range(max_retries):
        status_response = client.get(f"/attacks/{attack_id}/status", headers=HEADERS)
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] in ["completed", "failed"]:
            break
        time.sleep(2) 
    else:
        raise Exception(f"Attack {attack_id} did not complete within {max_retries*2} seconds.")

    assert status_data["status"] == "completed"
    assert status_data["attack_id"] == attack_id
    assert status_data["perturbation_details"]["progress_percentage"] == 100
    assert status_data["completed_at"] is not None

    results_response = client.get(f"/attacks/{attack_id}/results", headers=HEADERS)
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["attack_id"] == attack_id
    assert results_data["status"] == "completed"
    assert "original_input" in results_data
    assert "adversarial_example" in results_data
    assert "attack_success" in results_data
    assert results_data["original_input"] == attack_request_data["input_data"]

def test_list_models_no_filters():
    response = client.get("/models", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "data" in data
    assert isinstance(data["data"], list)
    assert data["total"] >= 5 

def test_list_models_filter_by_type():
    response = client.get("/models?type=NLP", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert all(m["type"] == "NLP" for m in data["data"])
    assert any(m["id"] == "default-sentiment-model" for m in data["data"])
    assert not any(m["type"] == "CV" for m in data["data"])

def test_list_models_filter_by_status():
    response = client.get("/models?status=active", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert all(m["status"] == "active" for m in data["data"])

def test_list_models_sort_by_name_asc():
    response = client.get("/models?sort_by=name&sort_order=asc", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    if len(data["data"]) > 1:
        assert data["data"][0]["name"] <= data["data"][1]["name"]

def test_list_models_pagination():
    response_page1 = client.get("/models?limit=2&skip=0", headers=HEADERS)
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    assert len(data_page1["data"]) == 2
    assert data_page1["total"] >= 5

    response_page2 = client.get("/models?limit=2&skip=2", headers=HEADERS)
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    assert len(data_page2["data"]) == 2
    assert data_page2["total"] >= 5

    assert data_page1["data"][0]["id"] != data_page2["data"][0]["id"]

def test_get_model_details():
    response = client.get("/models/default-sentiment-model", headers=HEADERS)
    assert response.status_code == 200
    model_data = response.json()
    assert model_data["id"] == "default-sentiment-model"
    assert model_data["name"] == "Default Sentiment Classifier"

def test_create_new_model():
    new_model_data = {
        "id": "test-new-model-from-api",
        "name": "New Test Model from API",
        "type": "NLP",
        "version": "1.0.0",
        "description": "Model created via API test."
    }
    response = client.post("/models", json=new_model_data, headers=HEADERS)
    assert response.status_code == 201
    assert response.json()["id"] == "test-new-model-from-api"

    list_response = client.get("/models", headers=HEADERS)
    assert list_response.status_code == 200
    assert any(m["id"] == "test-new-model-from-api" for m in list_response.json()["data"])

def test_list_attack_results_no_filters():
    response = client.get("/attacks", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["total"] >= 1 

def test_list_attack_results_filter_by_model_id():
    attack_request_data = {
        "model_id": "negative-bias-model",
        "attack_method_id": "textfooler",
        "input_data": "This is a model filter test.",
        "target_label": "Positive",
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    client.post("/attacks/launch", json=attack_request_data, headers=HEADERS)
    time.sleep(5) 

    response = client.get("/attacks?model_id=negative-bias-model", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert all(a["model_id"] == "negative-bias-model" for a in data["data"])
    assert any("model filter test" in a["original_input"] for a in data["data"])

def test_list_attack_results_filter_by_status():
    attack_request_data = {
        "model_id": "default-sentiment-model",
        "attack_method_id": "textfooler",
        "input_data": "This is a status filter test.",
        "target_label": "Negative",
        "attack_parameters": {"num_words_to_change": 1, "max_candidates": 5}
    }
    launched_attack_response = client.post("/attacks/launch", json=attack_request_data, headers=HEADERS)
    launched_attack_id = launched_attack_response.json()["attack_id"]

    response = client.get(f"/attacks?status=in_progress", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert any(a["id"] == launched_attack_id and (a["status"] == "in_progress" or a["status"] == "completed") for a in data["data"])

def test_list_attack_results_filter_by_success():
    response_success = client.get("/attacks?attack_success=true", headers=HEADERS)
    assert response_success.status_code == 200
    data_success = response_success.json()
    assert all(a["attack_success"] is True for a in data_success["data"])
    assert data_success["total"] >= 1 

    response_failed = client.get("/attacks?attack_success=false", headers=HEADERS)
    assert response_failed.status_code == 200
    data_failed = response_failed.json()
    assert all(a["attack_success"] is False for a in data_failed["data"])

def test_list_attack_results_sort_by_created_at_asc():
    response = client.get("/attacks?sort_by=created_at&sort_order=asc", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    if len(data["data"]) > 1:
        assert data["data"][0]["created_at"] < data["data"][-1]["created_at"]

def test_list_attack_results_pagination():
    for i in range(5): 
        client.post("/attacks/launch", json={"model_id": "default-sentiment-model", "attack_method_id": "textfooler", "input_data": f"Pagination test {i}", "attack_parameters": {}}, headers=HEADERS)
    time.sleep(10) 

    response_page1 = client.get("/attacks?limit=2&skip=0&sort_by=created_at&sort_order=asc", headers=HEADERS)
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    assert len(data_page1["data"]) == 2
    assert data_page1["total"] >= 5 

    response_page2 = client.get("/attacks?limit=2&skip=2&sort_by=created_at&sort_order=asc", headers=HEADERS)
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    assert len(data_page2["data"]) == 2
    assert data_page2["total"] >= 5

    assert data_page1["data"][0]["id"] != data_page2["data"][0]["id"]

def test_get_non_existent_attack_status():
    response = client.get("/attacks/non-existent-attack-id/status", headers=HEADERS)
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
    launch_response = client.post("/attacks/launch", json=attack_request_data, headers=HEADERS)
    attack_id = launch_response.json()["attack_id"]

    response = client.get(f"/attacks/{attack_id}/results", headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["detail"] == "Attack is not yet completed"
