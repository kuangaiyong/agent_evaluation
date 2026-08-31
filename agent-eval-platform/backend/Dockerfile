FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt -r requirements-dev.txt
COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
