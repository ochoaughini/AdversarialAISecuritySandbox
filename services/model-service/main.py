from fastapi import FastAPI, HTTPException, status, Depends, Query, Request, Response
from pydantic import BaseModel
import time
import os
from sqlalchemy.orm import Session
from services.database import Model, get_db, create_db_and_tables
import logging
from services.logging_config import setup_logging
from services.metrics_collector import metrics_collector
from typing import Optional, Dict, Any, List
from collections import OrderedDict

# Setup logging for this service
logger = setup_logging("model-service")

# --- Dynamic Model Loading Infrastructure ---
class LRUCache:
    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return -1
        value = self.cache.pop(key)
        self.cache[key] = value
        metrics_collector.increment_cache_hit(key)
        return value

    def put(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            lru_key = self.cache.popitem(last=False)[0]
            logger.info(f"LRU Cache: Evicting model '{lru_key}' to make space.")
            metrics_collector.increment_cache_eviction(lru_key)
        self.cache[key] = value
        logger.info(f"LRU Cache: Added/Updated model '{key}'. Current cache size: {len(self.cache)}/{self.capacity}")
        metrics_collector.increment_cache_miss(key) # A put is effectively a miss and then load

model_cache = LRUCache(capacity=int(os.getenv("MODEL_CACHE_CAPACITY", 5))) # Configurable capacity

async def load_model_instance(model_id: str, model_type: str, db_session: Session):
    cached_model = model_cache.get(model_id)
    if cached_model != -1:
        return cached_model

    logger.info(f"Loading model instance for model_id: '{model_id}', type: '{model_type}' (Not in cache).")
    
    model_instance = None
    if model_type == "NLP":
        if model_id == "default-sentiment-model":
            try:
                from transformers import pipeline
                model_instance = pipeline("sentiment-analysis")
                logger.info(f"Loaded 'default-sentiment-model' using transformers pipeline.")
            except ImportError:
                logger.warning("Transformers not available. Loading StructuredMockAIModel for 'default-sentiment-model'.")
                model_instance = StructuredMockAIModel()
            except Exception as e:
                logger.exception(f"Error loading transformers pipeline for 'default-sentiment-model': {e}. Falling back to mock.")
                model_instance = StructuredMockAIModel()
        elif model_id == "negative-bias-model":
            model_instance = NegativeBiasMockAIModel()
            logger.info(f"Loaded 'negative-bias-model' (mock with negative bias).")
        elif model_id == "positive-bias-model":
            model_instance = PositiveBiasMockAIModel()
            logger.info(f"Loaded 'positive-bias-model' (mock with positive bias).")
        else:
            try:
                from transformers import pipeline
                model_instance = pipeline("sentiment-analysis")
                logger.info(f"Loaded generic NLP model using transformers pipeline for '{model_id}'.")
            except ImportError:
                logger.warning(f"Transformers not available. Loading StructuredMockAIModel for '{model_id}'.")
                model_instance = StructuredMockAIModel()
            except Exception as e:
                logger.exception(f"Error loading generic NLP pipeline for '{model_id}': {e}. Falling back to mock.")
                model_instance = StructuredMockAIModel()

    elif model_type == "CV":
        model_instance = CVMockModel()
        logger.info(f"Loaded CV mock model for '{model_id}'.")
    elif model_type == "Time Series":
        model_instance = TimeSeriesMockModel()
        logger.info(f"Loaded Time Series mock model for '{model_id}'.")
    else:
        logger.warning(f"Unknown model type '{model_type}' for model_id '{model_id}'. Using general purpose mock.")
        model_instance = StructuredMockAIModel()

    if model_instance:
        model_cache.put(model_id, model_instance)
        return model_instance
    else:
        logger.error(f"Failed to load or find suitable mock for model ID: {model_id}, Type: {model_type}")
        return None # Indicate failure to load

# --- Mock AI Models for demonstration purposes with different behaviors ---
class BaseMockAIModel:
    def predict(self, input_data: Any):
        raise NotImplementedError("Subclasses must implement predict method.")

class StructuredMockAIModel(BaseMockAIModel):
    def __init__(self):
        self.positive_keywords = ['good', 'great', 'excellent', 'happy', 'love', 'amazing']
        self.negative_keywords = ['bad', 'terrible', 'awful', 'sad', 'hate', 'poor']
        logger.debug("Structured mock AI model initialized for prediction.")

    def predict(self, text_input: str):
        text_input_lower = str(text_input).lower()
        time.sleep(0.05)
        if any(keyword in text_input_lower for keyword in self.positive_keywords):
            return {"prediction": "Positive", "confidence": 0.95}
        elif any(keyword in text_input_lower for keyword in self.negative_keywords):
            return {"prediction": "Negative", "confidence": 0.85}
        else:
            return {"prediction": "Neutral", "confidence": 0.70}

class NegativeBiasMockAIModel(StructuredMockAIModel):
    def predict(self, text_input: str):
        time.sleep(0.06)
        text_input_lower = str(text_input).lower()
        if "bad" in text_input_lower or "terrible" in text_input_lower or "fail" in text_input_lower:
            return {"prediction": "Negative", "confidence": 0.98}
        if any(keyword in text_input_lower for keyword in self.positive_keywords):
            return {"prediction": "Neutral", "confidence": 0.60}
        return {"prediction": "Negative", "confidence": 0.75}

class PositiveBiasMockAIModel(StructuredMockAIModel):
    def predict(self, text_input: str):
        time.sleep(0.04)
        text_input_lower = str(text_input).lower()
        if "good" in text_input_lower or "great" in text_input_lower or "success" in text_input_lower:
            return {"prediction": "Positive", "confidence": 0.98}
        if any(keyword in text_input_lower for keyword in self.negative_keywords):
            return {"prediction": "Neutral", "confidence": 0.60}
        return {"prediction": "Positive", "confidence": 0.75}

class CVMockModel(BaseMockAIModel):
    def predict(self, image_data: str):
        time.sleep(0.1)
        if "cat" in str(image_data).lower():
            return {"prediction": "Cat", "confidence": 0.99}
        elif "dog" in str(image_data).lower():
            return {"prediction": "Dog", "confidence": 0.98}
        return {"prediction": "Object", "confidence": 0.7}

class TimeSeriesMockModel(BaseMockAIModel):
    def predict(self, series_data: List[float]):
        time.sleep(0.08)
        if not isinstance(series_data, list) or not all(isinstance(x, (int, float)) for x in series_data):
            logger.warning(f"Invalid series_data type received by TS mock: {type(series_data)}")
            return {"prediction": "Error", "confidence": 0.0}
        
        if len(series_data) > 0 and max(series_data) > 100:
            return {"prediction": "Anomaly Detected", "confidence": 0.92}
        return {"prediction": "Normal", "confidence": 0.85}


app = FastAPI(
    title="AI Adversarial Sandbox - Model Service",
    description="Manages AI model loading, inference, and versioning.",
    version="1.0.0"
)

# --- Pydantic Models ---
class PredictionRequest(BaseModel):
    model_id: str
    input_data: Any

class PredictionResponse(BaseModel):
    model_id: str
    prediction: str
    confidence: float

class ModelBase(BaseModel):
    id: str
    name: str
    type: str
    version: str
    description: Optional[str] = None
    status: Optional[str] = "active"
    model_file_url: Optional[str] = None
    metadata: Optional[dict] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    metrics: Optional[dict] = None

class ModelCreate(ModelBase):
    pass

class ModelResponse(ModelBase):
    created_at: datetime
    updated_at: datetime

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

@app.on_event("startup")
def on_startup():
    logger.info("Model Service startup initiated.")
    create_db_and_tables()
    db = Session(bind=get_db().__next__().bind)
    try:
        models_to_seed = [
            Model(id="default-sentiment-model", name="Default Sentiment Classifier", type="NLP", version="1.0.0", description="A general-purpose sentiment analysis model. Uses HuggingFace Transformers if available, else a structured mock."),
            Model(id="negative-bias-model", name="Negative Bias Sentiment", type="NLP", version="1.0.0", description="A sentiment model with a bias towards negative classifications."),
            Model(id="positive-bias-model", name="Positive Bias Sentiment", type="NLP", version="1.0.0", description="A sentiment model with a bias towards positive classifications."),
            Model(id="cv-object-detector", name="Mock Object Detector", type="CV", version="1.0.0", description="A mock model for image classification (cat/dog/object)."),
            Model(id="ts-anomaly-detector", name="Mock Anomaly Detector", type="Time Series", version="1.0.0", description="A mock model for time series anomaly detection.")
        ]
        
        for model_data in models_to_seed:
            if db.query(Model).filter(Model.id == model_data.id).first() is None:
                db.add(model_data)
                logger.info(f"Model '{model_data.id}' added to DB.")
            else:
                logger.info(f"Model '{model_data.id}' already exists in DB.")
        db.commit()
    except Exception as e:
        logger.exception(f"Error during Model Service startup model registration: {e}")
    finally:
        db.close()

# Metrics endpoint for Prometheus or direct access
@app.get("/metrics", summary="Expose service metrics")
async def get_metrics(request: Request):
    accept_header = request.headers.get("Accept", "")
    if "application/json" in accept_header:
        return metrics_collector.get_metrics_json()
    else:
        return Response(content=metrics_collector.get_metrics_text(), media_type="text/plain")

@app.post("/predict", response_model=PredictionResponse, summary="Get a prediction from an AI model")
async def predict_endpoint(request: PredictionRequest, db: Session = Depends(get_db)):
    logger.info(f"Prediction request received for model '{request.model_id}'. Input type: {type(request.input_data).__name__}")
    
    db_model_info = db.query(Model).filter(Model.id == request.model_id).first()
    if not db_model_info:
        logger.warning(f"Prediction requested for non-existent model ID: {request.model_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{request.model_id}' not found.")

    model_instance = await load_model_instance(db_model_info.id, db_model_info.type, db)
    if model_instance is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to load model instance for '{request.model_id}'.")
    
    try:
        if hasattr(model_instance, 'task') and hasattr(model_instance, '__call__') and model_instance.task == 'sentiment-analysis':
            if not isinstance(request.input_data, str):
                raise ValueError("Input data for NLP (transformers) model must be a string.")
            result = model_instance(request.input_data)[0]
            prediction_label = result['label'].capitalize()
            confidence_score = result['score']
            logger.info(f"Prediction by transformers for '{request.model_id}': {prediction_label} with confidence {confidence_score:.4f}")
        elif isinstance(model_instance, BaseMockAIModel):
            result = model_instance.predict(request.input_data)
            prediction_label = result['prediction']
            confidence_score = result['confidence']
            logger.info(f"Prediction by mock model for '{request.model_id}': {prediction_label} with confidence {confidence_score:.4f}")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prediction logic not implemented for this model instance type.")
        
    except ValueError as e:
        logger.error(f"Input validation error for model '{request.model_id}': {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error during model inference for model '{request.model_id}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during model inference: {e}")

    return PredictionResponse(
        model_id=request.model_id,
        prediction=prediction_label,
        confidence=confidence_score
    )

@app.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED, summary="Upload a new AI model")
async def create_model(model: ModelCreate, db: Session = Depends(get_db)):
    logger.info(f"Attempting to create new model: {model.id}")
    db_model = db.query(Model).filter(Model.id == model.id).first()
    if db_model:
        logger.warning(f"Model with ID '{model.id}' already exists. Cannot create duplicate.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Model with ID '{model.id}' already exists.")
    db_model = Model(**model.dict())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    logger.info(f"Model '{db_model.id}' created successfully in DB.")
    return db_model

@app.get("/models/{model_id}", response_model=ModelResponse, summary="Get model details")
async def get_model(model_id: str, db: Session = Depends(get_db)):
    logger.info(f"Fetching details for model: {model_id}")
    db_model = db.query(Model).filter(Model.id == model_id).first()
    if db_model is None:
        logger.warning(f"Model '{model_id}' not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    logger.info(f"Model '{model_id}' details fetched successfully.")
    return db_model

@app.get("/models", response_model=Dict[str, Any], summary="List available AI models with filtering and sorting")
async def list_models(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type: Optional[str] = Query(None, description="Filter by model type (e.g., NLP, CV, Time Series)"),
    status: Optional[str] = Query(None, description="Filter by model status (e.g., active, deprecated)"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by (e.g., id, name, created_at, updated_at)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)")
):
    logger.info(f"Listing models with filters: type={type}, status={status}, sort_by={sort_by}, sort_order={sort_order}, skip={skip}, limit={limit}")
    
    query = db.query(Model)

    if type:
        query = query.filter(Model.type == type)
    if status:
        query = query.filter(Model.status == status)

    if sort_by:
        sort_column = getattr(Model, sort_by, None)
        if sort_column is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort_by field: {sort_by}")
        
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        elif sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sort_order must be 'asc' or 'desc'")
    
    total_models = query.count()
    models = query.offset(skip).limit(limit).all()
    
    logger.info(f"Returned {len(models)} models out of {total_models} total.")
    return {"total": total_models, "limit": limit, "offset": skip, "data": [ModelResponse.from_orm(m) for m in models]}

@app.get("/", summary="Model Service health check")
async def read_root():
    logger.info("Model Service health check requested.")
    return {"message": "Model Service is operational!"}
