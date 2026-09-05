# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies first
# (Docker layer cache: only re-runs pip if requirements.txt changes)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL application code into /app (not /app/models/)
COPY . /app/

# Expose the port Cloud Run will send traffic to
EXPOSE 8080

# Start Gunicorn — uses $PORT injected by Cloud Run (defaults to 8080)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 120 apps:app"]
