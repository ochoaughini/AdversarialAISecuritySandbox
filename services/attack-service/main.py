from fastapi import FastAPI, HTTPException, status, Depends, Query, Request, Response
from pydantic import BaseModel
import uuid
import asyncio
import httpx
from datetime import datetime
import os
import time
from sqlalchemy.orm import Session
from services.database import AttackResult, get_db, create_db_and_tables
from typing import List, Optional, Any, Dict
import logging
from services.logging_config import setup_logging
from services.metrics_collector import metrics_collector

# Setup logging for this service
logger = setup_logging("attack-service")

# --- Webhook Retry Configuration ---
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", 3))
WEBHOOK_RETRY_DELAY_SECONDS = int(os.getenv("WEBHOOK_RETRY_DELAY_SECONDS", 1))

# --- TextAttack Integration ---
from textattack.models.wrappers import ModelWrapper
from textattack.attack_recipes import TextFoolerJin2019
from textattack.constraints.semantics.language_models import GPT2LM
from textattack.shared import AttackedText
from textattack.goal_functions import UntargetedClassification, TargetedClassification
from textattack.constraints.overlap import MaxWordsPerturbed
from textattack.transformations import WordSwapEmbedding
from textattack.attack import Attack
from textattack.search_methods import GreedyWordSwapWIR


# Custom ModelWrapper for our FastAPI Model Service
class RemoteModelWrapper(ModelWrapper):
    def __init__(self, model_service_url):
        self.model_service_url = model_service_url
        logger.info(f"RemoteModelWrapper initialized with model service URL: {model_service_url}")
        self.model_id = "default-sentiment-model"

    async def __call__(self, text_input_list, model_id: str = None):
        predictions = []
        effective_model_id = model_id if model_id else self.model_id 
        async with httpx.AsyncClient() as client:
            for text_input in text_input_list:
                try:
                    response = await client.post(
                        f"{self.model_service_url}/predict",
                        json={"model_id": effective_model_id, "input_data": text_input},
                        timeout=30
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    label_map = {"Negative": 0, "Neutral": 1, "Positive": 2}
                    numerical_label = label_map.get(result["prediction"], 1)
                    predictions.append(numerical_label)
                    logger.debug(f"Model prediction for '{text_input[:50]}...' with model '{effective_model_id}': {result['prediction']}")
                except httpx.RequestError as exc:
                    logger.error(f"Error communicating with model service for prediction (model '{effective_model_id}'): {exc}. Input: '{text_input[:50]}...' ")
                    predictions.append(1)
                except httpx.HTTPStatusError as exc:
                    logger.error(f"Model service returned error for prediction (model '{effective_model_id}'): {exc.response.status_code} - {exc.response.text}. Input: '{text_input[:50]}...' ")
                    predictions.append(1)
        
        import numpy as np
        return np.array(predictions)

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")
WEBHOOK_LISTENER_URL = os.getenv("WEBHOOK_LISTENER_URL", "http://webhook-listener:8003/webhook-receiver") # Get from env
remote_model_wrapper_instance = RemoteModelWrapper(MODEL_SERVICE_URL)

app = FastAPI(
    title="AI Adversarial Sandbox - Attack Service",
    description="Orchestrates and executes various adversarial attacks.",
    version="1.0.0"
)

class AttackLaunchRequest(BaseModel):
    model_id: str
    attack_method_id: str
    input_data: Any
    target_label: str = None
    attack_parameters: dict = {}
    callback_url: str = None

class AttackLaunchResponse(BaseModel):
    attack_id: str
    status: str
    message: str
    estimated_completion_time_seconds: int = None

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

class AttackStatusResponse(AttackResultSchema):
    progress_percentage: int = 0
    current_stage: str = "queued"

# --- Webhook Sender with Retries ---
async def send_webhook_with_retries(webhook_url: str, payload: Dict[str, Any]):
    for attempt in range(WEBHOOK_MAX_RETRIES):
        metrics_collector.increment_webhook_delivery_attempt(webhook_url) # Metric for each attempt
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status() # Raise an exception for 4xx/5xx responses
                logger.info(f"Webhook successfully sent on attempt {attempt + 1} to {webhook_url}. Status: {response.status_code}")
                metrics_collector.increment_webhook_success(webhook_url)
                return True
        except httpx.RequestError as exc:
            logger.warning(f"Webhook delivery failed on attempt {attempt + 1} to {webhook_url}: Connection error - {exc}. Retrying...")
            metrics_collector.increment_webhook_retry(webhook_url) # Metric for retry
        except httpx.HTTPStatusError as exc:
            logger.warning(f"Webhook delivery failed on attempt {attempt + 1} to {webhook_url}: HTTP error - {exc.response.status_code} {exc.response.text}. Retrying...")
            metrics_collector.increment_webhook_retry(webhook_url) # Metric for retry
        except Exception as e:
            logger.exception(f"Unexpected error during webhook delivery on attempt {attempt + 1}: {e}. Retrying...")
            metrics_collector.increment_webhook_retry(webhook_url) # Metric for retry
        
        if attempt < WEBHOOK_MAX_RETRIES - 1:
            retry_delay = WEBHOOK_RETRY_DELAY_SECONDS * (2 ** attempt) # Exponential backoff
            logger.info(f"Waiting {retry_delay} seconds before next webhook retry for {payload.get('attack_id')}.")
            await asyncio.sleep(retry_delay)
    
    logger.error(f"Webhook delivery failed after {WEBHOOK_MAX_RETRIES} attempts for attack {payload.get('attack_id')} to {webhook_url}.")
    metrics_collector.increment_webhook_failure(webhook_url) # Metric for final failure
    return False


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    endpoint_base_path = request.url.path
    metrics_collector.observe_http_request(endpoint_base_path, process_time)
    
    logger.debug(f"Request to {endpoint_base_path} completed in {process_time:.4f}s")
    return response

@app.on_event("startup")
def on_startup():
    logger.info("Attack Service startup initiated.")
    create_db_and_tables()

@app.get("/metrics", summary="Expose service metrics")
async def get_metrics(request: Request):
    accept_header = request.headers.get("Accept", "")
    if "application/json" in accept_header:
        return metrics_collector.get_metrics_json()
    else:
        return Response(content=metrics_collector.get_metrics_text(), media_type="text/plain")

async def perform_real_attack(attack_id: str, request: AttackLaunchRequest, db_session: Session):
    db_attack_result = db_session.query(AttackResult).filter(AttackResult.id == attack_id).first()
    if not db_attack_result:
        logger.error(f"Attack {attack_id} not found in DB at start of processing. This should not happen.")
        return

    db_attack_result.status = "in_progress"
    db_attack_result.perturbation_details = {"progress_percentage": 10, "current_stage": "initializing_attack_engine"}
    db_attack_result.updated_at = datetime.utcnow()
    db_session.add(db_attack_result)
    db_session.commit()
    db_session.refresh(db_attack_result)
    logger.info(f"Attack {attack_id} status updated to 'in_progress'.")
    
    start_time = time.time()
    original_prediction = "unknown"
    original_confidence = 0.0
    
    try:
        async with httpx.AsyncClient() as client:
            model_response = await client.post(
                f"{MODEL_SERVICE_URL}/predict",
                json={"model_id": request.model_id, "input_data": request.input_data},
                timeout=30
            )
            model_response.raise_for_status()
            original_result = model_response.json()
            original_prediction = original_result["prediction"]
            original_confidence = original_result["confidence"]
        logger.info(f"Original prediction fetched for attack {attack_id}: {original_prediction} using model '{request.model_id}'.")

        db_attack_result.perturbation_details["progress_percentage"] = 30
        db_attack_result.perturbation_details["current_stage"] = "generating_adversarial_example"
        db_attack_result.original_prediction = original_prediction
        db_attack_result.original_confidence = original_confidence
        db_attack_result.updated_at = datetime.utcnow()
        db_session.add(db_attack_result)
        db_session.commit()
        db_session.refresh(db_attack_result)

        label_map = {"Negative": 0, "Neutral": 1, "Positive": 2}
        original_label_num = label_map.get(original_prediction, 1)
        
        transformation = WordSwapEmbedding(max_candidates=request.attack_parameters.get("max_candidates", 10))
        constraints = [
            MaxWordsPerturbed(max_num_words=request.attack_parameters.get("num_words_to_change", 2))
        ]
        
        if request.target_label and request.target_label in label_map:
            goal_function = TargetedClassification(remote_model_wrapper_instance, target_class=label_map[request.target_label],
                                                   query_model_id=request.model_id)
            logger.info(f"Attack {attack_id}: Targeted attack with target label {request.target_label}.")
        else:
            goal_function = UntargetedClassification(remote_model_wrapper_instance, target_class=original_label_num,
                                                     query_model_id=request.model_id)
            logger.info(f"Attack {attack_id}: Untargeted attack.")

        attack = Attack(goal_function, constraints, transformation, GreedyWordSwapWIR())

        attack_result_textattack = attack.attack(request.input_data, original_label_num)
        
        if attack_result_textattack.perturbed_text:
            adversarial_example = attack_result_textattack.perturbed_text.text
            attack_success_intermediate = attack_result_textattack.goal_function_result.succeeded
            logger.info(f"Attack {attack_id}: Adversarial example generated. Success (pre-eval): {attack_success_intermediate}")
        else:
            adversarial_example = str(request.input_data)
            attack_success_intermediate = False 
            logger.warning(f"Attack {attack_id}: No adversarial example found for input '{request.input_data}'.")

        db_attack_result.perturbation_details["progress_percentage"] = 80
        db_attack_result.perturbation_details["current_stage"] = "evaluating_adversarial_output"
        db_attack_result.adversarial_example = adversarial_example
        db_attack_result.updated_at = datetime.utcnow()
        db_session.add(db_attack_result)
        db_session.commit()
        db_session.refresh(db_attack_result)

        adversarial_prediction = original_prediction 
        adversarial_confidence = original_confidence
        if adversarial_example != request.input_data:
            async with httpx.AsyncClient() as client:
                model_response_adv = await client.post(
                    f"{MODEL_SERVICE_URL}/predict",
                    json={"model_id": request.model_id, "input_data": adversarial_example},
                    timeout=30
                )
                model_response_adv.raise_for_status()
                adv_result = model_response_adv.json()
                adversarial_prediction = adv_result["prediction"]
                adversarial_confidence = adv_result["confidence"]
                
                if request.target_label:
                    attack_success_final = (adversarial_prediction == request.target_label)
                    logger.info(f"Attack {attack_id}: Targeted attack final result. Targeted: {request.target_label}, Actual: {adversarial_prediction}. Success: {attack_success_final}")
                else:
                    attack_success_final = (adversarial_prediction != original_prediction)
                    logger.info(f"Attack {attack_id}: Untargeted attack final result. Original: {original_prediction}, Adversarial: {adversarial_prediction}. Success: {attack_success_final}")
        else:
            attack_success_final = False 
            logger.info(f"Attack {attack_id}: No perturbation, so attack considered failed.")

        perturbation_details_data = {
            "original_text_len": len(str(request.input_data)),
            "adversarial_text_len": len(str(adversarial_example)),
            "num_words_perturbed": attack_result_textattack.num_words_perturbed if attack_result_textattack.num_words_perturbed is not None else 0,
            "diff": attack_result_textattack.str_diff if attack_result_textattack.str_diff else "No diff available"
        }

        db_attack_result.adversarial_prediction = adversarial_prediction
        db_attack_result.adversarial_confidence = adversarial_confidence
        db_attack_result.attack_success = attack_success_final
        db_attack_result.perturbation_details = perturbation_details_data
        db_attack_result.metrics = {"attack_time_seconds": time.time() - start_time}
        db_attack_result.status = "completed"
        db_attack_result.completed_at = datetime.utcnow()
        db_attack_result.updated_at = datetime.utcnow()
        db_session.add(db_attack_result)
        db_session.commit()
        db_session.refresh(db_attack_result)
        logger.info(f"Attack {attack_id} completed successfully. Final status: {db_attack_result.status}. Success: {db_attack_result.attack_success}.")

    except Exception as e:
        db_attack_result.status = "failed"
        db_attack_result.error = str(e)
        db_attack_result.updated_at = datetime.utcnow()
        db_session.add(db_attack_result)
        db_session.commit()
        db_session.refresh(db_attack_result)
        logger.exception(f"Attack {attack_id} failed with an exception: {e}")

    if request.callback_url:
        webhook_payload = {
            "event_type": f"attack_{db_attack_result.status}",
            "attack_id": attack_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": db_attack_result.status,
            "model_id": db_attack_result.model_id,
            "attack_method_id": db_attack_result.attack_method_id,
            "attack_success": db_attack_result.attack_success,
            "original_input_preview": db_attack_result.original_input[:100] + "..." if len(db_attack_result.original_input) > 100 else db_attack_result.original_input,
            "adversarial_example_preview": db_attack_result.adversarial_example[:100] + "..." if len(db_attack_result.adversarial_example) > 100 else db_attack_result.adversarial_example,
            "result_url": f"http://attack-service:8002/attacks/{attack_id}/results" 
        }
        await send_webhook_with_retries(request.callback_url, webhook_payload)


@app.post("/launch", response_model=AttackLaunchResponse, summary="Launch an adversarial attack")
async def launch_attack_endpoint(request: AttackLaunchRequest, db: Session = Depends(get_db)):
    attack_id = f"atk_{uuid.uuid4().hex}"
    logger.info(f"New attack launch request received. Attack ID: {attack_id}. Model: {request.model_id}, Method: {request.attack_method_id}")
    
    new_attack_result = AttackResult(
        id=attack_id,
        model_id=request.model_id,
        attack_method_id=request.attack_method_id,
        original_input=str(request.input_data),
        original_prediction="unknown",
        original_confidence=0.0,
        adversarial_example=str(request.input_data),
        adversarial_prediction="unknown",
        adversarial_confidence=0.0,
        attack_success=False,
        perturbation_details={"progress_percentage": 0, "current_stage": "queued"},
        metrics={},
        status="queued",
        created_at=datetime.utcnow(),
        completed_at=None,
        error=None
    )
    db.add(new_attack_result)
    db.commit()
    db.refresh(new_attack_result)
    logger.info(f"Attack {attack_id} initialized and queued in DB.")

    asyncio.create_task(perform_real_attack(attack_id, request, SessionLocal()))

    return AttackLaunchResponse(
        attack_id=attack_id,
        status="initiated",
        message="Attack initiated successfully. Check status endpoint for progress.",
        estimated_completion_time_seconds=60
    )

@app.get("/attacks/{attack_id}/status", response_model=AttackStatusResponse, summary="Get status of an adversarial attack")
async def get_attack_status(attack_id: str, db: Session = Depends(get_db)):
    logger.info(f"Fetching status for attack: {attack_id}")
    db_attack_result = db.query(AttackResult).filter(AttackResult.id == attack_id).first()
    if not db_attack_result:
        logger.warning(f"Status requested for non-existent attack ID: {attack_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack ID not found")
    
    response_data = db_attack_result.__dict__
    perturbation_details = response_data.get("perturbation_details") or {}
    response_data["progress_percentage"] = perturbation_details.get("progress_percentage", 0)
    response_data["current_stage"] = perturbation_details.get("current_stage", "queued")
    response_data["started_at"] = db_attack_result.created_at.isoformat() + "Z"
    response_data["updated_at"] = db_attack_result.updated_at.isoformat() + "Z"
    response_data["completed_at"] = db_attack_result.completed_at.isoformat() + "Z" if db_attack_result.completed_at else None
    logger.debug(f"Status for {attack_id}: {db_attack_result.status}, {response_data['progress_percentage']}% ")
    return AttackStatusResponse(attack_id=attack_id, **response_data)


@app.get("/attacks/{attack_id}/results", response_model=AttackResultSchema, summary="Get results of a completed adversarial attack")
async def get_attack_results(attack_id: str, db: Session = Depends(get_db)):
    logger.info(f"Fetching results for attack: {attack_id}")
    db_attack_result = db.query(AttackResult).filter(AttackResult.id == attack_id).first()
    if not db_attack_result:
        logger.warning(f"Results requested for non-existent attack ID: {attack_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack ID not found")
    if db_attack_result.status != "completed":
        logger.warning(f"Results requested for incomplete attack ID: {attack_id} (Status: {db_attack_result.status})")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attack is not yet completed")
    
    response_data = db_attack_result.__dict__
    response_data["generated_at"] = db_attack_result.completed_at.isoformat() + "Z"
    response_data["perturbation_details"] = db_attack_result.perturbation_details or {}
    response_data["metrics"] = db_attack_result.metrics or {}
    logger.info(f"Results for attack {attack_id} fetched successfully.")
    return AttackResultSchema(**response_data)

@app.get("/attacks", response_model=Dict[str, Any], summary="List all adversarial attack results with filtering and sorting")
async def list_attacks(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    attack_method_id: Optional[str] = Query(None, description="Filter by attack method ID"),
    status: Optional[str] = Query(None, description="Filter by attack status (e.g., queued, in_progress, completed, failed)"),
    attack_success: Optional[bool] = Query(None, description="Filter by attack success (true/false)"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by (e.g., id, created_at, completed_at, model_id)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)")
):
    logger.info(f"Listing attack results with filters: model_id={model_id}, method={attack_method_id}, status={status}, success={attack_success}, sort_by={sort_by}, order={sort_order}, skip={skip}, limit={limit}")
    
    query = db.query(AttackResult)

    if model_id:
        query = query.filter(AttackResult.model_id == model_id)
    if attack_method_id:
        query = query.filter(AttackResult.attack_method_id == attack_method_id)
    if status:
        query = query.filter(AttackResult.status == status)
    if attack_success is not None:
        query = query.filter(AttackResult.attack_success == attack_success)

    if sort_by:
        sort_column = getattr(AttackResult, sort_by, None)
        if sort_column is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort_by field: {sort_by}")
        
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        elif sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sort_order must be 'asc' or 'desc'")
    
    results = query.offset(skip).limit(limit).all()
    total_results = query.count()

    logger.info(f"Returned {len(results)} attack results out of {total_results} total.")
    return {"total": total_results, "limit": limit, "offset": skip, "data": [AttackResultSchema.from_orm(r) for r in results]}


@app.get("/", summary="Attack Service health check")
async def read_root():
    logger.info("Attack Service health check requested.")
    return {"message": "Attack Service is operational!"}
