FROM python:3.11-slim

WORKDIR /app
COPY collatz_backoff.py demo_client.py /app/

RUN python -m compileall /app

ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/demo_client.py"]
