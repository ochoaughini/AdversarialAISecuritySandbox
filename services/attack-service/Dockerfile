# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Create a non-root user and switch to it
RUN adduser --system --group appuser
USER appuser

# Copy the requirements file into the container
COPY --chown=appuser:appuser requirements.txt .

# Install any needed packages specified in requirements.txt
USER root
RUN pip install --no-cache-dir -r requirements.txt

# Download the small English spaCy model for TextAttack
RUN python -m spacy download en_core_web_sm
USER appuser

# Copy common modules and then the rest of the application code
COPY --chown=appuser:appuser ../database.py .
COPY --chown=appuser:appuser ../logging_config.py .
COPY --chown=appuser:appuser ../metrics_collector.py .
COPY --chown=appuser:appuser . .

# Expose port 8002 for the FastAPI application
EXPOSE 8002

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
