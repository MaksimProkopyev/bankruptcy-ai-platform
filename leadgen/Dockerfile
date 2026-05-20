FROM python:3.12-slim

WORKDIR /app

# Install ai-core (required by agents/shared/llm_router)
COPY ai-core/ ./ai-core/
RUN pip install --no-cache-dir ./ai-core/

# Install agents package
COPY agents/ ./agents/
RUN pip install --no-cache-dir ./agents/

# Install leadgen dependencies
COPY leadgen/requirements.txt ./leadgen/requirements.txt
RUN pip install --no-cache-dir -r ./leadgen/requirements.txt

# Copy service source into /app/leadgen/ so package imports work
COPY leadgen/ ./leadgen/

ENV PYTHONPATH=/app

CMD ["uvicorn", "leadgen.main:app", "--host", "0.0.0.0", "--port", "8002"]
