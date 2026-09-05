FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY . .

# Expose port (Render/Railway/CloudRun dynamically inject PORT environment variable)
ENV PORT=8000
EXPOSE 8000

# Run uvicorn on 0.0.0.0 and dynamically use $PORT if set
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
