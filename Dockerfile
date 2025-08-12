# Use official Python base image
FROM python:3.10-slim


# Set working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch==2.3.0+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install torchvision==0.23.0+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install --no-cache-dir -r requirements.txt --verbose --no-deps

# Copy the entire project into container
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# Command to run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
