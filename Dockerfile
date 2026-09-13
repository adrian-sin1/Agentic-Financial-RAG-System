# --- Stage 1: build the React frontend -------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: install Python dependencies -----------------------------------
FROM python:3.12-slim AS python-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 3: slim runtime image ---------------------------------------------
FROM python:3.12-slim
WORKDIR /app

COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY src/ ./src/
COPY run_server.py .
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["python", "run_server.py"]
