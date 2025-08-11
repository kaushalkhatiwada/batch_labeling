# Use official Python image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for opencv, pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt if you have one
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose port if running a web server (e.g., FastAPI on 8000)
EXPOSE 8000
# Set environment variables
ENV ACCESS_KEY_ID=your_access_key_id
ENV SECRET_ACCESS_KEY=your_secret_access_key
ENV BUCKET_NAME=your_bucket_name
ENV OUTPUT_BUCKET_NAME=your_output_bucket_name
ENV ENDPOINT_URL=your_endpoint_url


CMD ["python", "fbnet.py"]