# AI Adversarial Sandbox - API Specification

This document outlines the RESTful API endpoints for the AI Adversarial Sandbox, designed for programmatic interaction with AI models and adversarial attack capabilities.

## 1. Base URL

`https://api.adversarial-sandbox.com/v1` (Example)

## 2. Authentication and Authorization

All API requests must be authenticated using **OAuth2 Bearer Tokens**.
- Clients will obtain a JWT (JSON Web Token) from an `/auth/token` endpoint (not detailed here but assumed).
- The token must be included in the `Authorization` header as `Bearer <TOKEN>`.
- Role-Based Access Control (RBAC) will enforce granular permissions based on user roles (e.g., `viewer`, `developer`, `admin`).

```http
Authorization: Bearer <YOUR_JWT_TOKEN>
```

## 3. General Principles

- **RESTful Design:** Use standard HTTP methods (GET, POST, PUT, DELETE) to interact with resources.
- **JSON Payloads:** All request and response bodies will be JSON.
- **Standard HTTP Status Codes:** Use appropriate HTTP status codes for success, client errors, and server errors.
- **Versioning:** API versioning via `/v1` in the URL.
- **Rate Limiting:** To prevent abuse, rate limits will be applied per authenticated user/IP. Details TBD.
- **Pagination:** For list endpoints, use `limit` and `offset` query parameters.
- **Webhooks:** Support for asynchronous notifications on long-running tasks (e.g., attack completion).

## 4. Error Handling

Standard error response format:

```json
{
  "code": "error_code_string",
  "message": "A human-readable error description.",
  "details": {
    "field_name": "Specific reason for error related to this field"
  }
}
```

**Common Error Codes:**
- `400 Bad Request`: Invalid input payload.
- `401 Unauthorized`: Missing or invalid authentication token.
- `403 Forbidden`: Insufficient permissions.
- `404 Not Found`: Resource not found.
- `429 Too Many Requests`: Rate limit exceeded.
- `500 Internal Server Error`: Unexpected server error.
- `503 Service Unavailable`: Temporary service outage.

## 5. API Endpoints

### 5.1 Model Management

#### 5.1.1 List Models

`GET /models`

**Description:** Retrieves a list of available AI models.

**Query Parameters:**
- `type` (optional, string): Filter by model type (e.g., `CV`, `NLP`).
- `status` (optional, string): Filter by model status (e.g., `active`, `deprecated`).
- `limit` (optional, integer): Max number of models to return (default: 100).
- `offset` (optional, integer): Offset for pagination (default: 0).
- `sort_by` (optional, string): Field to sort by (e.g., `id`, `name`, `created_at`, `updated_at`).
- `sort_order` (optional, string): Sort order (`asc` or `desc`).

**Response (200 OK):**
```json
{
  "total": 5,
  "limit": 100,
  "offset": 0,
  "data": [
    {
      "id": "model_cv_resnet50_v1",
      "name": "ResNet-50 Image Classifier v1",
      "type": "CV",
      "version": "1.0.0",
      "description": "Pre-trained ResNet-50 for ImageNet classification.",
      "status": "active",
      "created_at": "2023-01-15T10:00:00Z",
      "updated_at": "2023-01-15T10:00:00Z"
    },
    {
      "id": "model_nlp_bert_sentiment_v2",
      "name": "BERT Sentiment Analyzer v2",
      "type": "NLP",
      "version": "2.0.1",
      "description": "Fine-tuned BERT for sentiment analysis (positive/negative/neutral).",
      "status": "active",
      "created_at": "2023-02-20T14:30:00Z",
      "updated_at": "2023-03-01T09:15:00Z"
    }
  ]
}
```

#### 5.1.2 Get Model Details

`GET /models/{model_id}`

**Description:** Retrieves detailed information about a specific AI model.

**Path Parameters:**
- `model_id` (string, required): The unique identifier of the model.

**Response (200 OK):**
```json
{
  "id": "model_cv_resnet50_v1",
  "name": "ResNet-50 Image Classifier v1",
  "type": "CV",
  "version": "1.0.0",
  "description": "Pre-trained ResNet-50 for ImageNet classification.",
  "status": "active",
  "input_schema": {
    "type": "object",
    "properties": {
      "image": {
        "type": "string",
        "format": "byte",
        "description": "Base64 encoded image data"
      }
    },
    "required": ["image"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "prediction": {
        "type": "string",
        "description": "Predicted class label"
      },
      "confidence": {
        "type": "number",
        "format": "float",
        "description": "Confidence score of the prediction"
      }
    }
  },
  "metrics": {
    "accuracy": 0.92,
    "f1_score": 0.91
  },
  "created_at": "2023-01-15T10:00:00Z",
  "updated_at": "2023-01-15T10:00:00Z"
}
```

#### 5.1.3 Upload New Model

`POST /models`

**Description:** Uploads a new AI model to the sandbox.

**Request Body:**
```json
{
  "name": "New Text Classifier for Spam",
  "type": "NLP",
  "version": "1.0.0",
  "description": "Custom model for spam detection.",
  "model_file_url": "s3://your-bucket/models/spam_classifier_v1.pth",
  "metadata": {
    "trained_on": "public_spam_dataset",
    "framework": "pytorch"
  }
}
```
**Response (201 Created):**
```json
{
  "id": "model_nlp_spam_v1",
  "name": "New Text Classifier for Spam",
  "type": "NLP",
  "status": "processing",
  "created_at": "2023-04-01T11:00:00Z"
}
```
*Note: Model processing (e.g., loading, validation) will be asynchronous.*

### 5.2 Prediction & Inference

#### 5.2.1 Get Model Prediction

`POST /models/{model_id}/predict`

**Description:** Gets a prediction from a specified AI model.

**Path Parameters:**
- `model_id` (string, required): The unique identifier of the model.

**Request Body:** (Varies based on `model_id`'s `input_schema`)
Example for an NLP model:
```json
{
  "input_data": "This is a great product, I love it!"
}
```
Example for a CV model:
```json
{
  "image": "base64_encoded_image_data_here"
}
```

**Response (200 OK):** (Varies based on `model_id`'s `output_schema`)
Example for an NLP model:
```json
{
  "prediction": "Positive",
  "confidence": 0.98,
  "model_id": "model_nlp_bert_sentiment_v2",
  "input_hash": "a1b2c3d4e5f6g7h8"
}
```

### 5.3 Adversarial Attacks

#### 5.3.1 List Available Attack Methods

`GET /attacks`

**Description:** Retrieves a list of supported adversarial attack methods.

**Query Parameters:**
- `model_type` (optional, string): Filter by compatible model type (e.g., `CV`, `NLP`).

**Response (200 OK):**
```json
{
  "total": 3,
  "data": [
    {
      "id": "attack_fgsm",
      "name": "Fast Gradient Sign Method",
      "description": "Generates adversarial examples by adding perturbation in the direction of the sign of the gradient.",
      "compatible_model_types": ["CV"],
      "parameters_schema": {
        "epsilon": {"type": "number", "default": 0.01, "description": "Magnitude of perturbation"},
        "clip_min": {"type": "number", "default": 0.0},
        "clip_max": {"type": "number", "default": 1.0}
      }
    },
    {
      "id": "attack_textfooler",
      "name": "TextFooler",
      "description": "Generates adversarial text by replacing words with semantically similar ones.",
      "compatible_model_types": ["NLP"],
      "parameters_schema": {
        "num_words_to_change": {"type": "integer", "default": 5},
        "max_candidates": {"type": "integer", "default": 20}
      }
    }
  ]
}
```

#### 5.3.2 Launch Adversarial Attack

`POST /attacks/launch`

**Description:** Launches an adversarial attack against a specified model. This is an asynchronous operation.

**Request Body:**
```json
{
  "model_id": "model_nlp_bert_sentiment_v2",
  "attack_method_id": "attack_textfooler",
  "input_data": "This movie was absolutely amazing and I loved every second.",
  "target_label": "Negative",
  "attack_parameters": {
    "num_words_to_change": 2,
    "max_candidates": 10
  },
  "callback_url": "https://your-app.com/webhook/attack-results"
}
```

**Response (202 Accepted):**
```json
{
  "attack_id": "atk_nlp_xyz123abc",
  "status": "initiated",
  "message": "Attack initiated successfully. Results will be sent to the callback URL.",
  "estimated_completion_time_seconds": 300
}
```

#### 5.3.3 Get Attack Status

`GET /attacks/{attack_id}/status`

**Description:** Retrieves the current status of an ongoing or completed adversarial attack.

**Path Parameters:**
- `attack_id` (string, required): The unique identifier of the attack.

**Response (200 OK):**
```json
{
  "attack_id": "atk_nlp_xyz123abc",
  "status": "in_progress",
  "progress_percentage": 60,
  "current_stage": "generating_candidates",
  "started_at": "2023-04-01T12:05:00Z",
  "updated_at": "2023-04-01T12:08:00Z",
  "result_available_at": null,
  "error": null
}
```
**Possible Statuses:** `initiated`, `queued`, `in_progress`, `completed`, `failed`, `cancelled`.

#### 5.3.4 Get Attack Results

`GET /attacks/{attack_id}/results`

**Description:** Retrieves the detailed results of a completed adversarial attack.

**Path Parameters:**
- `attack_id` (string, required): The unique identifier of the attack.

**Response (200 OK):**
```json
{
  "attack_id": "atk_nlp_xyz123abc",
  "status": "completed",
  "original_input": "This movie was absolutely amazing and I loved every second.",
  "original_prediction": "Positive",
  "original_confidence": 0.99,
  "adversarial_example": "This movie was absolutely astonishing and I adored every second.",
  "adversarial_prediction": "Negative",
  "adversarial_confidence": 0.52,
  "attack_success": true,
  "perturbation_details": {
    "words_changed": [
      {"original": "amazing", "adversarial": "astonishing"},
      {"original": "loved", "adversarial": "adored"}
    ],
    "levenshtein_distance": 2
  },
  "metrics": {
    "attack_time_seconds": 120.5,
    "cpu_usage_avg": "50%",
    "gpu_usage_avg": "80%"
  },
  "generated_at": "2023-04-01T12:10:00Z"
}
```

## 6. Webhooks

For asynchronous notifications, especially for `Launch Adversarial Attack`, the system can send POST requests to a `callback_url` provided during the attack launch.

**Webhook Payload Example (Attack Completed):**
```json
{
  "event_type": "attack_completed",
  "attack_id": "atk_nlp_xyz123abc",
  "timestamp": "2023-04-01T12:10:00Z",
  "status": "completed",
  "result_url": "https://api.adversarial-sandbox.com/v1/attacks/atk_nlp_xyz123abc/results",
  "model_id": "model_nlp_bert_sentiment_v2",
  "attack_method_id": "attack_textfooler",
  "attack_success": true,
  "original_input_preview": "This movie was absolutely amazing and I loved every second.",
  "adversarial_example_preview": "This movie was absolutely astonishing and I adored every second."
}
```

This API specification ensures clear, consistent, and secure interaction with the AI Adversarial Sandbox, enabling seamless integration with other systems.
