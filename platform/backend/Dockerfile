FROM node:24-alpine AS frontend-build
WORKDIR /web
COPY frontend/package.json ./package.json
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app/ ./app/
COPY backend/alembic.ini ./alembic.ini
COPY backend/entrypoint.sh ./entrypoint.sh
COPY --from=frontend-build /web/dist ./app/frontend/
RUN chmod 0555 ./entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
