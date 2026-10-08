FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMNI_HOST=0.0.0.0 \
    OMNI_PORT=8080 \
    OMNI_REFRESH_SECONDS=180

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python3", "run.py", "--host", "0.0.0.0", "--port", "8080"]
