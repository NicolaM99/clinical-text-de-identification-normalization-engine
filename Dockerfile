# Use a lightweight official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
# Prevents Python from writing pyc files to disc and buffers stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application entry point
COPY main.py .

# Expose the application port (Cloud Run will route traffic to this port)
EXPOSE 8080

# Launch the FastAPI application using Uvicorn
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
