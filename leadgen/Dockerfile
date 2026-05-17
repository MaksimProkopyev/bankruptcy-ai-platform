FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service source into /app/leadgen/ so package imports work
COPY . ./leadgen/

# Create a minimal __init__.py at /app level isn't needed;
# leadgen is the top-level package at /app/leadgen/
ENV PYTHONPATH=/app

CMD ["uvicorn", "leadgen.main:app", "--host", "0.0.0.0", "--port", "8002"]
