FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src/ /app/src/
COPY demo_client.py /app/demo_client.py

RUN python -m pip install --no-cache-dir -e /app

ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/demo_client.py"]
EXPOSE 8080
