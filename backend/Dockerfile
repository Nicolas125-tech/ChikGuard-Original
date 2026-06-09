FROM python:3.12-slim-bookworm

# Apply docker-expert and security-auditor best practices: non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psutil

COPY . .

# Ensure appuser owns the application files
RUN chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "app.py"]
