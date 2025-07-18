# Use a lightweight official Python runtime as a parent image
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
USER appuser

# Copy the rest of the application code into the container
COPY --chown=appuser:appuser . .

# Expose the port the Flask app runs on
EXPOSE 8003

# Command to run the application using Gunicorn for production-like environment
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8003", "main:app"]
