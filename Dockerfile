FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UNISPACE_DATA_FILE=/data/unispace.json

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[ai]" \
    && useradd --create-home app \
    && mkdir /data && chown app /data

USER app
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "unispace.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
