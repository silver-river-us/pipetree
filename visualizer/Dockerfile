FROM python:3.12-slim

WORKDIR /app

# Install pipetree package
COPY pipetree/ /app/pipetree/
RUN pip install --no-cache-dir /app/pipetree

# Install visualizer dependencies
RUN pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "jinja2>=3.1.0" \
    "websockets>=12.0" \
    "python-multipart>=0.0.6" \
    "python-dotenv" \
    "sqlmodel" \
    "httpx>=0.26.0" \
    "peewee>=3.17.0" \
    "peewee-migrate>=1.12.0" \
    "pyjwt>=2.8.0"

# Copy visualizer code
COPY visualizer/visualizer/ /app/visualizer/
COPY visualizer/pyproject.toml ./

# Create data directory for SQLite databases
RUN mkdir -p /data

ENV DB_PATH=/data/pipelines
ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "visualizer.app:app", "--host", "0.0.0.0", "--port", "8001"]
