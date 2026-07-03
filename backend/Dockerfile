# Dockerfile for Python Flask Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/ ./backend
COPY cli.py .

EXPOSE 5000

ENV PORT=5000
ENV FLASK_APP=backend/app.py

# Run flask server
CMD ["python", "backend/app.py"]
