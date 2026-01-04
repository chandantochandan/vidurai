# Vidurai Proxy v2.0.0
# Build from parent directory: docker build -f vidurai-proxy/Dockerfile -t vidurai-proxy:2.0.0 .

FROM python:3.10-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git && \
      rm -rf /var/lib/apt/lists/*

# Copy Vidurai SDK first (from parent context)
COPY vidurai /app/vidurai
COPY setup.py /app/setup.py
COPY requirements.txt /app/sdk-requirements.txt
COPY README.md /app/README.md

# Install SDK (editable)
RUN pip install --no-cache-dir -e .

# Copy proxy
COPY vidurai-proxy /app/vidurai-proxy

WORKDIR /app/vidurai-proxy

# Install proxy dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 9999

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9999"]
