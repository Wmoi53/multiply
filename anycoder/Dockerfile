# Multi-stage build: compile the React frontend, then serve it + the FastAPI
# backend from a single container on one port (matches akhaliq/anycoder's
# sdk: docker, app_port: 7860 Space layout).

FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist ./static

ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
