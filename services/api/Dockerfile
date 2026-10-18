FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/repo/services/api

WORKDIR /repo/services/api
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Source is bind-mounted by docker-compose at /repo; copied here too so the image runs on its own.
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
