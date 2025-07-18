# AI Adversarial Sandbox (Professionalized)

This repository hosts the professionalized version of the AI Adversarial Sandbox, evolving from a simple Flask application into a robust, scalable, and secure SaaS platform.

## Project Vision

To provide a comprehensive platform for developing, testing, and demonstrating adversarial attacks against various AI models, ensuring their robustness and security in real-world deployments.

## Architecture

This project adopts a microservices architecture, containerized with Docker and orchestrated by Kubernetes.

**Key Services:**
- `api-gateway`: Handles incoming requests, authentication, and routing.
- `model-service`: Manages AI model loading, inference, and versioning.
- `attack-service`: Orchestrates and executes various adversarial attacks.

## Getting Started (Local Development)

Refer to `docs/development/SETUP.md` for detailed instructions on setting up your local development environment.

## Running Tests

To run the automated tests locally:

1.  Ensure Docker Compose services are *not* running, or if they are, ensure your tests use mock services or a separate test database to prevent interference. The provided tests use in-memory SQLite databases for isolation.
2.  Navigate to the project root directory: `cd ai-adversarial-sandbox-pro`
3.  Install top-level test dependencies (pytest, httpx, etc.): `pip install pytest httpx`
4.  Install dependencies for each service locally (if you haven't already for local development):
    ```bash
    pip install -r services/api-gateway/requirements.txt
    pip install -r services/model-service/requirements.txt
    pip install -r services/attack-service/requirements.txt
    ```
    (Note: `textattack` and `torch` can be large. For quicker test runs, consider mocking their dependencies or running tests in dedicated CI environments where dependencies are pre-cached.)
5.  Run all tests: `pytest tests/`

## Documentation

- **Architecture:** `docs/architecture/README.md`
- **API Specification:** `docs/architecture/API_SPECIFICATION.md`
- **Security Policy:** `docs/security/SECURITY.md`
- **Development Setup:** `docs/development/SETUP.md`

## Current Status: Phase 1 - Foundational Development Advanced

The project now features:
- A functional microservices architecture orchestrated by Docker Compose.
- Real AI model integration (`transformers`).
- Real adversarial attack capabilities (`TextAttack`).
- Database persistence for models and attack results.
- A functional React frontend for prediction, attack launching, historical attack viewing, and model management.
- **Initial JWT-based authentication for API access.**
- **Basic automated unit and integration tests for core backend services.**
