# syntax=docker/dockerfile:1
FROM node:20-alpine AS frontend-builder
WORKDIR /app

COPY apps/frontend/package.json apps/frontend/package-lock.json ./apps/frontend/
RUN npm install --prefix apps/frontend
COPY apps/frontend ./apps/frontend
RUN npm run build --prefix apps/frontend

FROM python:3.10-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

COPY apps/backend/requirements.txt /app/apps/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/apps/backend/requirements.txt

COPY apps/backend /app/apps/backend
COPY --from=frontend-builder /app/apps/frontend/dist /app/dist
COPY nginx.conf /etc/nginx/nginx.conf
COPY scripts/start.sh /app/scripts/start.sh
RUN chmod +x /app/scripts/start.sh

EXPOSE 80
CMD ["/app/scripts/start.sh"]
