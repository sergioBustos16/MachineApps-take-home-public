FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for compiling sqlite or other C-level requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies from PyPI (including custom Vention libraries)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose FastAPI server port
EXPOSE 8000

# Start development / production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
