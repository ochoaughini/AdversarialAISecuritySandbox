from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
import logging
import time
from services.logging_config import setup_logging
from services.metrics_collector import metrics_collector

# Setup logging for this service
logger = setup_logging("api-gateway-service")

app = FastAPI(
    title="AI Adversarial Sandbox - API Gateway",
    description="Central API gateway for model management, prediction, and adversarial attack orchestration.",
    version="1.0.0"
)

# --- Security Configuration ---
SECRET_KEY = "your-super-secret-jwt-key" # CHANGE THIS IN PRODUCTION
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token created for user: {data.get('sub')}")
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT payload missing 'sub' claim.")
            raise credentials_exception
        user_data = {"username": username, "roles": ["admin", "developer"]}
        logger.info(f"User '{username}' authenticated successfully.")
        return user_data
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception(f"Unexpected error during authentication: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication error.")

# --- Pydantic Models for API ---
class Token(BaseModel):
    access_token: str
    token_type: str

class PredictionRequest(BaseModel):
    model_id: str
    input_data: Any

class PredictionResponse(BaseModel):
    model_id: str
    prediction: str
    confidence: float

class ModelSchema(BaseModel):
    id: str
    name: str
    type: str
    version: str
    description: Optional[str] = None
    status: Optional[str] = None
    model_file_url: Optional[str] = None
    metadata: Optional[dict] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    metrics: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AttackResultSchema(BaseModel):
    id: str
    model_id: str
    attack_method_id: str
    original_input: str
    original_prediction: str
    original_confidence: float
    adversarial_example: str
    adversarial_prediction: str
    adversarial_confidence: float
    attack_success: bool
    perturbation_details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Middleware for metrics collection ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    endpoint_base_path = request.url.path
    metrics_collector.observe_http_request(endpoint_base_path, process_time)
    
    logger.debug(f"Request to {endpoint_base_path} completed in {process_time:.4f}s")
    return response

# --- API Endpoints ---

@app.get("/", summary="Root endpoint for API Gateway health check")
async def read_root():
    logger.info("API Gateway health check requested.")
    return {"message": "API Gateway is operational!"}

@app.post("/token", response_model=Token, summary="Obtain JWT token for authentication")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "admin" or form_data.password != "password":
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "roles": ["admin", "developer"]}, expires_delta=access_token_expires
    )
    logger.info(f"Successful login for user: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}

# Metrics endpoint for Prometheus or direct access
@app.get("/metrics", summary="Expose service metrics")
async def get_metrics(request: Request):
    accept_header = request.headers.get("Accept", "")
    if "application/json" in accept_header:
        return metrics_collector.get_metrics_json()
    else:
        return Response(content=metrics_collector.get_metrics_text(), media_type="text/plain")

@app.post("/predict", response_model=PredictionResponse, summary="Get a prediction from an AI model")
async def predict(request: PredictionRequest, current_user: dict = Depends(get_current_user)):
    logger.info(f"Prediction requested for model '{request.model_id}' by user '{current_user['username']}'")
    async with httpx.AsyncClient() as client:
        model_service_url = "http://model-service:8001/predict" 
        try:
            response = await client.post(model_service_url, json=request.dict(), timeout=60)
            response.raise_for_status()
            logger.info(f"Prediction successful for model '{request.model_id}'.")
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Model service connection error during prediction for model '{request.model_id}': {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Model service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Model service returned error during prediction for model '{request.model_id}': {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Model service error: {exc.response.text}")

@app.post("/attacks/launch", response_model=AttackLaunchResponse, summary="Launch an adversarial attack")
async def launch_attack(request: AttackLaunchRequest, current_user: dict = Depends(get_current_user)):
    logger.info(f"Attack launch requested for model '{request.model_id}' with method '{request.attack_method_id}' by user '{current_user['username']}'.")
    async with httpx.AsyncClient() as client:
        attack_service_url = "http://attack-service:8002/launch"
        try:
            response = await client.post(attack_service_url, json=request.dict(), timeout=60)
            response.raise_for_status()
            logger.info(f"Attack initiated successfully by attack service for model '{request.model_id}'. Attack ID: {response.json().get('attack_id')}")
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Attack service connection error during launch for model '{request.model_id}': {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Attack service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Attack service returned error during launch for model '{request.model_id}': {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Attack service error: {exc.response.text}")

@app.get("/attacks/{attack_id}/status", response_model=AttackResultSchema, summary="Get status of an adversarial attack")
async def get_attack_status(attack_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Attack status requested for ID '{attack_id}' by user '{current_user['username']}'.")
    async with httpx.AsyncClient() as client:
        attack_service_url = f"http://attack-service:8002/attacks/{attack_id}/status"
        try:
            response = await client.get(attack_service_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Attack service connection error fetching status for ID '{attack_id}': {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Attack service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Attack service returned error fetching status for ID '{attack_id}': {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Attack service error: {exc.response.text}")

@app.get("/attacks/{attack_id}/results", response_model=AttackResultSchema, summary="Get results of a completed adversarial attack")
async def get_attack_results(attack_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Attack results requested for ID '{attack_id}' by user '{current_user['username']}'.")
    async with httpx.AsyncClient() as client:
        attack_service_url = f"http://attack-service:8002/attacks/{attack_id}/results"
        try:
            response = await client.get(attack_service_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Attack service connection error fetching results for ID '{attack_id}': {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Attack service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Attack service returned error fetching results for ID '{attack_id}': {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Attack service error: {exc.response.text}")

@app.get("/attacks", response_model=Dict[str, Any], summary="List all adversarial attack results with filtering and sorting")
async def list_attacks(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    attack_method_id: Optional[str] = Query(None, description="Filter by attack method ID"),
    status: Optional[str] = Query(None, description="Filter by attack status (e.g., queued, in_progress, completed, failed)"),
    attack_success: Optional[bool] = Query(None, description="Filter by attack success (true/false)"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by (e.g., id, created_at, completed_at, model_id)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)")
):
    logger.info(f"Listing all attacks requested by user '{current_user['username']}'. Filters: model_id={model_id}, method={attack_method_id}, status={status}, success={attack_success}, sort_by={sort_by}, order={sort_order}")
    async with httpx.AsyncClient() as client:
        params = {
            "skip": skip,
            "limit": limit,
            "model_id": model_id,
            "attack_method_id": attack_method_id,
            "status": status,
            "attack_success": attack_success,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        filtered_params = {k: v for k, v in params.items() if v is not None}

        attack_service_url = "http://attack-service:8002/attacks"
        try:
            response = await client.get(attack_service_url, params=filtered_params, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Attack service connection error listing attacks with filters: {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Attack service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Attack service returned error listing attacks with filters: {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Attack service error: {exc.response.text}")

@app.post("/models", response_model=ModelSchema, status_code=status.HTTP_201_CREATED, summary="Upload a new AI model")
async def create_model(model: ModelSchema, current_user: dict = Depends(get_current_user)):
    logger.info(f"Model creation requested for '{model.id}' by user '{current_user['username']}'.")
    async with httpx.AsyncClient() as client:
        model_service_url = "http://model-service:8001/models"
        try:
            response = await client.post(model_service_url, json=model.dict(by_alias=True), timeout=60)
            response.raise_for_status()
            logger.info(f"Model '{model.id}' created successfully.")
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Model service connection error during model creation for '{model.id}': {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Model service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Model service returned error during model creation for '{model.id}': {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Model service error: {exc.response.text}")

@app.get("/models/{model_id}", response_model=ModelSchema, summary="Get model details")
async def get_model(model_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Model details requested for '{model_id}' by user '{current_user['username']}'.")
    async with httpx.AsyncClient() as client:
        model_service_url = f"http://model-service:8001/models/{model_id}"
        try:
            response = await client.get(model_service_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Model service connection error fetching details for '{model_id}': {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Model service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Model service returned error fetching details for '{model_id}': {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Model service error: {exc.response.text}")

@app.get("/models", response_model=Dict[str, Any], summary="List available AI models with filtering and sorting")
async def list_models(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type: Optional[str] = Query(None, description="Filter by model type (e.g., NLP, CV, Time Series)"),
    status: Optional[str] = Query(None, description="Filter by model status (e.g., active, deprecated)"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by (e.g., id, name, created_at, updated_at)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)")
):
    logger.info(f"Listing all models requested by user '{current_user['username']}'. Filters: type={type}, status={status}, sort_by={sort_by}, order={sort_order}")
    async with httpx.AsyncClient() as client:
        params = {
            "skip": skip,
            "limit": limit,
            "type": type,
            "status": status,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        filtered_params = {k: v for k, v in params.items() if v is not None}
        
        model_service_url = "http://model-service:8001/models"
        try:
            response = await client.get(model_service_url, params=filtered_params, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Model service connection error listing models with filters: {exc}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Model service connection error: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"Model service returned error listing models with filters: {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Model service error: {exc.response.text}")
