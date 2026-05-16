FROM python:3.11-slim

# Install system dependencies required for compiling the C++ engine
RUN apt-get update && apt-get install -y build-essential cmake gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code
COPY src/ ./src/

# Hugging Face Spaces strictly requires apps to run on port 7860
EXPOSE 7860

# Start the FastAPI server
CMD ["uvicorn", "src.app_backend:app", "--host", "0.0.0.0", "--port", "7860"]