# Multi-stage Dockerfile for HCI Project
# This Dockerfile builds both the backend (Flask) and frontend (React + Vite)

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Backend with Python
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source files
COPY *.py ./
COPY *.jpg ./

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose ports
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=flask_server.py
ENV PYTHONUNBUFFERED=1

# Run Flask server
CMD ["python", "flask_server.py"]
