# AI Adversarial Sandbox

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

## Licensing

This AI Adversarial Sandbox is licensed under the **Business Source License 1.1 (BUSL 1.1)**.

### Why BUSL 1.1?

The choice of BUSL 1.1 reflects our commitment to building a sustainable and commercially viable SaaS product while maintaining a degree of transparency and future openness for the broader community.

*   **Commercial Protection:** As a Software-as-a-Service (SaaS) platform, protecting our core business model is paramount. BUSL 1.1 allows anyone to view, use, modify, and distribute the source code for non-commercial purposes, but it specifically restricts providing the software as a competing commercial service. This ensures our ability to monetize the advanced features and managed infrastructure we provide.
*   **Source-Available Transparency:** Unlike proprietary licenses, BUSL 1.1 keeps the source code publicly available. This allows security researchers, developers, and potential customers to inspect the code, understand its workings, and verify its integrity and quality. This transparency fosters trust and can encourage contributions and feedback that do not directly compete with the SaaS offering.
*   **Future Openness:** A key feature of BUSL 1.1 is its time-based conversion. After a specified "Change Date" (in our case, **4 years** from the first public release), the entire codebase will automatically convert to the permissive **Apache License 2.0**. This provides a clear roadmap for the software to become fully open source in the future, allowing for unrestricted use and further community growth over time.
*   **Compatibility:** All third-party libraries and frameworks used in this project are licensed under permissive open-source licenses (e.g., MIT, Apache 2.0), which are fully compatible with the Business Source License.

For commercial licensing inquiries or if you wish to use the software as a competing service before the Change Date, please contact us at **info@lexsightllc.com**.

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
