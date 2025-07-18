# AI Adversarial Sandbox - Development Setup Guide

This guide provides instructions for setting up your local development environment for the AI Adversarial Sandbox project.

## 1. System Requirements

- **Operating System:** macOS, Linux, or Windows (with WSL2 recommended for Windows users).
- **RAM:** Minimum 16 GB (32 GB recommended for running multiple services/models).
- **CPU:** Modern multi-core processor.
- **Disk Space:** Minimum 50 GB free space.
- **Internet Connection:** Required for downloading dependencies and Docker images.

## 2. Prerequisites

Ensure the following software is installed on your system:

- **Git:** Version control system.
    - `git --version`
- **Docker Desktop:** Or Docker Engine (for Linux). Required for containerizing services.
    - `docker --version`
    - `docker compose version` (or `docker-compose --version` for older versions)
- **Python:** Version 3.9+ (or as specified in `backend/requirements.txt`).
    - `python3 --version`
- **Node.js & npm/yarn:** For frontend development.
    - `node --version`
    - `npm --version` (or `yarn --version`)
- **kubectl:** Kubernetes command-line tool (if interacting with local K8s like Minikube/K3s).
    - `kubectl version --client`
- **(Optional) Minikube / K3s / Kind:** For local Kubernetes cluster simulation.
- **(Optional) VS Code / PyCharm / IntelliJ IDEA:** Recommended IDEs with good Docker/Kubernetes integration.

## 3. Local Development Setup Instructions

Follow these steps to get the project running locally:

### 3.1. Clone the Repository

```bash
git clone https://github.com/your-username/ai-adversarial-sandbox-pro.git
cd ai-adversarial-sandbox-pro
```
*Note: Replace `your-username` with the actual GitHub organization/user once the repo is created.*

### 3.2. Prepare Environment Variables

Create a `.env` file in the root directory of the project. This file will hold environment variables for local development.

```
# Example .env content
# FLASK_APP=services/api-gateway/main.py
# FLASK_DEBUG=1
# DATABASE_URL=postgresql://user:password@localhost:5432/adversarial_sandbox_db
# RABBITMQ_URL=amqp://guest:guest@localhost:5672/
# AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
# AWS_REGION=your-aws-region
```
*Note: For sensitive production credentials, use a dedicated secret management solution.*

### 3.3. Start Dependencies (Database, Message Queue)

For local development, you can run dependent services using Docker Compose. A `docker-compose.dev.yml` will be provided for this purpose.

```bash
docker compose -f docker-compose.dev.yml up -d postgres rabbitmq
```
This will start local instances of PostgreSQL and RabbitMQ.

### 3.4. Backend Setup (API Gateway, Model Service, Attack Service)

Each backend service (located in `services/`) will have its own `requirements.txt` and potentially a `Dockerfile`.

1.  **Install Python Dependencies for Each Service:**
    ```bash
    # Example for api-gateway
    pip install -r services/api-gateway/requirements.txt
    # Repeat for model-service, attack-service, etc.
    ```
2.  **Run Migrations (if applicable):**
    ```bash
    # Example for API Gateway (adjust based on ORM/framework)
    python services/api-gateway/manage.py migrate
    ```
3.  **Run Services Locally (for development):**
    ```bash
    # Example for API Gateway
    python services/api-gateway/main.py
    # Open new terminals for other services:
    # python services/model-service/main.py
    # python services/attack-service/main.py
    ```
    *Alternatively, you can run all services via a comprehensive `docker-compose.dev.yml`.*

### 3.5. Frontend Setup (UI)

1.  **Navigate to the Frontend Directory:**
    ```bash
    cd frontend # Assuming a 'frontend' directory for React app
    ```
2.  **Install Node.js Dependencies:**
    ```bash
    npm install # or yarn install
    ```
3.  **Start Frontend Development Server:**
    ```bash
    npm start # or yarn start
    ```
    The frontend application should open in your browser, typically at `http://localhost:3000`.

## 4. Development Workflow

- **Branching:** Create a new branch for each feature or bug fix: `git checkout -b feature/your-feature-name`.
- **Committing:** Make small, atomic commits with clear messages.
- **Testing:** Run unit and integration tests frequently.
    - `pytest tests/unit/api-gateway/` (example)
- **Code Review:** Submit pull requests (PRs) to `main` for review.
- **Linting & Formatting:** Ensure code adheres to defined style guides (e.g., Black for Python, Prettier for JS).

## 5. Testing Procedures

- **Unit Tests:** Located in `tests/unit/`. Run with `pytest`.
- **Integration Tests:** Located in `tests/integration/`. Require dependent services to be running.
- **End-to-End (E2E) Tests:** Located in `tests/e2e/`. Simulate user interactions with the full system (e.g., using Playwright, Cypress).
- **Performance Tests:** Using tools like Locust or JMeter.
- **Security Tests:** SAST, DAST, penetration testing (as per `docs/security/SECURITY.md`).

## 6. Documentation Guidelines

- Keep all documentation (architectural, API, security, development) up-to-date.
- Use Markdown for clarity and readability.
- Ensure diagrams are up-to-date and generated from code where possible (e.g., Mermaid).

This setup guide aims to provide a clear and efficient process for all developers contributing to the AI Adversarial Sandbox.
